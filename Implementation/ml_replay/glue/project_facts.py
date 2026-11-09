"""Rebuild the pinned binary projection from the original label-free Parquet shards."""

from collections.abc import Callable
from contextlib import closing
from dataclasses import dataclass
from hashlib import file_digest, md5
from io import BytesIO
import json
from pathlib import Path
import re

import numpy as np
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq


ROWS = 31_898_238
RELEASE = "full-20261030-v1"
DATASET = "ibm-hi-medium-b1b99c68b765580f"
PREFIX = f"curated/dataset_version={DATASET}/run_id={RELEASE}/transactions/"
FIELDS = ("source_id", "dataset_version", "run_id", "source_record_ordinal", "event_time", "sender_bank",
          "sender_account", "receiver_bank", "receiver_account", "amount_received", "receiving_currency",
          "amount_paid", "payment_currency")
FACT = np.dtype([("paid", "<u8", (2,)), ("received", "<u8", (2,)), ("id", "<u4"), ("sender", "<u4"),
                 ("receiver", "<u4"), ("minute", "<u4"), ("paid_currency", "<u2"),
                 ("received_currency", "<u2"), ("pad", "<u4")])
SHARD_KEY = re.compile(r"event_date=2022-09-(\d{2})/part-[\w.-]+\.parquet")


@dataclass(frozen=True)
class Shard:
    key: str
    day: int
    size: int
    etag: str


def need(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def inventory(path: Path) -> tuple[str, list[Shard]]:
    data = json.loads(path.read_text())
    source_hash = data["source_sha256"]
    need(bool(re.fullmatch(r"[0-9a-f]{64}", source_hash)), "Missing raw transaction checksum")
    shards = []
    for row in data["shards"]:
        key, size, etag = row["key"], row["size"], row["etag"]
        match = SHARD_KEY.fullmatch(key.removeprefix(PREFIX))
        if not key.startswith(PREFIX) or match is None:
            raise ValueError(f"Shard outside the archived clean-fact allowlist: {key}")
        need(type(size) is int and 0 < size < 150_000_000
             and bool(re.fullmatch(r"[0-9a-f]{32}(-1)?", etag)), f"Unexpected shard size or ETag: {key}")
        shards.append(Shard(key, int(match[1]), size, etag))
    keys = [shard.key for shard in shards]
    expected = {day: {27: 14, 28: 2}.get(day, 16) for day in range(1, 29)}
    need(keys == sorted(set(keys)) and {day: sum(s.day == day for s in shards) for day in range(1, 29)} == expected
         and len(shards) == sum(expected.values()), "Incomplete or unordered October 30 fact inventory")
    return source_hash, shards


def verified_parquet(shard: Shard, data: bytes) -> pa.Table:
    digest = md5(data, usedforsecurity=False)
    tag = (md5(digest.digest(), usedforsecurity=False).hexdigest() + "-1"
           if shard.etag.endswith("-1") else digest.hexdigest())
    need(len(data) == shard.size and tag == shard.etag, f"Archived fact object differs: {shard.key}")
    return pq.ParquetFile(BytesIO(data)).read(columns=list(FIELDS))


def codes(column: pa.ChunkedArray, codebook: dict[str, int], dtype: np.dtype) -> np.ndarray:
    values = column.combine_chunks().dictionary_encode()
    need(values.null_count == 0, "Cannot code missing published fact fields")
    keys = np.array([codebook.setdefault(value, len(codebook)) for value in values.dictionary.to_pylist()], dtype=dtype)
    return keys[values.indices.to_numpy()]


def amounts(table: pa.Table, name: str) -> np.ndarray:
    col = table[name].combine_chunks()
    need(col.type == pa.decimal128(38, 8) and col.null_count == 0, f"Unexpected {name} amount contract")
    words = np.frombuffer(col.buffers()[1], dtype="<u8", count=2 * len(col), offset=16 * col.offset).reshape(-1, 2)
    need(not bool(np.any(words[:, 1] >> np.uint64(63))), f"Negative {name} amount")
    return words


def rebuild(path: Path, output: Path, days_path: Path, expected: str, read_shard: Callable[[Shard], bytes]) -> int:
    source_hash, shards = inventory(path)
    days = np.zeros(ROWS + 1, dtype=np.uint8)
    accounts: dict[str, int] = {}
    currencies: dict[str, int] = {}
    epoch = np.datetime64("2022-09-01", "ns").astype(np.int64)
    day_count = 0
    with output.open("xb") as stream:
        for i, shard in enumerate(shards):
            table = verified_parquet(shard, read_shard(shard))
            for field, identity in (("dataset_version", DATASET), ("run_id", RELEASE)):
                need(table[field].null_count == 0 and bool(pc.all(pc.equal(table[field], identity)).as_py()),
                     f"Wrong fact {field}: {shard.key}")
            source = table["source_id"]
            need(source.null_count == 0 and bool(pc.all(pc.starts_with(source, source_hash + ":")).as_py()),
                 f"Invalid source identity: {shard.key}")
            ids = pc.cast(pc.utf8_slice_codeunits(source, start=65), pa.int32()).to_numpy()
            need(bool(np.all((ids > 0) & (ids <= ROWS))) and len(np.unique(ids)) == len(ids)
                 and bool(np.all(days[ids] == 0)) and np.array_equal(ids, table["source_record_ordinal"].to_numpy()),
                 f"Unexpected or repeated payment ordinal: {shard.key}")
            ns = table["event_time"].to_numpy().astype("datetime64[ns]").astype(np.int64) - epoch
            at = (ns // 60_000_000_000).astype(np.int32)
            need(bool(np.all(ns % 60_000_000_000 == 0)) and bool(np.all(at // 1440 == shard.day - 1)),
                 f"Unexpected payment time: {shard.key}")
            days[ids] = shard.day
            records = np.zeros(len(ids), dtype=FACT)
            records["id"], records["minute"] = ids, at
            for side in ("sender", "receiver"):
                key = pc.binary_join_element_wise(table[f"{side}_bank"], table[f"{side}_account"], ":")
                records[side] = codes(key, accounts, np.dtype("<u4"))
            records["paid"] = amounts(table, "amount_paid")
            records["received"] = amounts(table, "amount_received")
            records["paid_currency"] = codes(table["payment_currency"], currencies, np.dtype("<u2"))
            records["received_currency"] = codes(table["receiving_currency"], currencies, np.dtype("<u2"))
            records.tofile(stream)
            day_count += len(records)
            if i + 1 == len(shards) or shards[i + 1].day != shard.day:
                print(f"Rebuilt clean facts for September {shard.day:02}: {day_count:,}", flush=True)
                day_count = 0
    with output.open("rb") as stream:
        need(file_digest(stream, "sha256").hexdigest() == expected, "Rebuilt fact projection differs from local SHA-256")
    need(np.array_equal(days, np.fromfile(days_path, dtype=np.uint8)), "Rebuilt dates differ from the pinned input")
    return len(accounts)


def rebuild_from_s3(s3, bucket: str, owner: str, inventory_path: Path, output: Path, days_path: Path,
                    expected: str) -> int:
    def read(shard: Shard) -> bytes:
        etag = f'"{shard.etag}"'
        response = s3.get_object(Bucket=bucket, Key=shard.key, ExpectedBucketOwner=owner, IfMatch=etag)
        with closing(response["Body"]) as body:
            need(response["ETag"] == etag and response["ContentLength"] == shard.size,
                 f"Unexpected archived S3 object metadata: {shard.key}")
            return body.read(shard.size + 1)

    return rebuild(inventory_path, output, days_path, expected, read)
