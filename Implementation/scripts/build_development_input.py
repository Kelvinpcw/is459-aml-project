#!/usr/bin/env python3
"""Create a date-selected, stable-ID ingestion copy without changing originals."""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import io
import json
import shutil
from collections import Counter
from contextlib import contextmanager
from datetime import date, datetime
from functools import lru_cache
from pathlib import Path

ORIGINAL_HEADER = [
    "Timestamp", "From Bank", "Account", "To Bank", "Account",
    "Amount Received", "Receiving Currency", "Amount Paid", "Payment Currency",
    "Payment Format", "Is Laundering",
]
INGESTION_HEADER = [
    "source_id", "source_record_ordinal", "timestamp_raw", "from_bank_raw",
    "sender_account", "to_bank_raw", "receiver_account", "amount_received_raw",
    "receiving_currency", "amount_paid_raw", "payment_currency", "payment_format",
    "is_laundering_raw",
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


@contextmanager
def deterministic_gzip_text(path: Path):
    with path.open("xb") as binary:
        with gzip.GzipFile(filename="", mode="wb", fileobj=binary, mtime=0) as compressed:
            with io.TextIOWrapper(compressed, encoding="utf-8", newline="") as text:
                yield text


@lru_cache(maxsize=100_000)
def parse_timestamp(value: str) -> datetime:
    return datetime.strptime(value, "%Y/%m/%d %H:%M")


def build_input(transactions: Path, accounts: Path, patterns: Path,
                output: Path, start: date, end: date) -> dict:
    """End is exclusive. Full-file scanning is required because times are unsorted."""
    if start >= end:
        raise ValueError("start must be before the exclusive end date")
    if output.exists():
        raise FileExistsError(f"Choose a new output directory: {output}")
    sources = {"transactions": transactions, "accounts": accounts, "patterns": patterns}
    initial_stats = {key: (p.stat().st_size, p.stat().st_mtime_ns)
                     for key, p in sources.items()}
    checksums = {key: sha256(p) for key, p in sources.items()}
    dataset_digest = hashlib.sha256(json.dumps(checksums, sort_keys=True).encode()).hexdigest()
    dataset_version = "ibm-hi-medium-" + dataset_digest[:16]
    output.mkdir(parents=True)
    counts = Counter({key: 0 for key in ("source_records", "selected_records",
                                        "outside_development_scope", "ingestion_quarantined")})
    formats: dict[str, Counter] = {}
    days = Counter()
    tx_path = output / "transactions.csv.gz"
    quarantine_path = output / "ingestion-quarantine.jsonl.gz"
    try:
        with transactions.open(encoding="utf-8", newline="") as source, \
                deterministic_gzip_text(tx_path) as accepted, \
                deterministic_gzip_text(quarantine_path) as rejected:
            reader = csv.reader(source, strict=True)
            if next(reader) != ORIGINAL_HEADER:
                raise ValueError("Unexpected source header; positional account mapping must be reviewed")
            writer = csv.writer(accepted, lineterminator="\n")
            writer.writerow(INGESTION_HEADER)
            for ordinal, row in enumerate(reader, start=1):
                counts["source_records"] += 1
                source_id = f"{checksums['transactions']}:{ordinal}"
                reason = None
                if len(row) != len(ORIGINAL_HEADER):
                    reason = "wrong_column_count"
                else:
                    try:
                        event_time = parse_timestamp(row[0])
                    except ValueError:
                        reason = "invalid_timestamp"
                if reason:
                    counts["ingestion_quarantined"] += 1
                    rejected.write(json.dumps({"source_id": source_id,
                                               "source_record_ordinal": ordinal,
                                               "reason": reason, "raw_fields": row}) + "\n")
                    continue
                if not start <= event_time.date() < end:
                    counts["outside_development_scope"] += 1
                    continue
                writer.writerow([source_id, ordinal, *row])
                counts["selected_records"] += 1
                days[event_time.date().isoformat()] += 1
                label = row[10]
                counts[f"selected_label_{label}"] += 1
                group = formats.setdefault(row[9], Counter())
                group["transactions"] += 1
                group["labelled_laundering"] += int(label == "1")
                group["invalid_labels"] += int(label not in ("0", "1"))
                if ordinal % 2_000_000 == 0:
                    print(f"Scanned source record {ordinal:,}; selected {counts['selected_records']:,}", flush=True)
        if counts["selected_records"] == 0:
            raise ValueError("The selected development period contains no transactions")
        assert counts["source_records"] == (counts["selected_records"] +
                                             counts["outside_development_scope"] +
                                             counts["ingestion_quarantined"])
        with accounts.open("rb") as source, (output / "accounts.csv.gz").open("xb") as target:
            with gzip.GzipFile(filename="", mode="wb", fileobj=target, mtime=0) as compressed:
                shutil.copyfileobj(source, compressed)
        for key, path in sources.items():
            if (path.stat().st_size, path.stat().st_mtime_ns) != initial_stats[key]:
                raise RuntimeError(f"Source changed during ingestion: {path.name}")
        manifest = {
            "schema_version": 1,
            "dataset_version": dataset_version,
            "development_scope": {"start_inclusive": start.isoformat(), "end_exclusive": end.isoformat()},
            "timestamp_policy": "dataset-local; source timezone unspecified",
            "source_files": {key: {"filename": path.name, "sha256": checksums[key],
                                    "size_bytes": initial_stats[key][0]}
                             for key, path in sources.items()},
            "counts": dict(counts),
            "selected_dates": dict(sorted(days.items())),
            "source_id_policy": "original transaction file SHA-256 + colon + 1-based CSV data-record ordinal",
            "ingestion_columns": INGESTION_HEADER,
            "artifacts": {p.name: {"sha256": sha256(p), "size_bytes": p.stat().st_size}
                          for p in (tx_path, quarantine_path, output / "accounts.csv.gz")},
            "q1_source_reference_by_format": {key: dict(value) for key, value in sorted(formats.items())},
            "reference_note": "Raw selected-input counts; reconcile with accepted facts after preparation quarantines.",
        }
        (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
        return manifest
    except BaseException:
        (output / "INCOMPLETE.txt").write_text("Ingestion did not finish. Do not upload or process this directory.\n")
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--transactions", type=Path, required=True)
    parser.add_argument("--accounts", type=Path, required=True)
    parser.add_argument("--patterns", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--start", type=date.fromisoformat, default=date(2022, 9, 1))
    parser.add_argument("--end", type=date.fromisoformat, default=date(2022, 9, 2))
    args = parser.parse_args()
    manifest = build_input(args.transactions, args.accounts, args.patterns,
                           args.output, args.start, args.end)
    print(json.dumps({"dataset_version": manifest["dataset_version"],
                      "counts": manifest["counts"], "output": str(args.output)}, indent=2))


if __name__ == "__main__":
    main()
