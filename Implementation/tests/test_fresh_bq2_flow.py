"""Run raw CSVs through the same stage boundaries used by Glue and TRACE."""

import csv
from datetime import date, datetime, timedelta
import io
import json
import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest

ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "jobs", ROOT / "ml_replay/glue"):
    sys.path.insert(0, str(path))


def fixture(mirror: Path) -> tuple[str, str, set[str]]:
    from fresh_inputs import ACCOUNT_HEADER, TRANSACTION_HEADER
    from pipeline.release import encoded, sha

    def write(key, content):
        path = mirror / key
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        return {"key": key, "sha256": sha(content)}

    def write_csv(name, header, rows):
        stream = io.StringIO(newline="")
        writer = csv.writer(stream)
        writer.writerow(header)
        writer.writerows(rows)
        return write(f"fresh-bq2/incoming/{name}.csv", stream.getvalue().encode())

    start = datetime(2024, 10, 7, 10)
    days = []
    for offset in range(4):
        pairs = ([(f"PAYEE{i}", "HUB") for i in range(1, 6)] if offset == 0
                 else [("HUB", f"DEST{i}") for i in range(1, 6)])
        pairs += [("LOOP1", "LOOP2"), ("LOOP2", "LOOP1")]
        days.append([[(start + timedelta(days=offset, minutes=i)).strftime("%Y/%m/%d %H:%M"),
                      "001", sender, "1", receiver, "725.00000000", "US Dollar",
                      "725.00000000", "US Dollar", "ACH"]
                     for i, (sender, receiver) in enumerate(pairs)])
    first = write_csv("payments-a", TRANSACTION_HEADER, [days[2][5], *days[0], *days[1]])
    second = write_csv("payments-b", TRANSACTION_HEADER, [days[2][6], *days[2][:5], *days[3]])
    accounts = write_csv("accounts", ACCOUNT_HEADER,
                         [["Example Bank", "1", "LOOP1", "E-1", "Known account"]])
    cycle_ids = {first["sha256"] + ":1", second["sha256"] + ":1"}
    labels = [{"source_id": first["sha256"] + ":1", "is_laundering": 1}] + [
        {"source_id": second["sha256"] + f":{i}", "is_laundering": int(i == 2)}
        for i in range(1, 7)
    ]
    base = {"schema_version": 1, "dataset_version": "fresh-bq2-synthetic",
            "history_start": "2024-10-07", "files": [first, second], "accounts": accounts}
    day_one = write("fresh-bq2/incoming/first/ready.json", encoded({
        **base, "batch_start": "2024-10-09", "cutoff": "2024-10-10",
        "labels": write("fresh-bq2/reference/labels.json", encoded(labels)),
        "annotations": write("fresh-bq2/reference/annotations.json", encoded([
            {"annotation_id": "cycle-across-files", "pattern_type": "cycle_2", "source_ids": sorted(cycle_ids)}
        ])),
    }))
    day_two = write("fresh-bq2/incoming/second/ready.json", encoded({
        **base, "batch_start": "2024-10-10", "cutoff": "2024-10-11",
        "files": [first, second, write_csv("payments-c", TRANSACTION_HEADER, [[
            "2024/10/10 13:15", "2", "NEW1", "3", "NEW2", "1.00000000", "US Dollar",
            "1.00000000", "US Dollar", "ACH",
        ]])],
    }))
    return day_one["key"], day_two["key"], cycle_ids


def exercise(mirror: Path, bundle: Path, approved_digest: str) -> dict:
    import pyarrow.parquet as pq

    from dashboard.data import get_case, read_evidence_part
    from fresh_glue import CURRENT, STAGES, run_local
    from pipeline.bq2_release import LocalBQ2Objects
    from pipeline.release import encoded, split_uri, verify_ref

    def read(path):
        return json.loads(path.read_bytes())

    def check(condition, message):
        if not condition:
            raise AssertionError(message)

    def active():
        pointer = read(mirror / CURRENT)
        return pointer, verify_ref(LocalBQ2Objects(mirror), pointer)

    first, second, cycle_ids = fixture(mirror)
    succeeded = {stage: "published" if stage == "publish" else "passed" for stage in STAGES}
    check(run_local(mirror, first, bundle, approved_digest, "fresh-test-a") == succeeded, "First run stages")
    pointer, release = active()
    objects = LocalBQ2Objects(mirror)
    metrics = verify_ref(objects, release["evaluation"])
    check(metrics["eligible_payments"] == metrics["labelled_payments"] == 7, "Wrong eligible population")
    check(metrics["scored_payments"] == 21, "Cutoff must keep 21 of 28 input payments")
    check(metrics["payment_precision"] == metrics["payment_recall"] == 0.5, f"Unexpected metrics {metrics}")
    check(metrics["recovered_patterns"] == metrics["eligible_patterns"] == 1, "Cycle evidence not recovered")
    prefix = mirror / split_uri(pointer["uri"])[1]
    ranked = pq.read_table(prefix.with_name("ranked_cases.parquet")).to_pylist()
    index = pq.read_table(prefix.with_name("evidence_index.parquet")).to_pylist()
    case, _ = get_case(objects, release, next(row for row in index if row["case_id"] == ranked[0]["case_id"]))
    evidence = {json.loads(line)["source_id"] for part in case["evidence_parts"]
                for line in read_evidence_part(objects, part).splitlines()}
    check(cycle_ids <= evidence and cycle_ids <= set(ranked[0]["highlighted_source_ids"]),
          "Two distinct row-1 payments must resolve through TRACE's real evidence reader")
    manifest = verify_ref(objects, release["shortlist"])
    check(len(manifest["models"]) == 3 and len(manifest["case_model_sha256"]) == 2 and len(ranked) > 0,
          "The fixture must exercise all five fitted models")
    duplicate = run_local(mirror, first, bundle, approved_digest, "fresh-test-repeat")
    check(duplicate == {"prepare": "already-published"} and active()[0] == pointer, "Duplicate run published")

    # Fail evaluation after preparation, detection and scoring have finished.
    invalid = read(mirror / second)
    invalid["labels"] = read(mirror / first)["labels"]
    bad = "fresh-bq2/incoming/invalid/ready.json"
    (mirror / bad).parent.mkdir(parents=True)
    (mirror / bad).write_bytes(encoded(invalid))
    try:
        run_local(mirror, bad, bundle, approved_digest, "fresh-test-bad")
    except ValueError as error:
        check("labels" in str(error) and active()[0] == pointer, f"Wrong failure or pointer changed: {error}")
    else:
        raise AssertionError("Mismatched evaluation labels published")

    check(run_local(mirror, second, bundle, approved_digest, "fresh-test-b") == succeeded, "Second run stages")
    latest_pointer, latest = active()
    unlabeled = verify_ref(objects, latest["evaluation"])
    check(latest_pointer != pointer and latest["cutoff"] == (date(2024, 10, 10) + timedelta(days=1)).isoformat(),
          "New batch did not become current")
    check(unlabeled["scored_payments"] == 29 and unlabeled["eligible_payments"] == 8 and
          unlabeled["payment_precision"] is None and unlabeled["payment_recall"] is None,
          "Unlabelled data must be scored and reported without invented metrics")
    return {"labelled": metrics, "unlabelled": unlabeled, "duplicate": duplicate, "failure_kept_release": True}


class FreshBQ2FlowTests(unittest.TestCase):
    def test_large_csv_preserves_source_ids_and_graph_across_parquet_parts(self):
        import pyarrow.parquet as pq

        from fresh_glue import hash_file, parse_ready
        from fresh_inputs import ACCOUNT_HEADER, PARQUET_BATCH_ROWS, TRANSACTION_HEADER, detect_batch, prepare_batch
        from pipeline.release import encoded, split_uri

        with TemporaryDirectory(prefix="trace-fresh-volume-") as directory:
            mirror = Path(directory)
            incoming = mirror / "fresh-bq2/incoming"
            incoming.mkdir(parents=True)
            payments = incoming / "payments.csv"
            accounts = incoming / "accounts.csv"
            work = mirror / "reports"
            work.mkdir()
            with accounts.open("w", newline="") as stream:
                csv.writer(stream).writerow(ACCOUNT_HEADER)
            common = ["2024/10/07 10:00", "1", "HUB", "1"]
            amounts = ["725.0", "US Dollar", "725.0", "US Dollar", "ACH"]
            with payments.open("w", newline="") as stream:
                writer = csv.writer(stream)
                writer.writerow(TRANSACTION_HEADER)
                writer.writerows([*common, f"DEST{i}", *amounts] for i in range(4))
                writer.writerows([*common, "HUB", *amounts] for _ in range(PARQUET_BATCH_ROWS - 4))
                writer.writerow([*common, "DEST4", *amounts])
            ready = parse_ready(encoded({
                "schema_version": 1, "dataset_version": "fresh-bq2-spill",
                "history_start": "2024-10-07", "batch_start": "2024-10-07", "cutoff": "2024-10-08",
                "files": [{"key": str(payments.relative_to(mirror)), "sha256": hash_file(payments)}],
                "accounts": {"key": str(accounts.relative_to(mirror)), "sha256": hash_file(accounts)},
            }))
            manifest_path = prepare_batch(ready, "spill-check", mirror, work)
            manifest = json.loads(manifest_path.read_bytes())
            self.assertEqual(manifest["accepted_rows"], PARQUET_BATCH_ROWS + 1)
            _, facts = split_uri(manifest["inputs"]["transactions"])
            parts = sorted((mirror / facts).glob("event_date=*/*.parquet"))
            self.assertEqual([pq.ParquetFile(path).metadata.num_rows for path in parts], [PARQUET_BATCH_ROWS, 1])
            self.assertEqual(pq.ParquetFile(parts[-1]).read(columns=["source_id"])[0][0].as_py(),
                             f"{hash_file(payments)}:{PARQUET_BATCH_ROWS + 1}")
            detector = detect_batch(manifest_path, mirror, work, date(2024, 10, 7), date(2024, 10, 8))
            stats = json.loads(detector.read_bytes())["statistics"]
            self.assertEqual(stats["case_count"], 1)
            self.assertEqual(stats["case_evidence_rows_including_case_overlap"], 5)

    def test_two_batches_with_saved_models(self):
        bundle = os.environ.get("TRACE_TEST_MODEL_BUNDLE")
        digest = os.environ.get("TRACE_TEST_MODEL_BUNDLE_SHA256")
        if not bundle or not digest:
            self.skipTest("Set the private approved model bundle path and manifest digest")
        with TemporaryDirectory(prefix="trace-fresh-flow-") as directory:
            result = exercise(Path(directory), Path(bundle), digest)
        self.assertTrue(result["failure_kept_release"])
