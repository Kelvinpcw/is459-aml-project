"""Reconcile saved cloud JSON against the frozen label-free local replay.

Accepts files read through the signed-in AWS console; no AWS credentials or APIs.
Compares parsed full bundles and their deterministic emitted JSON encoding so
browser whitespace rendering cannot hide an evidence/content discrepancy.
"""
import hashlib
import json
from datetime import datetime
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "jobs"))
from q2_detect import Config, RULE_VERSION, case_index_row, encode_case


def verify(root):
    review = root / "aws/reviews"
    replay = json.loads((review / "q2-local-replay-m00-v1.json").read_text())
    report = json.loads((review / "q2-report-q2-dev-20220901-m00-v1.json").read_text())
    if (report.get("status") != "PASSED" or report.get("stage") != "q2" or
            report.get("rule_version") != RULE_VERSION or report.get("detector_received_labels") is not False):
        raise ValueError("Cloud Q2 is not a passed label-free analysis")
    if report["config"] != replay["config"] or report["statistics"] != replay["statistics"]:
        raise ValueError("Cloud scope/limits/statistics differ from the frozen replay")
    if report["full_prepared_rows"] != replay["source_rows_scanned"]:
        raise ValueError("Immutable input population changed")
    config = replay["config"]
    base = ("s3://is459-aml-g2team7-160885259244-us-east-1/gold/cases/"
            f"dataset_version={config['dataset_version']}/run_id={config['run_id']}/"
            f"analysis_id={config['analysis_id']}/")
    if report["outputs"] != {"bundles": base + "bundles/", "case_index": base + "case_index/"}:
        raise ValueError("Cloud output locations differ from the reviewed namespace")
    cloud = root / "data/q2-cloud-m00-v1"
    local = root / "data/q2-local-m00-v1"
    expected = {c["case_id"]: c for c in replay["case_inventory"]}
    observed = {p.stem for p in cloud.glob("*.json")}
    if observed != set(expected):
        raise ValueError("Cloud bundle inventory is incomplete or has unexpected cases")
    verified = []
    for case_id, inventory in sorted(expected.items()):
        case = json.loads((cloud / f"{case_id}.json").read_text())
        reference = json.loads((local / f"{case_id}.json").read_text())
        if case != reference:
            raise ValueError("Cloud case differs from complete local evidence: " + case_id)
        canonical = encode_case(case)
        digest = hashlib.sha256(canonical).hexdigest()
        if digest != inventory["bundle_sha256"] or len(canonical) != inventory["bundle_bytes"]:
            raise ValueError("Deterministic bundle hash/size differs: " + case_id)
        verified.append({"case_id": case_id, "canonical_sha256": digest,
                         "evidence_transactions": len(case["transactions"])})
    result = {"status": "VERIFIED", "analysis_id": config["analysis_id"],
              "cloud_quality_status": report["status"], "config_and_statistics_match": True,
              "full_prepared_rows": report["full_prepared_rows"],
              "scoped_rows": report["statistics"]["scoped_rows"],
              "case_count": len(verified), "all_bundle_content_matches": True,
              "all_canonical_bundle_hashes_match": True,
              "evidence_rows_including_overlap": sum(c["evidence_transactions"] for c in verified),
              "case_index_physical_read_validated": False,
              "note": "Complete JSON bundles verified; Athena Parquet validation is recorded separately.",
              "cases": verified}
    index_file = review / "q2-athena-case-index-rows.json"
    if index_file.exists():
        header, *rows = json.loads(index_file.read_text())
        expected_columns = set(case_index_row(reference, Config(**config), "s3://example")) | {"#"}
        if set(header) != expected_columns or len(set(header)) != len(header):
            raise ValueError("Athena index columns differ from the output contract")
        if len(rows) != len(expected) or any(len(row) != len(header) for row in rows):
            raise ValueError("Athena index is incomplete or malformed")
        seen = set()
        time_fields = {"window_start", "window_end", "snapshot_cutoff", "first_event_time", "last_event_time"}
        count_fields = {"participant_count", "unique_edge_count", "evidence_transaction_count"}
        for values in rows:
            actual = dict(zip(header, values))
            actual.pop("#")
            case_id = actual["case_id"]
            if case_id not in expected or case_id in seen:
                raise ValueError("Missing, foreign or duplicate physical case ID")
            seen.add(case_id)
            case = json.loads((local / f"{case_id}.json").read_text())
            reference_row = case_index_row(case, Config(**config), base + f"bundles/{case_id}.json")
            for field in time_fields:
                actual[field] = datetime.fromisoformat(actual[field])
                if isinstance(reference_row[field], str):
                    reference_row[field] = datetime.fromisoformat(reference_row[field])
            for field in count_fields:
                actual[field] = int(actual[field])
            actual["window_date"] = datetime.fromisoformat(actual["window_date"]).date()
            if actual != reference_row:
                raise ValueError("Athena physical index row differs from its case: " + case_id)
        if seen != set(expected):
            raise ValueError("Physical case inventory differs")
        result.update({"case_index_physical_read_validated": True,
                       "index_rows_all_fields_match": len(rows),
                       "note": "All complete case bundles and every Athena-read index field match the frozen replay."})
    (review / "q2-cloud-verification-m00-v1.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({k: v for k, v in result.items() if k != "cases"}, indent=2))


if __name__ == "__main__":
    verify(Path(__file__).resolve().parents[1])
