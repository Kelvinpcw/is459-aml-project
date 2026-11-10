"""Independently evaluate a completed shortlist against the saved AWS labels and IBM patterns."""

import argparse
from collections import Counter, defaultdict
from hashlib import file_digest
import json
from pathlib import Path
import sys

import numpy as np
import pyarrow.parquet as pq

from rank_shortlist import CASE, KINDS, RESULT, ReplayFiles, binary, require, snapshot_cutoff
from datetime import date


def sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return file_digest(stream, "sha256").hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("experiments", type=Path)
    parser.add_argument("attempt", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    replay = args.experiments / "trace-q2-full-replay"
    sys.path.insert(0, str(replay))
    from reference import eligible_shapes, match_attempts, read_labels
    from prepare import PREP, RELEASE

    source_check = json.loads((args.attempt / "source-check.json").read_text())
    shortlist_manifest = args.output / "manifest.json"
    manifest = json.loads(shortlist_manifest.read_text())
    require(manifest["release_id"] == RELEASE["release_id"] == source_check["release_id"],
            "Evaluation and shortlist use different releases")
    require(manifest["input_check_sha256"] == sha256(args.attempt / "source-check.json"),
            "Shortlist input verification changed")
    ranked_artifact, alert_artifact = (manifest["artifacts"][name] for name in ("ranked_cases", "payment_alerts"))
    for artifact in (ranked_artifact, alert_artifact):
        require(sha256(args.output / artifact["file"]) == artifact["sha256"], "Output bytes changed before evaluation")

    root = replay / "work"
    population, case_rows = source_check["facts"], source_check["case_rows"]
    data = ReplayFiles(binary(root / "cases.bin", CASE, case_rows), binary(root / "scored.bin", RESULT, case_rows),
                       binary(root / "case-ids.s64", np.dtype("S64"), case_rows),
                       binary(root / "evidence.u32", np.dtype("<u4"), source_check["evidence_memberships"]),
                       binary(root / "days.u8", np.dtype("u1"), population + 1))
    cases = pq.read_table(args.output / ranked_artifact["file"]).to_pylist()
    alerts = pq.read_table(args.output / alert_artifact["file"])
    ids = alerts["source_record_ordinal"].to_numpy()
    expected_prefix = PREP["source_manifest"]["source_files"]["transactions"]["sha256"] + ":"
    require(len(ids) == manifest["payment_alerts"] and bool(np.all((ids > 0) & (ids <= population)))
            and len(np.unique(ids)) == len(ids), "Invalid, missing, or repeated payment alert IDs")
    require(alerts["source_id"].to_pylist() == [f"{expected_prefix}{value}" for value in ids], "Wrong payment source identity")
    require(np.all(alerts["standalone_alert"].to_numpy() | alerts["case_evidence"].to_numpy()), "Alert has no selection reason")
    evidence_by_topology: dict[tuple[int, ...], list[tuple[str, set[int]]]] = defaultdict(list)
    all_core: set[int] = set()
    seen: set[int] = set()
    first = date.fromisoformat(manifest["first_date"])
    for case in cases:
        row = case["case_row"]
        core = set(case["highlighted_ordinals"])
        kind = int(data.cases[row]["kind"])
        cutoff = int(data.cases[row]["day"])
        require(row not in seen and data.case_ids[row].decode("ascii") == case["case_id"]
                and case["pattern_type"] == KINDS[kind]
                and case["snapshot_cutoff"] == snapshot_cutoff(first, cutoff), "Snapshot does not match the original case")
        require(len(core) == len(case["highlighted_ordinals"]) and core.issubset(map(int, data.members(row)))
                and all(data.days[i] <= cutoff for i in core), "Case evidence is duplicate, foreign, or later than its cutoff")
        require(case["highlighted_source_ids"] == [f"{expected_prefix}{value}" for value in case["highlighted_ordinals"]],
                "A highlighted payment lacks its exact source ID")
        seen.add(row)
        all_core.update(core)
        evidence_by_topology[data.topology(row)].append((case["case_id"], core))
    require(all_core == set(map(int, ids[alerts["case_evidence"].to_numpy()])), "Case evidence and payment alerts disagree")
    require(len(cases) == manifest["case_snapshots"]
            and len({row["investigation_id"] for row in cases}) == manifest["investigations"], "Archive counts disagree")
    print(f"Reconciled source IDs and time cutoffs for all {len(cases):,} retained cases and {len(ids):,} unique alerts", flush=True)

    labels = read_labels(1, 28, root)
    require(len(labels) == population + 1 and np.all(labels[1:] <= 1) and labels[0] == 255, "Incomplete label population")
    print("Verified all 28 AWS label partitions by ETag and source ordinal", flush=True)
    references = match_attempts(eligible_shapes(1, 28), 1, 28, labels, root)
    print(f"Parsed and matched {len(references)} eligible IBM annotations to source payments", flush=True)
    covered: Counter[str] = Counter()
    eligible: Counter[str] = Counter()
    missed: list[str] = []
    for annotation in references:
        kind = annotation["kind"]
        eligible[KINDS[kind]] += 1
        expected = set(annotation["ordinals"])
        candidates = evidence_by_topology[(kind, *annotation["nodes"])]
        if any(5 * len(expected & core) >= 4 * len(expected) for _, core in candidates):
            covered[KINDS[kind]] += 1
        else:
            missed.append(annotation["attempt_id"])
    positives = int(np.count_nonzero(labels == 1))
    true_positives = int(np.count_nonzero(labels[ids] == 1))
    recovered = sum(covered.values())
    observed = (len(references), recovered, len(ids), true_positives, positives, manifest["investigations"], len(cases))
    expected = (539, 539, 130_415, 25_252, 35_230, 9_493, 12_075)
    results = {"release_id": manifest["release_id"], "shortlist_manifest_sha256": sha256(shortlist_manifest),
               "first_date": manifest["first_date"], "last_date": manifest["last_date"],
               "payments": population, "payment_alerts": len(ids), "ibm_positive_alerts": true_positives,
               "ibm_positive_payments": positives, "payment_precision": true_positives / len(ids),
               "payment_recall": true_positives / positives, "eligible_patterns": len(references),
               "recovered_patterns": recovered, "investigations": manifest["investigations"],
               "case_snapshots": len(cases), "exact_checkpoint_parity": observed == expected,
               "by_pattern": {name: {"recovered": covered[name], "eligible": eligible[name]} for name in KINDS},
               "missed_pattern_ids": missed}
    with (args.output / "evaluation.json").open("x") as stream:
        json.dump(results, stream, indent=2)
        stream.write("\n")
    print(json.dumps(results, indent=2), flush=True)
    require(observed == expected, f"Expected {expected}, observed {observed}")


if __name__ == "__main__":
    main()
