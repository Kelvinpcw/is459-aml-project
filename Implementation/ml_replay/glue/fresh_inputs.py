"""Prepare fresh CSV files and detect complete, bounded BQ2 snapshots."""

import csv
from collections import defaultdict
from dataclasses import asdict
from datetime import date, datetime, timedelta
from decimal import Decimal
import io
import json
from pathlib import Path
import re
from typing import TypedDict

import pyarrow as pa
import pyarrow.parquet as pq

from pipeline.release import BUCKET, encoded, safe_id, sha, split_uri
from prepare import AMOUNT_PATTERN, AMOUNT_PRECISION, AMOUNT_SCALE
from q2_bundle_shards import SHARD_BYTES, pack_shards
from q2_detect import Config, DETECTOR_COLUMNS, assert_label_free_columns, build_cases, validate_manifest
from q2_snapshots import schedule


TRANSACTION_HEADER = ("Timestamp", "From Bank", "Account", "To Bank", "Account", "Amount Received",
                      "Receiving Currency", "Amount Paid", "Payment Currency", "Payment Format")
ACCOUNT_HEADER = ("Bank Name", "Bank ID", "Account Number", "Entity ID", "Entity Name")
MAX_PAYMENTS = 50_000
MAX_TRANSACTION_FILE_BYTES = 16 * 1024 * 1024
MAX_ACCOUNT_FILE_BYTES = 128 * 1024 * 1024
MAX_CYCLE_DEGREE = 64
ANALYSIS_ID = "fresh-bq2-v1"
TIMESTAMP_POLICY = "dataset-local; source timezone unspecified"
RawFact = dict[str, str | int | bool | datetime | Decimal | None]


class CsvReference(TypedDict):
    key: str
    sha256: str


class ReadyInputs(TypedDict):
    schema_version: int
    dataset_version: str
    history_start: str
    batch_start: str
    cutoff: str
    files: list[CsvReference]
    accounts: CsvReference


def parquet_fields(columns: list[str], types: dict[str, pa.DataType]) -> pa.Schema:
    return pa.schema([(name, types.get(name, pa.string())) for name in columns])


FACT_SCHEMA = parquet_fields(DETECTOR_COLUMNS + [
    "source_record_ordinal", "timestamp_raw", "from_bank_raw", "to_bank_raw", "sender_account_raw",
    "receiver_account_raw",
    "amount_paid_raw", "amount_received_raw"
], {
    "event_time": pa.timestamp("us"),
    "source_record_ordinal": pa.int64(),
    **{f"amount_{side}": pa.decimal128(AMOUNT_PRECISION, AMOUNT_SCALE) for side in ("paid", "received")},
    **{f"{side}_entity_unknown": pa.bool_() for side in ("sender", "receiver")},
})

INDEX_SCHEMA = parquet_fields([
    "case_id", "pattern_type", "hub", "ordered_nodes", "participant_count", "unique_edge_count",
    "evidence_transaction_count", "first_event_time", "last_event_time", "dataset_version", "run_id",
    "analysis_id", "rule_version", "window_start", "window_end", "snapshot_cutoff", "bundle_uri",
    "bundle_member", "bundle_sha256",
], {
    "ordered_nodes": pa.list_(pa.string()),
    **{name: pa.int64() for name in ("participant_count", "unique_edge_count", "evidence_transaction_count")},
    **{name: pa.timestamp("us") for name in ("first_event_time", "last_event_time", "window_start",
                                           "window_end", "snapshot_cutoff")},
})


def write_object(path: Path, body: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(body)


def verified_csv(mirror: Path, reference: CsvReference, maximum_bytes: int) -> io.StringIO:
    key = reference["key"]
    split_uri(f"s3://{BUCKET}/{key}")
    path = mirror / key
    if (not key.startswith("fresh-bq2/incoming/") or not key.endswith(".csv") or
            not path.resolve().is_relative_to(mirror.resolve())):
        raise ValueError(f"CSV must be inside the batch input namespace: {key}")
    with path.open("rb") as stream:
        raw = stream.read(maximum_bytes + 1)
    if len(raw) > maximum_bytes or sha(raw) != reference["sha256"]:
        raise ValueError(f"CSV exceeds the approved byte limit or differs from the manifest checksum: {key}")
    return io.StringIO(raw.decode("utf-8-sig"), newline="")


def normalized_bank(value: str) -> str:
    trimmed = value.strip()
    if not re.fullmatch(r"[0-9]+", trimmed):
        raise ValueError("Bank ID must contain digits")
    return trimmed.lstrip("0") or "0"


def money(value: str) -> Decimal:
    if not re.fullmatch(AMOUNT_PATTERN, value):
        raise ValueError(f"Amount does not fit decimal({AMOUNT_PRECISION},{AMOUNT_SCALE}): {value!r}")
    result = Decimal(value)
    if result < 0 or result.adjusted() >= AMOUNT_PRECISION - AMOUNT_SCALE:
        raise ValueError(f"Amount is outside the model's supported monetary domain: {value!r}")
    return result


def transaction(raw: list[str], event: datetime, source_hash: str, ordinal: int,
                dataset: str, run: str) -> RawFact:
    timestamp, from_bank, sender, to_bank, receiver, received, currency_received, paid, currency_paid, form = raw[:10]
    if not all(value.strip() for value in (sender, receiver, currency_received, currency_paid, form)):
        raise ValueError("Accounts, currencies and payment format must be populated")
    return {
        "dataset_version": dataset, "run_id": run, "source_id": f"{source_hash}:{ordinal}",
        "source_record_ordinal": ordinal, "timestamp_raw": timestamp, "event_time": event,
        "from_bank_raw": from_bank, "to_bank_raw": to_bank,
        "sender_account_raw": sender, "receiver_account_raw": receiver, "sender_bank": normalized_bank(from_bank),
        "sender_account": sender.strip(), "receiver_bank": normalized_bank(to_bank),
        "receiver_account": receiver.strip(), "amount_received_raw": received,
        "amount_paid_raw": paid, "amount_received": money(received), "amount_paid": money(paid),
        "receiving_currency": currency_received.strip(), "payment_currency": currency_paid.strip(),
        "payment_format": form.strip(),
    }


def account_mappings(mirror: Path, reference: CsvReference) -> dict[tuple[str, str], tuple[str, str]]:
    mappings: dict[tuple[str, str], tuple[str, str]] = {}
    with verified_csv(mirror, reference, MAX_ACCOUNT_FILE_BYTES) as stream:
        reader = csv.reader(stream, strict=True)
        if tuple(next(reader, [])) != ACCOUNT_HEADER:
            raise ValueError("Unexpected account mapping header")
        for ordinal, row in enumerate(reader, 1):
            if len(row) != len(ACCOUNT_HEADER):
                raise ValueError(f"Account mapping row {ordinal} has the wrong number of fields")
            _, bank, account, entity, name = row
            key = normalized_bank(bank), account.strip()
            if not key[1] or not entity.strip() or key in mappings:
                raise ValueError(f"Missing or duplicate account/entity mapping at row {ordinal}")
            mappings[key] = entity, name
    return mappings


def prepare_batch(ready: ReadyInputs, batch_id: str, mirror: Path, work: Path) -> Path:
    """Materialize label-free Parquet and reconcile all input rows against the cutoff."""
    dataset, run = safe_id(ready["dataset_version"]), safe_id(batch_id)
    first, start, cutoff = (date.fromisoformat(ready[key]) for key in ("history_start", "batch_start", "cutoff"))
    if ready.get("schema_version") != 1 or not first <= start < cutoff or not 1 <= (cutoff - first).days <= 29:
        raise ValueError("Expected a version 1 batch with up to 29 days of declared history and an exclusive cutoff")
    files: list[CsvReference] = ready["files"]
    if (not 1 <= len(files) <= 32 or len({ref["sha256"] for ref in files}) != len(files)
            or len({ref["key"] for ref in files}) != len(files)):
        raise ValueError("Expected 1–32 different transaction CSVs with distinct keys and checksums")
    records: dict[date, list[RawFact]] = defaultdict(list)
    scanned = before = after = 0
    for ref in sorted(files, key=lambda item: item["sha256"]):
        with verified_csv(mirror, ref, MAX_TRANSACTION_FILE_BYTES) as stream:
            reader = csv.reader(stream, strict=True)
            header = tuple(next(reader, []))
            if header not in (TRANSACTION_HEADER, (*TRANSACTION_HEADER, "Is Laundering")):
                raise ValueError(f"Unexpected transaction header in {ref['key']}")
            for ordinal, raw in enumerate(reader, 1):
                scanned += 1
                if scanned > MAX_PAYMENTS:
                    raise ValueError(f"Fresh BQ2 is bounded to {MAX_PAYMENTS:,} input transaction rows")
                try:
                    if len(raw) != len(header):
                        raise ValueError("Wrong number of transaction fields")
                    event = datetime.strptime(raw[0], "%Y/%m/%d %H:%M")
                    day = event.date()
                    if day < first:
                        before += 1
                    elif day >= cutoff:
                        after += 1
                    else:
                        records[day].append(transaction(raw, event, ref["sha256"], ordinal, dataset, run))
                except ValueError as error:
                    raise ValueError(f"{ref['key']} data row {ordinal}: {error}") from error
    accepted = scanned - before - after
    if not any(day >= start for day in records):
        raise ValueError("The declared new batch contains no transactions before its cutoff")
    accounts = account_mappings(mirror, ready["accounts"])
    prefix = f"curated/dataset_version={dataset}/run_id={run}/transactions/"
    for day, daily in sorted(records.items()):
        for row in daily:
            for side in ("sender", "receiver"):
                pair = str(row[f"{side}_bank"]), str(row[f"{side}_account"])
                mapping = accounts.get(pair)
                row[f"{side}_entity_id"], row[f"{side}_entity_name"] = mapping or (None, None)
                row[f"{side}_entity_unknown"] = mapping is None
        output = mirror / prefix / f"event_date={day}" / "part-00000.parquet"
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("xb") as stream:
            pq.write_table(pa.Table.from_pylist(daily, schema=FACT_SCHEMA), stream)
    manifest = {
        "schema_version": 1, "stage": "detector_inputs", "preparation_status": "PASSED",
        "dataset_version": dataset, "run_id": run, "accepted_rows": accepted,
        "fact_columns": [*FACT_SCHEMA.names, "event_date"],
        "amount_policy": {"precision": AMOUNT_PRECISION, "scale": AMOUNT_SCALE},
        "inputs": {"transactions": f"s3://{BUCKET}/{prefix}"}, "timestamp_policy": TIMESTAMP_POLICY,
    }
    validate_manifest(manifest)
    write_object(work / "preparation-report.json", encoded({
        "status": "PASSED", "dataset_version": dataset, "run_id": run,
        "input_rows": scanned, "accepted_rows": accepted, "before_history_rows": before,
        "at_or_after_cutoff_rows": after, "new_rows": sum(len(rows) for day, rows in records.items() if day >= start),
        "history_start": first.isoformat(), "batch_start": start.isoformat(), "cutoff": cutoff.isoformat(),
    }))
    path = work / "detector-inputs.json"
    write_object(path, encoded(manifest))
    return path


def node(row: RawFact, side: str) -> str:
    return json.dumps([row[f"{side}_bank"], row[f"{side}_account"]], separators=(",", ":"), ensure_ascii=False)


def enforce_cycle_degree(rows: list[RawFact]) -> None:
    incoming: dict[str, set[str]] = defaultdict(set)
    outgoing: dict[str, set[str]] = defaultdict(set)
    for row in rows:
        sender, receiver = node(row, "sender"), node(row, "receiver")
        if sender != receiver:
            incoming[receiver].add(sender)
            outgoing[sender].add(receiver)
            if max(len(incoming[receiver]), len(outgoing[sender])) > MAX_CYCLE_DEGREE:
                raise ValueError(f"Snapshot exceeds the bounded detector's {MAX_CYCLE_DEGREE}-peer cycle guard")


def canonical_index(case: dict, config: Config) -> dict:
    """Use structural-v2 hub/cycle identities for the bounded subset of that graph."""
    def normalized_node(value: str) -> str:
        return json.dumps(json.loads(value), separators=(",", ":"), ensure_ascii=False)

    hub = normalized_node(case["hub"]) if case["hub"] else None
    nodes = [hub] if hub else [normalized_node(value) for value in case["ordered_nodes"]]
    first = nodes.index(min(nodes))
    ordered = nodes[first:] + nodes[:first]
    identity = {
        "rule_version": "structural-v2", "dataset_version": config.dataset_version, "run_id": config.run_id,
        "window_start": config.window_start, "window_end": config.window_end, "snapshot_cutoff": config.snapshot_cutoff,
        "min_counterparties": config.min_counterparties, "max_cycle_degree": MAX_CYCLE_DEGREE,
    }
    topology = {"pattern_type": case["pattern_type"], "ordered_nodes": ordered}
    case_id = sha((json.dumps(identity, sort_keys=True, separators=(",", ":")) +
                   json.dumps(topology, separators=(",", ":"), ensure_ascii=False)).encode())
    return {
        **{name: case[name] for name in ("participant_count", "unique_edge_count", "evidence_transaction_count",
                                        "first_event_time", "last_event_time", "dataset_version", "run_id",
                                        "analysis_id")},
        **topology, "case_id": case_id, "hub": hub, "rule_version": identity["rule_version"],
        **{name: datetime.fromisoformat(identity[name]) for name in ("window_start", "window_end", "snapshot_cutoff")},
    }


def snapshot_index(rows: list[RawFact], config: Config, prefix: str, mirror: Path) -> dict:
    enforce_cycle_degree(rows)
    cases, stats = build_cases(rows, config)
    by_source = {row["source_id"]: row for row in rows}
    pairs = sorted(((canonical_index(case, config), case) for case in cases), key=lambda pair: pair[0]["case_id"])
    export_rows = (
        {**index, **row, "src": node(row, "sender"), "dst": node(row, "receiver")}
        for index, case in pairs for evidence in case["transactions"]
        for row in (by_source[evidence["source_id"]],)
    )
    shards = pack_shards(export_rows, BUCKET, prefix, config.window_end[:10], 0,
                         lambda key, body: write_object(mirror / key, body), SHARD_BYTES)
    locators = {case_id: {"bundle_uri": uri, "bundle_member": member, "bundle_sha256": checksum}
                for case_id, uri, member, checksum in shards}
    if len(locators) != len(pairs):
        raise ValueError("Bounded detector evidence export did not match its case index")
    index_rows = [{**index, **locators[index["case_id"]]} for index, _ in pairs]
    path = mirror / prefix / "case_index" / f"window_date={config.window_start[:10]}" / "part-00000.parquet"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        pq.write_table(pa.Table.from_pylist(index_rows, schema=INDEX_SCHEMA), stream)
    return stats


def detect_batch(manifest_path: Path, mirror: Path, work: Path, first_day: date, cutoff: date) -> Path:
    """Build complete overlapping seven-day snapshots and pin their evidence bundles."""
    manifest = json.loads(manifest_path.read_bytes())
    validate_manifest(manifest)
    if not 1 <= (cutoff - first_day).days <= 29:
        raise ValueError("Expected 1–29 daily snapshots in the bounded fresh BQ2 flow")
    dataset, run = safe_id(manifest["dataset_version"]), safe_id(manifest["run_id"])
    _, facts = split_uri(manifest["inputs"]["transactions"])
    expected = f"curated/dataset_version={dataset}/run_id={run}/transactions/"
    if facts != expected:
        raise ValueError("Detector facts must come from this prepared batch")
    paths = sorted((mirror / facts).glob("event_date=*/*.parquet"))
    records: list[RawFact] = []
    for path in paths:
        parquet = pq.ParquetFile(path)
        assert_label_free_columns(parquet.schema_arrow.names)
        if parquet.schema_arrow != FACT_SCHEMA or len(records) + parquet.metadata.num_rows > MAX_PAYMENTS:
            raise ValueError("Prepared fact schema or population exceeds the bounded detector contract")
        records.extend(parquet.read(columns=DETECTOR_COLUMNS).to_pylist())
    if (len(records) != manifest["accepted_rows"] or len({row["source_id"] for row in records}) != len(records)
            or any(not first_day <= row["event_time"].date() < cutoff for row in records)):
        raise ValueError("Prepared fact population differs from the declared batch")
    prefix = f"gold/cases/dataset_version={dataset}/run_id={run}/analysis_id={ANALYSIS_ID}/"
    ends = ((first_day + timedelta(days=1)).isoformat(), cutoff.isoformat())
    windows = schedule(*ends)
    snapshots = []
    for start, end in windows:
        config = Config(dataset, run, ANALYSIS_ID, start.isoformat(), end.isoformat(), end.isoformat())
        selected = [row for row in records if start <= row["event_time"] < end]
        stats = snapshot_index(selected, config, prefix, mirror)
        snapshots.append({
            "window_start": config.window_start, "window_end": config.window_end,
            "snapshot_cutoff": config.snapshot_cutoff, **stats,
            "history_complete": first_day <= start.date(), "history_available_from": first_day.isoformat(),
        })
    report = {
        "schema_version": 2, "stage": "q2", "status": "PASSED", "rule_version": "structural-v2",
        "distributed_processing": False, "detector_backend": "bounded-python",
        "detector_received_labels": False, "full_prepared_rows": len(records), "case_bundle_schema_version": 3,
        "config": {**asdict(config), "window_start": windows[0][0].isoformat(), "max_cycle_degree": MAX_CYCLE_DEGREE},
        "snapshots": snapshots,
        "statistics": {
            "scoped_rows": len(records), "case_count": sum(row["case_count"] for row in snapshots),
            "case_evidence_rows_including_case_overlap": sum(row["case_evidence_rows_including_case_overlap"]
                                                             for row in snapshots),
            "complete_for_declared_window": True, "truncated": False,
        },
        "outputs": {name: f"s3://{BUCKET}/{prefix}{name}/" for name in ("case_index", "bundles")},
    }
    path = work / "detector-report.json"
    write_object(path, encoded(report))
    return path
