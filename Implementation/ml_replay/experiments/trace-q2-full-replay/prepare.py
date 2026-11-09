"""Project checksum-verified AWS Parquet into exact, label-free replay inputs."""
from datetime import datetime
from hashlib import file_digest, md5
import json
import os
from pathlib import Path
import sys

import numpy as np
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parent
LOCAL = ROOT.parent / "trace-local-release"
OLD = ROOT.parent / "trace-fan-out-experiment"
PROJECT = Path(os.environ["TRACE_PROJECT_ROOT"]).resolve()
sys.path.insert(0, str(PROJECT / "Implementation"))
sys.path.insert(0, str(LOCAL / "fanout-replay"))
sys.path.insert(0, str(LOCAL))

from pipeline.release import load_current, split_uri, verify_ref
from local_data import LocalObjects
from stage import SOURCE_COUNT, verify_tag, require, IDENTITY, FACT_FIELDS, EPOCH

KINDS = ("fan_in", "fan_out", "cycle_2", "cycle_3", "cycle_4")
HOURS = 60
DAY = 24 * HOURS
OBJECTS = LocalObjects(LOCAL / "mirror")
RELEASE = load_current(OBJECTS)
PREP = verify_ref(OBJECTS, RELEASE["reports"]["preparation"])
CASE = np.dtype([("kind", "u1"), ("day", "u1"), ("pad", "<u2"), ("size", "<u4"),
                 ("degree", "<u4"), ("nodes", "<u4", (4,))])
FACT = np.dtype([("paid", "<u8", (2,)), ("received", "<u8", (2,)), ("id", "<u4"), ("sender", "<u4"),
                 ("receiver", "<u4"), ("minute", "<u4"), ("paid_currency", "<u2"),
                 ("received_currency", "<u2"), ("pad", "<u4")])
CASE_FIELDS = ("case_id", "pattern_type", "hub", "ordered_nodes", "evidence_transaction_count",
               "unique_edge_count", "participant_count", "first_event_time", "last_event_time",
               "window_start", "window_end", "snapshot_cutoff", "dataset_version", "run_id",
               "analysis_id", "rule_version")
assert CASE.itemsize == 28 and FACT.itemsize == 56


def inventory() -> dict[Path, tuple[int, str]]:
    rows = {}
    for root, path in ((OLD / "published-parquet", OLD / "published-files.json"),
                       (OBJECTS.root, LOCAL / "base-inventory.json")):
        for obj in json.loads(path.read_text()):
            target = root / obj["path"]
            rows[target] = (obj["size"], obj["etag"])
    return rows


def sources(kind: str, day: int) -> list[Path]:
    zone = {"facts": "transactions", "labels": "labels"}[kind]
    root = OLD / "published-parquet" / kind if day <= 16 else OBJECTS.root / split_uri(PREP["outputs"][zone])[1]
    partition = root / f"event_date=2022-09-{day:02}"
    paths = sorted(partition.glob("*.parquet"))
    expected = {27: 14, 28: 2}.get(day, 16)
    require(len(paths) == expected, f"Expected {expected} shards under {partition}")
    return paths


def verified_file(path: Path, expected: dict[Path, tuple[int, str]]) -> None:
    size, etag = expected[path]
    require(path.stat().st_size == size and (len(etag) == 32 or etag.endswith("-1")),
            f"Unexpected S3 size or multipart contract for {path}")
    with path.open("rb") as stream:
        digest = file_digest(stream, lambda: md5(usedforsecurity=False))
    # Spark used a single-part multipart upload for some of these files.
    observed = (md5(digest.digest(), usedforsecurity=False).hexdigest() + "-1"
                if etag.endswith("-1") else digest.hexdigest())
    require(observed == etag, f"Local file differs from the verified S3 object {path}")


def minutes(table: pa.Table) -> np.ndarray:
    epoch = np.datetime64(EPOCH, "ns").astype(np.int64)
    seconds = table["event_time"].to_numpy().astype(np.int64) - epoch
    require(bool(np.all(seconds % 60_000_000_000 == 0)), "Unexpected sub-minute fact timestamp")
    return (seconds // 60_000_000_000).astype(np.int32)


def coded(column: pa.ChunkedArray, codebook: dict[str, int], dtype: np.dtype) -> np.ndarray:
    values = column.combine_chunks().dictionary_encode()
    require(values.null_count == 0, "Cannot code missing published fact fields")
    keys = np.array([codebook.setdefault(key, len(codebook)) for key in values.dictionary.to_pylist()],
                    dtype=dtype)
    return keys[values.indices.to_numpy()]


def decimal_words(table: pa.Table, key: str) -> np.ndarray:
    col = table[key].combine_chunks()
    require(col.type == pa.decimal128(38, 8) and col.null_count == 0, f"Unexpected {key} amount contract")
    words = np.frombuffer(col.buffers()[1], dtype="<u8", count=2 * len(col),
                          offset=16 * col.offset).reshape(-1, 2)
    require(not bool(np.any(words[:, 1] >> np.uint64(63))), f"Negative {key} amount")
    return words


def clean_facts(out: Path, checks: dict[Path, tuple[int, str]]) -> tuple[dict[str, int], list[dict[str, int]]]:
    days = np.zeros(SOURCE_COUNT + 1, dtype=np.uint8)
    accounts: dict[str, int] = {}
    currencies: dict[str, int] = {}
    daily = []
    with (out / "facts.bin").open("wb") as stream:
        for day in range(1, 29):
            count = 0
            for path in sources("facts", day):
                verified_file(path, checks)
                table = pq.ParquetFile(path).read(columns=[*IDENTITY, *FACT_FIELDS])
                ids = verify_tag(table, path)
                require(np.array_equal(ids, table["source_record_ordinal"].to_numpy()),
                        f"Source ordinal differs from its original ID in {path}")
                require(len(np.unique(ids)) == len(ids) and bool(np.all(days[ids] == 0)),
                        f"Repeated source ordinal in {path}")
                at = minutes(table)
                require(bool(np.all(at // DAY == day - 1)), f"Facts are in the wrong partition {path}")
                days[ids] = day
                records = np.zeros(len(ids), dtype=FACT)
                records["id"], records["minute"] = ids, at
                for output, side in (("sender", "sender"), ("receiver", "receiver")):
                    key = pc.binary_join_element_wise(table[f"{side}_bank"], table[f"{side}_account"], ":")
                    records[output] = coded(key, accounts, np.dtype("<u4"))
                records["paid"] = decimal_words(table, "amount_paid")
                records["received"] = decimal_words(table, "amount_received")
                records["paid_currency"] = coded(table["payment_currency"], currencies, np.dtype("<u2"))
                records["received_currency"] = coded(table["receiving_currency"], currencies, np.dtype("<u2"))
                records.tofile(stream)
                count += len(records)
            daily.append({"day": day, "facts": count})
            print(f"Verified facts September {day:02}: {count:,}", flush=True)
    require(bool(np.all(days[1:] > 0)) and SOURCE_COUNT == PREP["accepted_rows"],
            "Missing AWS fact rows")
    days.tofile(out / "days.u8")
    (out / "accounts.json").write_text(json.dumps(list(accounts), separators=(",", ":")))
    return accounts, daily


def stage_cases(out: Path, accounts: dict[str, int], checks: dict[Path, tuple[int, str]]) -> None:
    q2 = RELEASE["q2"]
    paths = OBJECTS.root / split_uri(q2["case_index"])[1]
    total = 0
    node_ids = {}
    with (out / "cases.bin").open("wb") as raw, (out / "case-ids.s64").open("wb") as keys:
        for day, meta in enumerate(q2["snapshots"], 1):
            folder = paths / ("window_date=" + meta["window_start"][:10])
            files = sorted(folder.glob("*.parquet"))
            require(bool(files), f"Missing published case index folder {folder}")
            for path in files:
                verified_file(path, checks)
            table = pq.read_table(files, columns=list(CASE_FIELDS), partitioning=None)
            expect = {
                "dataset_version": RELEASE["dataset_version"], "run_id": RELEASE["run_id"],
                "analysis_id": q2["analysis_id"], "rule_version": "structural-v2",
                **{key: datetime.fromisoformat(meta[key])
                   for key in ("window_start", "window_end", "snapshot_cutoff")},
            }
            for key, value in expect.items():
                require(table[key].null_count == 0 and pc.all(pc.equal(table[key], value)).as_py(),
                        f"Invalid case {key} in {folder}")
            require(len(table) == meta["case_count"]
                    and pc.sum(table["evidence_transaction_count"]).as_py() ==
                    meta["case_evidence_rows_including_case_overlap"], f"Case counts differ for {folder}")
            sorted_index = table.sort_by([("case_id", "ascending")])
            ids = np.asarray(sorted_index["case_id"].to_pylist(), dtype="S64")
            require(bool(np.all(np.char.str_len(ids) == 64)) and len(np.unique(ids)) == len(ids),
                    f"Invalid case identities for {folder}")
            ids.tofile(keys)
            records = np.zeros(len(table), dtype=CASE)
            records["day"] = day
            for i, row in enumerate(sorted_index.select([
                "pattern_type", "hub", "ordered_nodes", "evidence_transaction_count",
                "unique_edge_count", "participant_count",
            ]).to_pylist()):
                kind = KINDS.index(row["pattern_type"])
                degree = row["unique_edge_count"]
                nodes = row["ordered_nodes"]
                if kind < 2:
                    require(nodes == [row["hub"]] and degree >= 5 and row["participant_count"] == degree + 1,
                            f"Invalid fan topology in {folder}")
                else:
                    require(row["hub"] is None and len(set(nodes)) == len(nodes) == degree ==
                            row["participant_count"] == kind, f"Invalid cycle topology in {folder}")
                for j, key in enumerate(nodes):
                    if key not in node_ids:
                        bank, account = json.loads(key)
                        node_ids[key] = accounts[bank + ":" + account]
                    records["nodes"][i, j] = node_ids[key]
                records["kind"][i] = kind
                records["size"][i] = row["evidence_transaction_count"]
                records["degree"][i] = degree
            records.tofile(raw)
            total += len(records)
            print(f"Verified published case index cutoff {meta['window_end'][:10]}: {len(records):,}",
                  flush=True)
    require(total == q2["case_count"], "Incomplete published case index")


if __name__ == "__main__":
    directory = Path(sys.argv[1]).resolve()
    checks = inventory()
    accounts, daily = clean_facts(directory, checks)
    stage_cases(directory, accounts, checks)
    (directory / "manifest.json").write_text(json.dumps({
        "release": RELEASE["release_id"], "facts": SOURCE_COUNT, "accounts": len(accounts),
        "cases": RELEASE["q2"]["case_count"], "snapshots": len(RELEASE["q2"]["snapshots"]),
        "evidence_memberships": sum(x["case_evidence_rows_including_case_overlap"] for x in RELEASE["q2"]["snapshots"]),
        "daily": daily,
    }, indent=2) + "\n")
