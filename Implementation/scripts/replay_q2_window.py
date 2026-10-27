"""Trusted local preparation projection, followed by the production Q2 core.

This verification harness can read ingestion files; the deployed Q2 role cannot.
Only the explicit transaction columns below cross into the detector. Label values
and pattern annotations are never inspected, projected, scored or used to pick scope.
"""
from collections import Counter, defaultdict
import csv
from dataclasses import asdict
from datetime import datetime
from decimal import Decimal
import gzip
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "jobs"))
from q2_detect import Config, build_cases, encode_case, validate_manifest

TRANSACTION_PROJECTION = ["source_id", "timestamp_raw", "from_bank_raw", "sender_account",
                          "to_bank_raw", "receiver_account", "amount_received_raw",
                          "receiving_currency", "amount_paid_raw", "payment_currency", "payment_format"]


def bank(raw):
    value = raw.strip()
    if not value.isascii() or not value.isdigit():
        raise ValueError("Invalid bank identity in verified preparation input")
    return value.lstrip("0") or "0"


def replay(root):
    inputs = root / "data/development-20220901"
    ingestion = json.loads((inputs / "manifest.json").read_text())
    handoff = json.loads((root / "aws/manifests/q2-input-v2.json").read_text())
    validate_manifest(handoff)
    config = Config(handoff["dataset_version"], handoff["run_id"], "q2-dev-20220901-m00-v1",
                    "2022-09-01T00:00:00", "2022-09-01T00:01:00", "2022-09-01T00:01:00")
    start, end, cutoff = config.times()
    checksums = {}
    for name in ("transactions.csv.gz", "accounts.csv.gz"):
        with (inputs / name).open("rb") as stream:
            digest = hashlib.file_digest(stream, "sha256").hexdigest()
        if digest != ingestion["artifacts"][name]["sha256"]:
            raise ValueError("Input checksum differs from ingestion record")
        checksums[name] = digest
    records, needed = [], set()
    source_rows = 0
    with gzip.open(inputs / "transactions.csv.gz", "rt", newline="") as stream:
        reader = csv.reader(stream)
        header = next(reader)
        positions = [header.index(c) for c in TRANSACTION_PROJECTION]
        for raw in reader:
            source_rows += 1
            # Project immediately; no other transaction fields are accessed.
            row = dict(zip(TRANSACTION_PROJECTION, (raw[i] for i in positions)))
            event = datetime.strptime(row["timestamp_raw"], "%Y/%m/%d %H:%M")
            if not start <= event < end or event > cutoff:
                continue
            record = {"dataset_version": config.dataset_version, "run_id": config.run_id,
                      "source_id": row["source_id"], "event_time": event,
                      "sender_bank": bank(row["from_bank_raw"]), "sender_account": row["sender_account"].strip(),
                      "receiver_bank": bank(row["to_bank_raw"]), "receiver_account": row["receiver_account"].strip(),
                      "amount_paid": Decimal(row["amount_paid_raw"]).quantize(Decimal("0.00000001")),
                      "amount_received": Decimal(row["amount_received_raw"]).quantize(Decimal("0.00000001")),
                      **{c: row[c] for c in ("receiving_currency", "payment_currency", "payment_format")}}
            records.append(record)
            if len(records) > config.max_window_rows:
                raise ValueError("Local window exceeds reviewed bound")
            for side in ("sender", "receiver"):
                needed.add((record[f"{side}_bank"], record[f"{side}_account"]))
    if source_rows != handoff["accepted_rows"]:
        raise ValueError("Local source population differs from passed preparation")
    mappings, account_rows = {}, 0
    with gzip.open(inputs / "accounts.csv.gz", "rt", newline="") as stream:
        reader = csv.DictReader(stream)
        for row in reader:
            account_rows += 1
            key = bank(row["Bank ID"]), row["Account Number"].strip()
            if key in needed:
                if key in mappings:
                    raise ValueError("Duplicate account/entity key")
                mappings[key] = row["Entity ID"], row["Entity Name"]
    for record in records:
        for side in ("sender", "receiver"):
            mapping = mappings.get((record[f"{side}_bank"], record[f"{side}_account"]))
            record.update({f"{side}_entity_id": mapping[0] if mapping else None,
                           f"{side}_entity_name": mapping[1] if mapping else None,
                           f"{side}_entity_unknown": mapping is None})
    cases, stats = build_cases(records, config)
    # Independently reconcile every emitted case against all selected source rows.
    pair_sources = defaultdict(set)
    for r in records:
        pair = ((r["sender_bank"], r["sender_account"]), (r["receiver_bank"], r["receiver_account"]))
        if pair[0] != pair[1]:
            pair_sources[pair].add(r["source_id"])
    case_sources = set()
    for case in cases:
        pairs = [(tuple(json.loads(e["source"])), tuple(json.loads(e["target"]))) for e in case["edges"]]
        expected = set().union(*(pair_sources[pair] for pair in pairs))
        actual = [r["source_id"] for r in case["transactions"]]
        if len(actual) != len(set(actual)) or set(actual) != expected:
            raise ValueError("Case does not preserve all and only its supporting transactions")
        if len(case["nodes"]) != len({n["node_id"] for n in case["nodes"]}):
            raise ValueError("Repeated node in simple pattern")
        case_sources.update(actual)
    output = root / "data/q2-local-m00-v1"
    output.mkdir(exist_ok=True)
    inventory = []
    for case in cases:
        path = output / (case["case_id"] + ".json")
        body = encode_case(case)
        path.write_bytes(body)
        inventory.append({k: case[k] for k in ("case_id", "pattern_type", "participant_count",
                                              "unique_edge_count", "evidence_transaction_count")})
        inventory[-1].update({"bundle_bytes": len(body), "bundle_sha256": hashlib.sha256(body).hexdigest()})
    result = {"status": "PASSED", "validation_scope": "Local preparation projection + production Q2 core; not a cloud run",
              "config": asdict(config), "checksums_verified": checksums,
              "transaction_columns_projected": TRANSACTION_PROJECTION, "source_rows_scanned": source_rows,
              "account_rows_scanned": account_rows, "statistics": stats,
              "unique_supporting_transactions": len(case_sources),
              "all_case_evidence_reconciled": True,
              "case_inventory": inventory,
              "largest_bundle_bytes": max((c["bundle_bytes"] for c in inventory), default=0),
              "total_bundle_bytes": sum(c["bundle_bytes"] for c in inventory)}
    review = root / "aws/reviews/q2-local-replay-m00-v1.json"
    review.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({k: v for k, v in result.items() if k != "case_inventory"}, indent=2))


if __name__ == "__main__":
    replay(Path(__file__).resolve().parents[1])
