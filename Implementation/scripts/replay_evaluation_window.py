"""Local isolated evaluation of frozen cloud cases against all eligible input rows.

Trusted local preparation projects facts and labels into separate inputs. No
detector is run or modified; no AWS API or credentials are used.
"""
from collections import Counter
from datetime import datetime
from decimal import Decimal
import csv
import gzip
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "jobs"))
from evaluate_q2 import artifact_payloads, canonical_sha, evaluate, normalise_bank, parse_annotations, scope


def run(root):
    prep = json.loads((root / "aws/reviews/preparation-report-dev-20220901-v2.json").read_text())
    report = json.loads((root / "aws/reviews/q2-report-q2-dev-20220901-m00-v1.json").read_text())
    verified = json.loads((root / "aws/reviews/q2-cloud-verification-m00-v1.json").read_text())
    if verified["status"] != "VERIFIED" or not verified["case_index_physical_read_validated"]:
        raise ValueError("Require frozen independently verified cloud detections")
    config, start, end, cutoff = scope(report)
    source = root / "data/development-20220901/transactions.csv.gz"
    with source.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    if digest != prep["source_manifest"]["artifacts"][source.name]["sha256"]:
        raise ValueError("Selected source checksum changed")
    facts, labels, formats, positives = [], [], Counter(), Counter()
    source_rows = 0
    raw_start, raw_end, raw_cutoff = (t.strftime("%Y/%m/%d %H:%M:%S") for t in (start, end, cutoff))
    with gzip.open(source, "rt", newline="") as stream:
        for row in csv.DictReader(stream):
            source_rows += 1
            label = row["is_laundering_raw"]
            if label not in ("0", "1"):
                raise ValueError("Invalid source label")
            formats[row["payment_format"]] += 1
            positives[row["payment_format"]] += int(label)
            raw_time = row["timestamp_raw"] + ":00"
            if not raw_start <= raw_time < raw_end or raw_time > raw_cutoff:
                continue
            event = datetime.strptime(row["timestamp_raw"], "%Y/%m/%d %H:%M")
            fact = {"source_id": row["source_id"], "dataset_version": config["dataset_version"],
                    "run_id": config["run_id"], "event_time": event,
                    "sender_bank": normalise_bank(row["from_bank_raw"]), "sender_account": row["sender_account"].strip(),
                    "receiver_bank": normalise_bank(row["to_bank_raw"]), "receiver_account": row["receiver_account"].strip(),
                    "amount_paid": Decimal(row["amount_paid_raw"]), "payment_currency": row["payment_currency"],
                    "amount_received": Decimal(row["amount_received_raw"]), "receiving_currency": row["receiving_currency"],
                    "payment_format": row["payment_format"]}
            facts.append(fact)
            labels.append({"source_id": fact["source_id"], "dataset_version": config["dataset_version"],
                           "run_id": config["run_id"], "event_date": event.date(), "is_laundering": int(label)})
    expected = {r["payment_format"]: (r["transactions"], r["labelled_laundering"]) for r in prep["accepted_by_format"]}
    actual = {fmt: (n, positives[fmt]) for fmt, n in formats.items()}
    if source_rows != prep["accepted_rows"] or actual != expected:
        raise ValueError("Full local fact/label population differs from passed preparation")
    reference = root.parent / "Ibm_dataset_medium/HI-Medium_Patterns.txt"
    annotation_bytes = reference.read_bytes()
    annotation_sha = prep["source_manifest"]["source_files"]["patterns"]["sha256"]
    attempts = parse_annotations(annotation_bytes.decode("utf-8"), annotation_sha)
    cases = [json.loads(p.read_text()) for p in sorted((root / "data/q2-cloud-m00-v1").glob("*.json"))]
    result = evaluate(facts, labels, cases, report, attempts)
    result["evaluation_id"] = "eval-dev-20220901-m00-v1"
    output = root / "data/evaluation-local-m00-v1"
    output.mkdir(exist_ok=True)
    provenance = {"validation_scope": "Local checksum-verified source projection + frozen cloud cases; not a cloud evaluator run",
                                        "selected_source_sha256": digest, "annotations_sha256": annotation_sha,
                                        "full_source_rows_checked": source_rows,
                                        "full_positive_labels_checked": sum(positives.values()),
                                        "detector_report_canonical_sha256": canonical_sha(report),
                                        "evaluator_source_sha256": hashlib.sha256((root / "jobs/evaluate_q2.py").read_bytes()).hexdigest()}
    for name, body in artifact_payloads(result).items():
        (output / name).write_bytes(body)
    summary = {k: result[k] for k in ("status", "policy_version", "scope", "benchmark_status", "case_count",
                                     "detector_transaction_metrics", "amount_baseline_transaction_metrics", "annotation_metrics")}
    summary["provenance"] = provenance
    summary["artifacts"] = {name: {"sha256": hashlib.sha256((output / name).read_bytes()).hexdigest(),
                                  "bytes": (output / name).stat().st_size}
                            for name in ("metrics.json", "case_evaluation.jsonl", "attempt_evaluation.jsonl", "alert_source_ids.json")}
    (root / "aws/reviews/evaluation-local-m00-v1.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    run(Path(__file__).resolve().parents[1])
