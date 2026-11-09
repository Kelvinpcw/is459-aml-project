"""Verify released Parquet and project only fields used in the local comparison."""
from collections import defaultdict
from datetime import datetime, timedelta
import json
import os
from pathlib import Path
import sys

import numpy as np
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.csv as csv
import pyarrow.parquet as pq

EPOCH = datetime(2022, 9, 1)
DATASET = "ibm-hi-medium-b1b99c68b765580f"
RUN = "full-20261030-v1"
SOURCE_HASH = "3126afb8155e7c8815d62bc5370549a7b5ae6bf7dfe872b3cd7813e66a3d7ff5"
ANNOTATION_HASH = "392d748d8d76efc1a96f6dc29ad8dd282c815de96537f0296bb0a7fa96ec4130"
SOURCE_COUNT = 31_898_238
FAN_FIELDS = ("sender_bank", "sender_account", "receiver_bank", "receiver_account",
              "amount_received", "receiving_currency", "amount_paid", "payment_currency")
FACT_FIELDS = ("source_record_ordinal", "event_time", *FAN_FIELDS)
IDENTITY = ("source_id", "dataset_version", "run_id")


def require(value: bool, message: str) -> None:
    if not value:
        raise ValueError(message)


def minute(value: datetime) -> int:
    return (value - EPOCH) // timedelta(minutes=1)


def inputs(root: Path, kind: str, day: int) -> list[Path]:
    paths = sorted((root / kind / f"event_date=2022-09-{day:02}").glob("*.parquet"))
    expected = {27: 14, 28: 2}.get(day, 16)
    require(len(paths) == expected, f"{kind} on September {day} must contain {expected} release shards")
    return paths


def verify_tag(table: pa.Table, path: Path) -> np.ndarray:
    require(all(pc.all(pc.equal(table[key], val)).as_py() for key, val in
                (("dataset_version", DATASET), ("run_id", RUN))),
            f"Wrong run or dataset in {path}")
    source = table["source_id"]
    require(source.null_count == 0 and pc.all(pc.starts_with(source, SOURCE_HASH + ":")).as_py(),
            f"Unexpected source IDs in {path}")
    ordinals = pc.cast(pc.utf8_slice_codeunits(source, start=65), pa.int32()).to_numpy()
    require(bool(np.all((ordinals > 0) & (ordinals <= SOURCE_COUNT))), f"Invalid ordinal in {path}")
    return ordinals


def parse_reference(project: Path):
    sys.path.insert(0, str(project / "Implementation/jobs"))
    from evaluate_q2 import pair, parse_annotations, signature, topology

    annotation_path = Path(os.environ["TRACE_HI_MEDIUM_DIR"]) / "HI-Medium_Patterns.txt"
    attempts = parse_annotations(annotation_path.read_text(), ANNOTATION_HASH)
    targets = []
    for attempt in attempts:
        if attempt["annotation_type"] != "FAN-OUT":
            continue
        rows = attempt["transactions"]
        times = [minute(row["event_time"]) for row in rows]
        if min(times) < 8 * 1440 or max(times) >= 16 * 1440:
            continue
        if not any((d - 7) * 1440 <= min(times) and max(times) < d * 1440 for d in range(9, 17)):
            continue
        shape, _ = topology({pair(row) for row in rows}, "fan_out", 5)
        if shape:
            targets.append((attempt["attempt_id"], shape["hub"],
                            [(signature(row), m) for row, m in zip(rows, times, strict=True)]))
    return targets, signature


def stage(root: Path, out: Path, project: Path) -> None:
    targets, signature = parse_reference(project)
    wanted = {sig for _, _, rows in targets for sig, _ in rows}
    matches: dict[tuple, list[int]] = defaultdict(list)
    label_by_id = np.full(SOURCE_COUNT + 1, 255, dtype=np.uint8)
    seen_facts = np.zeros(SOURCE_COUNT + 1, dtype=np.bool_)
    epoch_seconds = int(np.datetime64(EPOCH, "s").astype(np.int64))
    n_holdout = n_holdout_positive = 0
    daily = []
    event_minutes = np.array(sorted({m for _, _, rows in targets for _, m in rows}), dtype=np.int32)
    with (out / "facts.csv").open("wb") as stream:
        for day in range(1, 29):
            partition_n = partition_positive = 0
            for path in inputs(root, "labels", day):
                table = pq.ParquetFile(path).read(columns=[*IDENTITY, "is_laundering"])
                ids = verify_tag(table, path)
                values = table["is_laundering"].to_numpy()
                require(bool(np.all((values == 0) | (values == 1))), f"Invalid label in {path}")
                require(len(np.unique(ids)) == len(ids) and bool(np.all(label_by_id[ids] == 255)),
                        f"Repeated source label in {path}")
                label_by_id[ids] = values
                partition_n += len(ids)
                partition_positive += int(values.sum())
            fact_n = 0
            for path in inputs(root, "facts", day):
                table = pq.ParquetFile(path).read(columns=[*IDENTITY, *FACT_FIELDS, "payment_format"])
                ids = verify_tag(table, path)
                require(np.array_equal(ids, table["source_record_ordinal"].to_numpy()),
                        f"Fact source ordinal differs from source ID in {path}")
                require(len(np.unique(ids)) == len(ids) and not np.any(seen_facts[ids]),
                        f"Repeated source fact in {path}")
                require(bool(np.all(label_by_id[ids] != 255)), f"Missing matching label for {path}")
                seen_facts[ids] = True
                fact_n += len(ids)
                # Spark timestamp values encode the dataset-local wall clock.
                raw_seconds = table["event_time"].to_numpy().astype("datetime64[s]").astype(np.int64)
                seconds = raw_seconds - epoch_seconds
                mins = (seconds // 60).astype(np.int32)
                require(bool(np.all((mins // 1440 == day - 1) & (seconds % 60 == 0))),
                        f"Unexpected partition or timestamp precision in {path}")
                if 9 <= day <= 16:
                    subset = table.select([*FACT_FIELDS, "payment_format"]).filter(pa.array(np.isin(mins, event_minutes)))
                    for row in subset.to_pylist():
                        key = signature(row)
                        if key in wanted:
                            matches[key].append(row["source_record_ordinal"])
                projected = table.select(FACT_FIELDS)
                projected = projected.set_column(1, "minute", pa.array(mins))
                csv.write_csv(projected, stream, write_options=csv.WriteOptions(include_header=False, quoting_style="none"))
            require(partition_n == fact_n, f"Fact and label row counts differ on September {day}")
            daily.append({"september_day": day, "payments": fact_n, "ibm_positive_payments": partition_positive})
            if 9 <= day <= 16:
                n_holdout += fact_n
                n_holdout_positive += partition_positive
            print(f"September {day:02}: {fact_n:,} facts and labels, {partition_positive:,} positives", flush=True)
    require((n_holdout, n_holdout_positive) == (15_025_129, 17_632), "Holdout differs from published evaluator")
    eligible = []
    for key, hub, rows in targets:
        ids = [matches[sig] for sig, _ in rows]
        if any(len(choices) != 1 or label_by_id[choices[0]] != 1 for choices in ids):
            continue
        if len({choices[0] for choices in ids}) != len(rows):
            continue
        eligible.append({"attempt_id": key, "hub": hub, "minutes": [m for _, m in rows]})
    require(len(eligible) == 24, f"Expected 24 eligible fan-out annotations, found {len(eligible)}")
    require(bool(np.all(seen_facts[1:])) and bool(np.all(label_by_id[1:] != 255)),
            "Expected the entire published 31,898,238-payment population")
    tail = daily[16:]
    require(sum(d["payments"] for d in tail) == 6987
            and sum(d["ibm_positive_payments"] for d in tail) == 4084, "Sparse-tail counts changed")
    label_by_id.tofile(out / "labels.u8")
    (out / "provenance.json").write_text(json.dumps({
        "input": "AWS published Parquet", "files": 864, "daily": daily,
    }, indent=2) + "\n")
    (out / "patterns.json").write_text(json.dumps(eligible, indent=2) + "\n")


if __name__ == "__main__":
    stage(*(Path(arg) for arg in sys.argv[1:]))
