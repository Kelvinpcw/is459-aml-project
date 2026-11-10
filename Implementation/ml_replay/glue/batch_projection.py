"""Project a completed label-free preparation and detector run for ML scoring."""

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
import json
from pathlib import Path
import re

import numpy as np
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq

from pipeline.release import safe_id, split_uri
from q2_detect import assert_label_free_columns, validate_manifest
from project_facts import FACT, FIELDS, amounts, codes
from rank_shortlist import CASE, KINDS, require

FACT_FIELDS = (*FIELDS, "payment_format")
CASE_FIELDS = ("case_id", "pattern_type", "hub", "ordered_nodes", "evidence_transaction_count",
               "unique_edge_count", "participant_count", "window_start", "window_end", "snapshot_cutoff",
               "dataset_version", "run_id", "analysis_id", "rule_version")


@dataclass(frozen=True)
class Snapshot:
    start: datetime
    end: datetime
    cases: int
    memberships: int


@dataclass(frozen=True)
class Batch:
    dataset_version: str
    run_id: str
    analysis_id: str
    facts_path: Path
    index_path: Path
    payments: int
    snapshots: tuple[Snapshot, ...]


@dataclass(frozen=True)
class Projection:
    source_ids: tuple[str, ...]
    source_ordinals: np.ndarray
    accounts: int
    cases: int
    memberships: int


def batch_inputs(manifest: dict, report: dict, mirror: Path) -> Batch:
    validate_manifest(manifest)
    dataset, run = (safe_id(manifest[key]) for key in ("dataset_version", "run_id"))
    payments = manifest["accepted_rows"]
    require(type(payments) is int and 0 < payments < np.iinfo(np.uint32).max, "Invalid fact population")
    config, stats = report["config"], report["statistics"]
    analysis = safe_id(config["analysis_id"])
    require(report["stage"] == "q2" and report["status"] == "PASSED" and report["rule_version"] == "structural-v2"
            and (report["distributed_processing"] is True or
                 (report["distributed_processing"] is False and report.get("detector_backend") == "bounded-python"))
            and report["detector_received_labels"] is False
            and (config["dataset_version"], config["run_id"]) == (dataset, run)
            and report["full_prepared_rows"] == payments and stats["scoped_rows"] == payments
            and stats["complete_for_declared_window"] is True and stats["truncated"] is False
            and config["min_counterparties"] == 5, "Require a complete structural-v2 run for the prepared facts")
    snapshots = tuple(Snapshot(datetime.fromisoformat(row["window_start"]), datetime.fromisoformat(row["window_end"]),
                               row["case_count"], row["case_evidence_rows_including_case_overlap"])
                      for row in report["snapshots"])
    for row, snap in zip(report["snapshots"], snapshots, strict=True):
        require(snap.end == datetime.combine(snap.end.date(), time.min) and
                snap.start == snap.end - timedelta(days=7) and row["snapshot_cutoff"] == snap.end.isoformat()
                and type(snap.cases) is int and snap.cases >= 0
                and type(snap.memberships) is int and snap.memberships >= snap.cases,
                "Unexpected snapshot cutoff, history window or population")
    require(0 < len(snapshots) < 255 and all((after.end - before.end).days == 1
            for before, after in zip(snapshots, snapshots[1:])), "Require consecutive daily snapshots")
    require(sum(s.cases for s in snapshots) == stats["case_count"] < np.iinfo(np.uint32).max and
            sum(s.memberships for s in snapshots) == stats["case_evidence_rows_including_case_overlap"],
            "Snapshot and detector report counts disagree")
    suffix = f"dataset_version={dataset}/run_id={run}/"
    _, facts = split_uri(manifest["inputs"]["transactions"])
    _, index = split_uri(report["outputs"]["case_index"])
    prefix = f"gold/cases/{suffix}analysis_id={analysis}/"
    attempt = report.get("attempt_id")
    if attempt:
        prefix += f"attempt={safe_id(attempt)}/"
    require(facts == f"curated/{suffix}transactions/" and index == prefix + "case_index/",
            "ML inputs must be the curated facts and case index from this run")
    require(set(FACT_FIELDS) <= set(manifest["fact_columns"]), "Detector manifest lacks ML fact fields")
    return Batch(dataset, run, analysis, mirror / facts, mirror / index, payments, snapshots)


def expect_value(column: pa.ChunkedArray, expected: str | datetime, name: str) -> None:
    if len(column):
        require(column.null_count == 0 and bool(pc.all(pc.equal(column, expected)).as_py()),
                f"{name} differs from the declared batch")


def frozen_codes(column: pa.ChunkedArray, codebook: dict[str, int], dtype: np.dtype) -> np.ndarray:
    values = column.combine_chunks().dictionary_encode()
    try:
        keys = np.array([codebook[value] for value in values.dictionary.to_pylist()], dtype=dtype)
    except KeyError as error:
        raise ValueError(f"Value outside the trained model codebook: {error.args[0]}") from error
    return keys[values.indices.to_numpy()]


def stage_facts(batch: Batch, first: date, replay: Path, aux: Path,
                currencies: dict[str, int], formats: dict[str, int]) -> tuple[tuple[str, ...], np.ndarray, dict[str, int]]:
    source_ids = [""]
    source_ordinals = np.zeros(batch.payments + 1, dtype=np.int64)
    accounts: dict[str, int] = {}
    days = np.zeros(batch.payments + 1, dtype=np.uint8)
    payment_formats = np.full(batch.payments + 1, 255, dtype=np.uint8)
    epoch = np.datetime64(first, "m")
    paths = sorted(batch.facts_path.glob("event_date=*/*.parquet"))
    require(bool(paths), f"No fact Parquet partitions under {batch.facts_path}")
    with (replay / "facts.bin").open("xb") as stream:
        for path in paths:
            day = (date.fromisoformat(path.parent.name.removeprefix("event_date=")) - first).days + 1
            require(1 <= day <= len(batch.snapshots), f"Fact partition outside the snapshots: {path}")
            parquet = pq.ParquetFile(path)
            assert_label_free_columns(parquet.schema_arrow.names)
            for record_batch in parquet.iter_batches(columns=list(FACT_FIELDS), batch_size=196_608):
                table = pa.Table.from_batches([record_batch])
                require(not any(column.null_count for column in table.columns), f"Missing required fact fields in {path}")
                expect_value(table["dataset_version"], batch.dataset_version, "Fact dataset")
                expect_value(table["run_id"], batch.run_id, "Fact run")
                ordinals = table["source_record_ordinal"]
                incoming_ids = table["source_id"].to_pylist()
                require(pa.types.is_int64(ordinals.type) and all(
                    re.fullmatch(r"[0-9a-f]{64}:[1-9][0-9]*", key) and key[65:] == str(ordinal)
                    for key, ordinal in zip(incoming_ids, ordinals.to_numpy(), strict=True)),
                    "Facts must retain the original file checksum and row ordinal")
                start, end = len(source_ids), len(source_ids) + len(incoming_ids)
                require(end <= batch.payments + 1, "Prepared facts exceed declared payment count")
                ids = np.arange(start, end, dtype=np.uint32)
                source_ids.extend(incoming_ids)
                source_ordinals[ids] = ordinals.to_numpy()
                timestamps = table["event_time"]
                require(pa.types.is_timestamp(timestamps.type) and timestamps.type.tz is None,
                        f"Expected dataset-local timestamps in {path}")
                events = timestamps.to_numpy()
                minute_times = events.astype("datetime64[m]")
                minutes = (minute_times - epoch).astype(np.int64)
                require(np.array_equal(events, minute_times) and np.all(minutes // 1440 == day - 1),
                        f"Unexpected payment timestamp in {path}")
                days[ids] = day
                payment_formats[ids] = frozen_codes(table["payment_format"], formats, np.dtype("u1"))
                records = np.zeros(len(ids), dtype=FACT)
                records["id"], records["minute"] = ids, minutes
                for side in ("sender", "receiver"):
                    key = pc.binary_join_element_wise(table[f"{side}_bank"], table[f"{side}_account"], ":")
                    records[side] = codes(key, accounts, np.dtype("<u4"))
                for direction, currency_field in (("paid", "payment_currency"), ("received", "receiving_currency")):
                    records[direction] = amounts(table, f"amount_{direction}")
                    records[f"{direction}_currency"] = frozen_codes(table[currency_field], currencies, np.dtype("<u2"))
                records.tofile(stream)
    require(np.all(days[1:] != 0), "Prepared facts are missing source records")
    require(len(set(source_ids)) == len(source_ids), "Prepared facts contain repeated source IDs")
    bank_codes: dict[str, int] = {}
    banks = np.fromiter((bank_codes.setdefault(key.split(":", 1)[0], len(bank_codes)) for key in accounts),
                        dtype="<u4", count=len(accounts))
    banks.tofile(aux / "banks.u32")
    payment_formats.tofile(aux / "formats.u8")
    days.tofile(replay / "days.u8")
    (aux / "input.json").write_text(json.dumps({"format_codes": formats}))
    return tuple(source_ids), source_ordinals, accounts


def case_partition(batch: Batch, snap: Snapshot) -> list[Path]:
    return sorted((batch.index_path / f"window_date={snap.start.date()}").glob("*.parquet"))


def stage_cases(batch: Batch, accounts: dict[str, int], replay: Path) -> tuple[int, int]:
    windows = {f"window_date={snap.start.date()}" for snap in batch.snapshots}
    require(all(path.parent.name in windows for path in batch.index_path.glob("window_date=*/*.parquet")),
            "Case index contains windows outside the detector report")
    with (replay / "cases.bin").open("xb") as rows, (replay / "case-ids.s64").open("xb") as ids:
        for day, snap in enumerate(batch.snapshots, 1):
            paths = case_partition(batch, snap)
            if not paths and snap.cases == 0:
                continue
            require(bool(paths), f"Missing case index for cutoff {snap.end.isoformat()}")
            table = pq.read_table(paths, columns=list(CASE_FIELDS), partitioning=None)
            for field, value in (("dataset_version", batch.dataset_version), ("run_id", batch.run_id),
                                 ("analysis_id", batch.analysis_id), ("rule_version", "structural-v2"),
                                 ("window_start", snap.start), ("window_end", snap.end), ("snapshot_cutoff", snap.end)):
                expect_value(table[field], value, f"Case {field}")
            require(len(table) == snap.cases and (pc.sum(table["evidence_transaction_count"]).as_py() or 0) ==
                    snap.memberships, f"Incomplete case index for cutoff {snap.end.isoformat()}")
            table = table.sort_by("case_id")
            case_ids = table["case_id"].to_pylist()
            require(len(set(case_ids)) == len(case_ids) and
                    all(re.fullmatch(r"[0-9a-f]{64}", key) is not None for key in case_ids), "Invalid case IDs")
            np.asarray(case_ids, dtype="S64").tofile(ids)
            records = np.zeros(len(table), dtype=CASE)
            records["day"] = day
            fields = ["pattern_type", "hub", "ordered_nodes", "evidence_transaction_count",
                      "unique_edge_count", "participant_count"]
            for i, row in enumerate(table.select(fields).to_pylist()):
                kind = KINDS.index(row["pattern_type"])
                nodes, degree = row["ordered_nodes"], row["unique_edge_count"]
                size = row["evidence_transaction_count"]
                require(0 < degree <= size <= batch.payments, "Invalid case evidence population")
                if kind < 2:
                    require(nodes == [row["hub"]] and degree >= 5 and row["participant_count"] == degree + 1,
                            "Invalid fan topology")
                else:
                    require(row["hub"] is None and len(set(nodes)) == len(nodes) == degree ==
                            row["participant_count"] == kind, "Invalid cycle topology")
                for j, key in enumerate(nodes):
                    bank, account = json.loads(key)
                    records["nodes"][i, j] = accounts[bank + ":" + account]
                records[i]["kind"], records[i]["size"], records[i]["degree"] = kind, size, degree
            records.tofile(rows)
    return sum(s.cases for s in batch.snapshots), sum(s.memberships for s in batch.snapshots)


def project(batch: Batch, replay: Path, aux: Path, currencies: dict[str, int],
            formats: dict[str, int]) -> Projection:
    first = batch.snapshots[0].end.date() - timedelta(days=1)
    source_ids, source_ordinals, accounts = stage_facts(batch, first, replay, aux, currencies, formats)
    cases, memberships = stage_cases(batch, accounts, replay)
    return Projection(source_ids, source_ordinals, len(accounts), cases, memberships)
