"""Independent streaming reference for the one-day USD Q1 demo queries."""
import collections
import csv
import gzip
import hashlib
import json
from pathlib import Path


def audit(input_dir):
    manifest = json.loads((input_dir / "manifest.json").read_text())
    source = input_dir / "transactions.csv.gz"
    with source.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    if digest != manifest["artifacts"][source.name]["sha256"]:
        raise ValueError("Input checksum differs from ingestion manifest")
    segments = collections.defaultdict(lambda: [0, 0])
    formats = collections.defaultdict(lambda: [0, 0])
    total = positive = source_rows = 0
    with gzip.open(source, "rt", newline="") as stream:
        for row in csv.DictReader(stream):
            source_rows += 1
            if row["payment_currency"] != "US Dollar":
                continue
            sender = row["from_bank_raw"].strip().lstrip("0") or "0"
            receiver = row["to_bank_raw"].strip().lstrip("0") or "0"
            key = (sender, receiver, row["payment_format"])
            label = int(row["is_laundering_raw"])
            segments[key][0] += 1
            segments[key][1] += label
            formats[row["payment_format"]][0] += 1
            formats[row["payment_format"]][1] += label
            total += 1
            positive += label
    if source_rows != manifest["counts"]["selected_records"]:
        raise ValueError("Source population differs from manifest")
    baseline = positive / total
    candidates = []
    for key, (n, l) in segments.items():
        if n < 1000:
            continue
        candidates.append({"sender_bank": key[0], "receiver_bank": key[1], "payment_format": key[2],
                           "n": n, "l": l, "baseline_n": total, "baseline_l": positive,
                           "laundering_rate": l / n, "risk_lift": (l / n) / baseline})
    candidates.sort(key=lambda r: (-r["risk_lift"], -r["n"], r["sender_bank"],
                                   r["receiver_bank"], r["payment_format"]))
    return {"source_input_sha256": digest, "source_rows": source_rows,
            "payment_currency": "US Dollar", "baseline_n": total, "baseline_l": positive,
            "support_threshold": 1000, "eligible_segments": len(candidates),
            "eligible_segment_positive_labels": sum(r["l"] for r in candidates),
            "eligible_segment_transactions": sum(r["n"] for r in candidates),
            "format_counts": {k: {"n": v[0], "l": v[1]} for k, v in sorted(formats.items())},
            "top_20": candidates[:20]}


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    result = audit(root / "data/development-20220901")
    output = root / "aws/reviews/q1-usd-source-reference.json"
    output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({k: v for k, v in result.items() if k not in ("top_20", "format_counts")}))
