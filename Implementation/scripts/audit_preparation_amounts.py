"""Independently reconcile an existing report to local input; no AWS requests."""
import argparse
import collections
import csv
import gzip
import json
import re
from pathlib import Path


def audit(input_dir, report_path):
    manifest = json.loads((input_dir / "manifest.json").read_text())
    report = json.loads(report_path.read_text())
    if report["source_manifest"] != manifest:
        raise ValueError("Report does not match the local ingestion manifest")
    legacy = re.compile(r"^[+-]?[0-9]+(?:\.[0-9]{1,2})?$")
    # Independent representation bounds for decimal(38,8); count significant integer digits.
    exact = re.compile(r"^[+-]?([0-9]+)(?:\.([0-9]{1,8}))?$")
    rejected = collections.defaultdict(collections.Counter)
    reasons = collections.Counter()
    input_rows = new_invalid = max_scale = max_integer = 0
    with gzip.open(input_dir / "transactions.csv.gz", "rt", newline="") as source:
        for row in csv.DictReader(source):
            input_rows += 1
            errors = []
            new_valid = True
            for side in ("paid", "received"):
                value = row[f"amount_{side}_raw"]
                if not legacy.fullmatch(value):
                    errors.append(f"invalid_{side}_amount")
                match = exact.fullmatch(value)
                if match is None:
                    new_valid = False
                else:
                    digits = len(match[1].lstrip("0"))
                    max_integer = max(max_integer, digits)
                    max_scale = max(max_scale, len(match[2] or ""))
                    new_valid &= digits <= 30
            new_invalid += not new_valid
            if errors:
                reasons[";".join(errors)] += 1
                rejected[row["payment_format"]]["transactions"] += 1
                rejected[row["payment_format"]]["labelled_laundering"] += int(row["is_laundering_raw"])
    if input_rows != report["input_rows"] or input_rows != manifest["counts"]["selected_records"]:
        raise ValueError("Input count does not match")
    if report["accepted_rows"] + report["quarantined_rows"] != input_rows:
        raise ValueError("Report row counts do not reconcile")
    if sum(reasons.values()) != report["quarantined_rows"]:
        raise ValueError("Amount-scale issue does not explain all quarantined rows")
    accepted = {r["payment_format"]: r for r in report["accepted_by_format"]}
    for format_name, reference in manifest["q1_source_reference_by_format"].items():
        for field in ("transactions", "labelled_laundering"):
            if accepted[format_name][field] + rejected[format_name][field] != reference[field]:
                raise ValueError("Format counts do not reconcile")
    return {"status": "BLOCKED_AMOUNT_PRECISION", "release_ready": False,
            "report_matches_local_manifest": True, "row_reconciliation_passed": True,
            "per_format_reconciliation_passed": True, "input_rows": input_rows,
            "legacy_amount_rejections": sum(reasons.values()),
            "reasons_reproduced_locally": dict(reasons), "rejected_by_format": dict(rejected),
            "quarantined_label_1": sum(r["labelled_laundering"] for r in rejected.values()),
            "decimal_38_8_representation_rejections": new_invalid,
            "observed_max_scale": max_scale, "observed_max_integer_digits": max_integer,
            "scope": "Independent local amount audit; not a full execution of preparation v2 or an inspection of every cloud Parquet object"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.input_dir, args.report)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
