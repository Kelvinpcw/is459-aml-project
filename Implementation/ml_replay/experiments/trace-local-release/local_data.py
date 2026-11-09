"""Read-only local adapters for the existing TRACE dashboard."""
from collections.abc import Iterator
from contextlib import closing
from decimal import Context, Decimal
from pathlib import Path, PurePosixPath
import re
import sqlite3
from typing import BinaryIO

import pyarrow.parquet as pq

from pipeline.release import BUCKET
COLUMNS = ("dataset_version", "run_id", "sender_bank", "receiver_bank", "payment_format",
           "payment_currency", "receiving_currency", "transaction_count", "laundering_count",
           "amount_paid_total", "amount_received_total")
NUMBERS = ("transaction_count", "laundering_count")


class LocalObjects:
    def __init__(self, root: Path):
        self.root = root

    def get_object(self, Bucket: str, Key: str) -> dict[str, BinaryIO]:
        if Bucket != BUCKET or Key.startswith("/") or ".." in PurePosixPath(Key).parts:
            raise ValueError("Unexpected release object key")
        path = self.root / Key
        if not path.is_file():
            raise FileNotFoundError(f"Published release object is absent from the local mirror: {Key}")
        return {"Body": path.open("rb")}

    def get_paginator(self, operation: str):
        if operation != "list_objects_v2":
            raise ValueError(f"Unsupported local S3 operation {operation}")
        return self

    def paginate(self, Bucket: str, Prefix: str) -> Iterator[dict]:
        if Bucket != BUCKET or Prefix.startswith("/") or ".." in PurePosixPath(Prefix).parts:
            raise ValueError("Unexpected release partition")
        yield {"Contents": [{"Key": path.relative_to(self.root).as_posix()}
                            for path in sorted((self.root / Prefix).glob("*.parquet"))]}


class ExactMoney:
    def __init__(self):
        self.value = Decimal(0)
        self.context = Context(prec=50)

    def step(self, amount: str) -> None:
        self.value = self.context.add(self.value, Decimal(amount))

    def finalize(self) -> str:
        return format(self.value, "f")


class LocalQ1:
    def __init__(self, path: Path):
        self.path = path

    def query(self, release: dict, sql: str) -> list[dict[str, str | None]]:
        source = release["catalog"]
        target = f'{source["database"]}.{source["q1_table"]}'
        if target not in sql or not sql.startswith(("SELECT ", "WITH selected AS")):
            raise ValueError("The local dashboard only runs its published Q1 read queries")
        translated = sql.replace(target, "counts").replace("DATE '", "'")
        translated = re.sub(r"SUM\((amount_(?:paid|received)_total)\)", r"EXACT_SUM(\1)", translated)
        with closing(sqlite3.connect(self.path.as_uri() + "?mode=ro", uri=True)) as db:
            db.row_factory = sqlite3.Row
            db.create_aggregate("EXACT_SUM", 1, ExactMoney)
            return [{key: None if row[key] is None else str(row[key]) for key in row.keys()}
                    for row in db.execute(translated)]


def build_q1(root: Path, output: Path, release: dict, expected: tuple[int, int]) -> None:
    prefix = release["q1"]["daily_counts"].split("/", 3)[-1]
    staging = output.with_suffix(".staging")
    if staging.exists():
        raise FileExistsError(f"Remove incomplete database before retrying: {staging}")
    with closing(sqlite3.connect(staging)) as db:
        db.execute("PRAGMA journal_mode=OFF")
        db.execute("PRAGMA synchronous=OFF")
        db.execute("PRAGMA cache_size=-65536")
        fields = ", ".join(f"{key} {'INTEGER' if key in NUMBERS else 'TEXT'} NOT NULL" for key in COLUMNS)
        db.execute(f"CREATE TABLE counts ({fields}, event_date TEXT NOT NULL)")
        sql = "INSERT INTO counts VALUES (" + ",".join("?" for _ in (*COLUMNS, "event_date")) + ")"
        counts = []
        for date in release["q1"]["dates"]:
            files = sorted((root / prefix / f"event_date={date}").glob("*.parquet"))
            if not files:
                raise FileNotFoundError(f"No published Q1 partition for {date}")
            n = labels = 0
            for path in files:
                for batch in pq.ParquetFile(path).iter_batches(columns=list(COLUMNS), batch_size=65536):
                    rows = batch.to_pylist()
                    if any((r["dataset_version"], r["run_id"]) != (release["dataset_version"], release["run_id"])
                           for r in rows):
                        raise ValueError(f"Wrong dataset/run in {path}")
                    db.executemany(sql, (tuple(format(r[k], "f") if isinstance(r[k], Decimal) else r[k]
                                               for k in COLUMNS) + (date,) for r in rows))
                    n += sum(row["transaction_count"] for row in rows)
                    labels += sum(row["laundering_count"] for row in rows)
            counts.append((n, labels))
            print(date, n, labels, flush=True)
        observed = tuple(map(sum, zip(*counts, strict=True)))
        if observed != expected:
            raise ValueError(f"Local Q1 population {observed} differs from published preparation {expected}")
        db.execute("CREATE INDEX by_date_currency ON counts(event_date,payment_currency)")
        db.commit()
    staging.replace(output)
