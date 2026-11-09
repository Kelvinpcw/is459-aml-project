"""Match IBM annotations and labels independently of the label-free case replay."""
from collections import defaultdict
from datetime import datetime
import json
import os
from pathlib import Path
import sys

import numpy as np
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq

from prepare import (DAY, EPOCH, IDENTITY, KINDS, PROJECT, RELEASE, SOURCE_COUNT,
                     inventory, minutes, require, sources, verified_file, verify_tag)

sys.path.insert(0, str(PROJECT / "Implementation/jobs"))
from evaluate_q2 import MATCH_COLUMNS, pair, parse_annotations, signature, topology

SCOPES = {"development": (1, 8), "holdout": (9, 16), "sparse_tail": (17, 28)}
ANNOTATION_HASH = "392d748d8d76efc1a96f6dc29ad8dd282c815de96537f0296bb0a7fa96ec4130"


def node_order(shape: dict) -> list[str]:
    if shape["hub"] is not None:
        return [shape["hub"]]
    following = dict(shape["edges"])
    nodes = [min(following)]
    for _ in range(len(following) - 1):
        nodes.append(following[nodes[-1]])
    require(following[nodes[-1]] == nodes[0], "Unexpected nonclosing annotation cycle")
    return nodes


def eligible_shapes(start: int, end: int) -> list[dict]:
    source = Path(os.environ["TRACE_HI_MEDIUM_DIR"]) / "HI-Medium_Patterns.txt"
    types = {"FAN-IN": "fan_in", "FAN-OUT": "fan_out", "CYCLE": "cycle"}
    refs = []
    for attempt in parse_annotations(source.read_text(), ANNOTATION_HASH):
        rows = attempt["transactions"]
        kind = types.get(attempt["annotation_type"])
        if kind is None or not all(start <= r["event_time"].day <= end for r in rows):
            continue
        times = [r["event_time"] for r in rows]
        if not any(datetime.fromisoformat(s["window_start"]) <= min(times)
                   and max(times) < datetime.fromisoformat(s["window_end"])
                   and max(times) <= datetime.fromisoformat(s["snapshot_cutoff"])
                   for s in RELEASE["q2"]["snapshots"][start - 1:end]):
            continue
        shape, _ = topology({pair(r) for r in rows}, kind, 5)
        if shape:
            refs.append({"attempt_id": attempt["attempt_id"], "kind": KINDS.index(shape["pattern_type"]),
                         "nodes": node_order(shape), "matches": [signature(r) for r in rows]})
    return refs


def read_labels(start: int, end: int, directory: Path) -> np.ndarray:
    days = np.fromfile(directory / "days.u8", dtype=np.uint8)
    require(len(days) == SOURCE_COUNT + 1, "Need all published fact ordinals before evaluation")
    labels = np.full(len(days), 255, dtype=np.uint8)
    checks = inventory()
    for day in range(start, end + 1):
        total = 0
        for path in sources("labels", day):
            verified_file(path, checks)
            table = pq.ParquetFile(path).read(columns=[*IDENTITY, "is_laundering"])
            ids = verify_tag(table, path)
            col = table["is_laundering"].to_numpy()
            require(len(np.unique(ids)) == len(ids) and bool(np.all(labels[ids] == 255)),
                    f"Repeated labels in {path}")
            require(bool(np.all((col == 0) | (col == 1))) and bool(np.all(days[ids] == day)),
                    f"Invalid or out-of-partition labels in {path}")
            labels[ids] = col
            total += len(ids)
        require(total == np.count_nonzero(days == day), f"Fact/label population differs on September {day:02}")
    return labels


def match_attempts(refs: list[dict], start: int, end: int,
                   labels: np.ndarray, directory: Path) -> list[dict]:
    if not refs:
        return []
    keys = {key for ref in refs for key in ref["matches"]}
    at_index, acc_index = map(MATCH_COLUMNS.index, ("event_time", "sender_account"))
    sender_accounts = pa.array(sorted({key[acc_index] for key in keys}))
    at = np.array(sorted({(key[at_index] - EPOCH).total_seconds() // 60 for key in keys}), dtype=np.int32)
    matches = defaultdict(list)
    for day in range(start, end + 1):
        cols = ["source_record_ordinal", *MATCH_COLUMNS]
        for path in sources("facts", day):
            table = pq.ParquetFile(path).read(columns=cols)
            table = table.filter(pc.is_in(table["sender_account"], value_set=sender_accounts))
            if not len(table):
                continue
            table = table.filter(pa.array(np.isin(minutes(table), at)))
            for row in table.to_pylist():
                sig = signature(row)
                if sig in keys:
                    matches[sig].append(row["source_record_ordinal"])
    nodes_wanted = {":".join(json.loads(n)) for r in refs for n in r["nodes"]}
    accounts = {key: i for i, key in enumerate(json.loads((directory / "accounts.json").read_text()))
                if key in nodes_wanted}
    result = []
    for ref in refs:
        matching = [matches[key] for key in ref["matches"]]
        if any(len(hits) != 1 or labels[hits[0]] != 1 for hits in matching):
            continue
        ordinals = [hits[0] for hits in matching]
        if len(set(ordinals)) != len(ordinals):
            continue
        result.append({"attempt_id": ref["attempt_id"], "kind": ref["kind"],
                       "nodes": [accounts[":".join(json.loads(n))] for n in ref["nodes"]],
                       "ordinals": ordinals})
    return result


if __name__ == "__main__":
    directory = Path(sys.argv[1]).resolve()
    scope = sys.argv[2]
    start, end = SCOPES[scope]
    labels = read_labels(start, end, directory)
    refs = match_attempts(eligible_shapes(start, end), start, end, labels, directory)
    labels.tofile(directory / f"labels-{scope}.u8")
    (directory / f"references-{scope}.json").write_text(json.dumps(refs, separators=(",", ":")) + "\n")
    print(scope, "eligible", len(refs), "labelled positives", int(np.count_nonzero(labels == 1)), flush=True)
