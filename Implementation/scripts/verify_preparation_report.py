"""Verify a downloaded preparation v2 report against the retained input manifest."""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "jobs"))
from q1_risk import validate_preparation_contract


def verify(report, manifest, run_id):
    validate_preparation_contract(report)
    if report["source_manifest"] != manifest or report["dataset_version"] != manifest["dataset_version"]:
        raise ValueError("Dataset/source manifest mismatch")
    if report["run_id"] != run_id:
        raise ValueError("Unexpected run identity")
    expected = manifest["counts"]["selected_records"]
    if (report["input_rows"] != expected or report["accepted_rows"] != expected or
            report["quarantined_rows"] != 0 or report["quarantine_by_reason"]):
        raise ValueError("Development population must be complete, with zero quarantine")
    if report["invalid_account_mappings"] != 0 or report["valid_account_mappings"] != 2087786:
        raise ValueError("Unexpected account mapping population")
    if report["join_coverage"] != {"unmatched_sender_rows": 0, "unmatched_receiver_rows": 0}:
        raise ValueError("Review unmatched endpoints before accepting development result")
    if any("launder" in column.lower() for column in report["fact_columns"]):
        raise ValueError("Labels present in facts")
    if not {"amount_paid_raw", "amount_received_raw", "amount_paid", "amount_received"} <= set(report["fact_columns"]):
        raise ValueError("Missing exact/raw amount contract")
    actual = {r["payment_format"]: {k: r[k] for k in ("transactions", "labelled_laundering")}
              for r in report["accepted_by_format"]}
    reference = {f: {k: v[k] for k in ("transactions", "labelled_laundering")}
                 for f, v in manifest["q1_source_reference_by_format"].items()}
    if actual != reference or report["quarantined_by_format"]:
        raise ValueError("Per-format source population mismatch")
    if sum(r["labelled_laundering"] for r in actual.values()) != manifest["counts"]["selected_label_1"]:
        raise ValueError("Positive labels do not reconcile")
    bucket = "is459-aml-g2team7-160885259244-us-east-1"
    suffix = f"dataset_version={manifest['dataset_version']}/run_id={run_id}/"
    for name, zone, directory in (("transactions", "curated", "transactions"),
                                  ("accounts", "curated", "accounts"),
                                  ("labels", "references/labels", "transactions")):
        if report["outputs"][name] != f"s3://{bucket}/{zone}/{suffix}{directory}/":
            raise ValueError("Unexpected output location")
    return {"status": "VERIFIED", "dataset_version": report["dataset_version"], "run_id": run_id,
            "accepted_rows": expected, "positive_labels": manifest["counts"]["selected_label_1"],
            "quarantined_rows": 0, "payment_formats": actual,
            "scope": "Independent report/manifest checks; actual Parquet schema/sample inspection recorded separately"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = verify(json.loads(args.report.read_text()), json.loads(args.manifest.read_text()), args.run_id)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
