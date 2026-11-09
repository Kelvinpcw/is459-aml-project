"""Read the published case index directly from the local Parquet mirror."""
from datetime import datetime
from functools import lru_cache

import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq

from dashboard.case_catalog import FIELDS, PAGE_SIZE
from pipeline.release import split_uri


class LocalCases:
    def __init__(self, objects, release):
        q2 = release["q2"]
        self.snapshots = {row["window_end"]: row for row in q2["snapshots"]}
        self.total = q2["case_count"]
        self.root = objects.root / split_uri(q2["case_index"])[1]
        self.identity = {"dataset_version": release["dataset_version"], "run_id": release["run_id"],
                         "analysis_id": q2["analysis_id"]}

    def _read_snapshot(self, cutoff: str) -> pa.Table:
        meta = self.snapshots[cutoff]
        folder = self.root / f"window_date={meta['window_start'][:10]}"
        files = sorted(folder.glob("*.parquet"))
        if not files:
            raise FileNotFoundError(f"Published case partition is absent for {cutoff}")
        table = pq.read_table(files, columns=list(FIELDS), partitioning=None)
        if (len(table) != meta["case_count"] or
                pc.sum(table["evidence_transaction_count"]).as_py() !=
                meta["case_evidence_rows_including_case_overlap"]):
            raise ValueError(f"Case or evidence counts do not match the manifest for {cutoff}")
        end = pa.scalar(datetime.fromisoformat(cutoff), type=table["window_end"].type)
        for field, value in (*self.identity.items(), ("window_end", end)):
            column = table[field]
            if column.null_count or not pc.all(pc.equal(column, value)).as_py():
                raise ValueError(f"Wrong case-index {field} for {cutoff}")
        return table.select([field for field in FIELDS if field not in self.identity])

    @lru_cache(maxsize=3)
    def table(self, cutoff: str | None) -> pa.Table:
        if cutoff is not None:
            return self._read_snapshot(cutoff)
        table = pa.concat_tables([self._read_snapshot(end) for end in sorted(self.snapshots)])
        if len(table) != self.total:
            raise ValueError("Case index does not match the published release count")
        return table

    @lru_cache(maxsize=6)
    def ordered(self, snapshot: str | None, pattern: str | None) -> tuple[pa.Table, pa.Array]:
        table = self.table(snapshot)
        if pattern:
            table = table.filter(pc.equal(table["pattern_type"], pattern))
        order = pc.sort_indices(table, sort_keys=[("case_id", "ascending"), ("window_end", "ascending")])
        return table, order

    def queue(self, snapshot: str | None, pattern: str | None, page: int | None):
        if page is None and not pattern:
            return self.total if snapshot is None else self.snapshots[snapshot]["case_count"]
        if page is None:
            return pc.count(pc.indices_nonzero(pc.equal(self.table(snapshot)["pattern_type"], pattern))).as_py()
        table, ordered = self.ordered(snapshot, pattern)
        selected = table.take(ordered.slice((page - 1) * PAGE_SIZE, PAGE_SIZE)).to_pylist()
        for row in selected:
            row["snapshot"] = row.pop("window_end").isoformat()
        return selected
