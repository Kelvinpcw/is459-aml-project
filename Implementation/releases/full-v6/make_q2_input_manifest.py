"""Trusted preparation handoff: publish only label-free detector metadata."""
import json
from pathlib import Path


def make_manifest(preparation):
    if (preparation.get("status") != "PASSED" or preparation.get("schema_version") != 2 or
            not preparation.get("label_separation_passed") or
            not preparation.get("source_reference_reconciliation_passed") or
            preparation.get("quarantined_rows") != 0):
        raise ValueError("Require the verified precision-safe complete preparation population")
    columns = preparation["fact_columns"]
    if any(any(word in c.lower() for word in ("launder", "label", "annotation")) for c in columns):
        raise ValueError("Facts are not label-free")
    return {"schema_version": 1, "stage": "detector_inputs", "preparation_status": "PASSED",
            "dataset_version": preparation["dataset_version"], "run_id": preparation["run_id"],
            "accepted_rows": preparation["accepted_rows"], "fact_columns": columns,
            "amount_policy": {"precision": preparation["amount_policy"]["precision"],
                              "scale": preparation["amount_policy"]["scale"]},
            "inputs": {"transactions": preparation["outputs"]["transactions"]},
            "timestamp_policy": preparation["timestamp_policy"]}


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    preparation = json.loads((root / "aws/reviews/preparation-report-dev-20220901-v2.json").read_text())
    output = root / "aws/manifests/q2-input-v2.json"
    output.parent.mkdir(exist_ok=True)
    output.write_text(json.dumps(make_manifest(preparation), indent=2) + "\n")
    print(output)
