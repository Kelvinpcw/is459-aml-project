"""Bounded Q2 development detector: label-free structural leads, never proof of laundering.

Spark validates/filters the immutable prepared input. Only a guarded development
window is materialised for deterministic graph/case assembly on the driver.
This is not an unbounded full-dataset graph implementation.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime
from decimal import Decimal
import hashlib
import json
import re
from urllib.parse import urlparse

RULE_VERSION = "structural-v1"
EVIDENCE_COLUMNS = ["source_id", "event_time", "sender_bank", "sender_account",
                    "receiver_bank", "receiver_account", "amount_paid", "payment_currency",
                    "amount_received", "receiving_currency", "payment_format"]
ENTITY_COLUMNS = [f"{side}_entity_{field}" for side in ("sender", "receiver")
                  for field in ("id", "name", "unknown")]
DETECTOR_COLUMNS = ["dataset_version", "run_id"] + EVIDENCE_COLUMNS + ENTITY_COLUMNS


class DetectionLimitError(ValueError):
    """A declared complete window cannot be processed within the configured bound."""


@dataclass(frozen=True)
class Config:
    dataset_version: str
    run_id: str
    analysis_id: str
    window_start: str
    window_end: str
    snapshot_cutoff: str
    min_counterparties: int = 5
    max_window_rows: int = 50000
    max_edges: int = 20000
    max_cycle_expansions: int = 250000
    max_cases: int = 500
    max_case_nodes: int = 1000
    max_case_evidence: int = 2000
    max_total_evidence: int = 100000
    max_bundle_bytes: int = 2000000

    def times(self):
        values = tuple(datetime.strptime(v, "%Y-%m-%dT%H:%M:%S")
                       for v in (self.window_start, self.window_end, self.snapshot_cutoff))
        if not values[0] < values[1] or not values[0] <= values[2] <= values[1]:
            raise ValueError("Require start < end and start <= cutoff <= end, in dataset-local time")
        if self.min_counterparties < 5:
            raise ValueError("The starting fan rule requires at least five counterparties")
        for key, value in asdict(self).items():
            if key.startswith("max_") and value < 1:
                raise ValueError("All processing limits must be positive")
        for value in (self.dataset_version, self.run_id, self.analysis_id):
            if not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", value):
                raise ValueError("Unsafe dataset/run/analysis identity")
        return values


def assert_label_free_columns(columns):
    forbidden = [c for c in columns if any(word in c.lower() for word in ("launder", "label", "annotation"))]
    if forbidden:
        raise ValueError("Detector must not receive labels or annotations: " + ", ".join(forbidden))


def validate_manifest(manifest):
    allowed = {"schema_version", "stage", "preparation_status", "dataset_version", "run_id",
               "accepted_rows", "fact_columns", "amount_policy", "inputs", "timestamp_policy"}
    if set(manifest) != allowed:
        raise ValueError("Use the dedicated detector-input manifest, not a full preparation/label report")
    if (manifest["schema_version"] != 1 or manifest["stage"] != "detector_inputs" or
            manifest["preparation_status"] != "PASSED" or manifest["accepted_rows"] < 1):
        raise ValueError("Invalid passed detector-input manifest")
    assert_label_free_columns(manifest["fact_columns"])
    if not set(DETECTOR_COLUMNS) <= set(manifest["fact_columns"]):
        raise ValueError("Manifest does not describe the required enriched facts")
    if manifest["amount_policy"] != {"precision": 38, "scale": 8}:
        raise ValueError("Q2 requires the precision-safe amount contract")
    if set(manifest["inputs"]) != {"transactions"}:
        raise ValueError("Detector input must be only enriched transaction facts")


def _node_id(node):
    return json.dumps(list(node), separators=(",", ":"), ensure_ascii=True)


def _json_default(value):
    if isinstance(value, (datetime, Decimal)):
        return value.isoformat() if isinstance(value, datetime) else str(value)
    raise TypeError(type(value).__name__)


def _components(adjacency, reverse):
    """Iterative Kosaraju: exact SCC pruning preserves every directed cycle."""
    visited, finish = set(), []
    nodes = set(adjacency) | set(reverse)
    for root in sorted(nodes):
        if root in visited:
            continue
        visited.add(root)
        stack = [(root, iter(sorted(adjacency.get(root, ())))) ]
        while stack:
            node, neighbours = stack[-1]
            nxt = next(neighbours, None)
            if nxt is None:
                finish.append(node)
                stack.pop()
            elif nxt not in visited:
                visited.add(nxt)
                stack.append((nxt, iter(sorted(adjacency.get(nxt, ())))))
    assigned, components = set(), []
    for root in reversed(finish):
        if root in assigned:
            continue
        component, stack = set(), [root]
        assigned.add(root)
        while stack:
            node = stack.pop()
            component.add(node)
            for nxt in reverse.get(node, ()):
                if nxt not in assigned:
                    assigned.add(nxt)
                    stack.append(nxt)
        if len(component) >= 2:
            components.append(component)
    return components


def build_cases(records, config):
    start, end, cutoff = config.times()
    adjacency, reverse, edge_records, nodes = defaultdict(set), defaultdict(set), defaultdict(list), {}
    source_ids = set()
    scoped = self_rows = outside = after_cutoff = 0
    for record in records:
        assert_label_free_columns(record)
        if not set(DETECTOR_COLUMNS) <= set(record):
            raise ValueError("Missing enriched detector columns")
        if record["dataset_version"] != config.dataset_version or record["run_id"] != config.run_id:
            raise ValueError("Mixed preparation dataset/run identity")
        event = record["event_time"]
        if not isinstance(event, datetime) or event.tzinfo is not None:
            raise ValueError("Require a valid dataset-local naive event time")
        if not start <= event < end:
            outside += 1
            continue
        if event > cutoff:
            after_cutoff += 1
            continue
        scoped += 1
        if scoped > config.max_window_rows:
            raise DetectionLimitError("Window row limit exceeded; no partial detection is accepted")
        source_id = record["source_id"]
        if not isinstance(source_id, str) or not source_id or source_id in source_ids:
            raise ValueError("Missing or duplicate transaction source ID")
        source_ids.add(source_id)
        endpoints = []
        for side in ("sender", "receiver"):
            node = (record[f"{side}_bank"], record[f"{side}_account"])
            if any(not isinstance(v, str) or not v for v in node):
                raise ValueError("Missing bank/account identity")
            info = {"node_id": _node_id(node), "bank": node[0], "account": node[1],
                    "entity_id": record[f"{side}_entity_id"], "entity_name": record[f"{side}_entity_name"],
                    "entity_unknown": record[f"{side}_entity_unknown"]}
            if info["entity_unknown"] != (info["entity_id"] is None):
                raise ValueError("Entity coverage flag differs from mapping")
            if node in nodes and nodes[node] != info:
                raise ValueError("Inconsistent account/entity mapping")
            nodes[node] = info
            endpoints.append(node)
        for side in ("paid", "received"):
            if not isinstance(record[f"amount_{side}"], Decimal) or not record[f"amount_{side}"].is_finite():
                raise ValueError("Exact finite decimal amount required")
        if any(not isinstance(record[c], str) or not record[c].strip()
               for c in ("payment_currency", "receiving_currency", "payment_format")):
            raise ValueError("Missing currency or payment format")
        src, dst = endpoints
        if src == dst:
            self_rows += 1
            continue
        pair = src, dst
        edge_records[pair].append({c: record[c] for c in EVIDENCE_COLUMNS})
        adjacency[src].add(dst)
        reverse[dst].add(src)
        if len(edge_records) > config.max_edges:
            raise DetectionLimitError("Distinct edge limit exceeded")
    cases, evidence_total = [], 0

    def emit(rule, participants, pairs, hub=None):
        nonlocal evidence_total
        if len(cases) >= config.max_cases or len(participants) > config.max_case_nodes:
            raise DetectionLimitError("Case or participant limit exceeded")
        evidence = sorted((r for pair in pairs for r in edge_records[pair]),
                          key=lambda r: (r["event_time"], r["source_id"]))
        if len(evidence) > config.max_case_evidence:
            raise DetectionLimitError("Per-case evidence limit exceeded; evidence cannot be truncated")
        evidence_total += len(evidence)
        if evidence_total > config.max_total_evidence:
            raise DetectionLimitError("Total case evidence limit exceeded")
        logical = {"rule_version": RULE_VERSION, "dataset_version": config.dataset_version,
                   "run_id": config.run_id, "window_start": config.window_start,
                   "window_end": config.window_end, "snapshot_cutoff": config.snapshot_cutoff,
                   "min_counterparties": config.min_counterparties,
                   "pattern_type": rule, "ordered_nodes": [_node_id(n) for n in participants]}
        case_id = hashlib.sha256(json.dumps(logical, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        edges = [{"source": _node_id(a), "target": _node_id(b),
                  "transaction_count": len(edge_records[(a, b)])} for a, b in pairs]
        case = {**logical, "case_id": case_id, "analysis_id": config.analysis_id,
                "hub": _node_id(hub) if hub else None,
                "participant_count": len(participants), "unique_edge_count": len(pairs),
                "evidence_transaction_count": len(evidence),
                "first_event_time": min(r["event_time"] for r in evidence),
                "last_event_time": max(r["event_time"] for r in evidence),
                "nodes": [nodes[n] for n in participants], "edges": edges, "transactions": evidence,
                "interpretation": "Structural investigation lead. No claim of laundering or chronological return of funds."}
        if len(encode_case(case)) > config.max_bundle_bytes:
            raise DetectionLimitError("Case bundle byte limit exceeded")
        cases.append(case)

    for hub, peers in sorted(reverse.items()):
        if len(peers) >= config.min_counterparties:
            ordered = sorted(peers)
            emit("fan_in", [hub] + ordered, [(peer, hub) for peer in ordered], hub)
    for hub, peers in sorted(adjacency.items()):
        if len(peers) >= config.min_counterparties:
            ordered = sorted(peers)
            emit("fan_out", [hub] + ordered, [(hub, peer) for peer in ordered], hub)
    components = _components(adjacency, reverse)
    expansions = 0
    for component in components:
        within = {n: sorted(adjacency.get(n, set()) & component) for n in component}
        for root in sorted(component):
            stack = [(root,)]
            while stack:
                path = stack.pop()
                for nxt in within[path[-1]]:
                    expansions += 1
                    if expansions > config.max_cycle_expansions:
                        raise DetectionLimitError("Cycle search expansion limit exceeded")
                    if nxt == root and 2 <= len(path) <= 4:
                        emit(f"cycle_{len(path)}", list(path), list(zip(path, path[1:] + (root,))))
                    elif len(path) < 4 and nxt > root and nxt not in path:
                        stack.append(path + (nxt,))
    cases.sort(key=lambda c: c["case_id"])
    if len({c["case_id"] for c in cases}) != len(cases):
        raise ValueError("Duplicate logical case identity")
    return cases, {"scoped_rows": scoped, "outside_window_rows": outside, "after_cutoff_rows": after_cutoff,
                   "self_transaction_rows": self_rows, "nonself_transaction_rows": scoped - self_rows,
                   "distinct_nonself_edges": len(edge_records), "observed_nodes": len(nodes),
                   "unknown_entity_nodes": sum(n["entity_unknown"] for n in nodes.values()),
                   "nontrivial_scc_count": len(components), "cycle_expansions": expansions,
                   "case_count": len(cases), "case_counts_by_pattern": dict(Counter(c["pattern_type"] for c in cases)),
                   "case_evidence_rows_including_case_overlap": evidence_total,
                   "complete_for_declared_window": True, "truncated": False}


def collect_window(facts, manifest, config):
    from pyspark.sql import functions as F, types as T
    validate_manifest(manifest)
    config.times()
    assert_label_free_columns(facts.columns)
    if set(facts.columns) != set(manifest["fact_columns"]):
        raise ValueError("Actual fact columns differ from approved detector manifest")
    for column in ("amount_paid", "amount_received"):
        if facts.schema[column].dataType != T.DecimalType(38, 8):
            raise ValueError("Require decimal(38,8) facts")
    if facts.count() != manifest["accepted_rows"]:
        raise ValueError("Input fact count differs from immutable preparation approval")
    if facts.filter(~F.coalesce((F.col("dataset_version") == config.dataset_version) &
                               (F.col("run_id") == config.run_id), F.lit(False))).limit(1).count():
        raise ValueError("Input mixes dataset/run identities")
    if facts.filter(F.col("event_time").isNull()).limit(1).count():
        raise ValueError("Null event time in approved facts")
    start, end, cutoff = config.times()
    window = facts.filter((F.col("event_time") >= F.lit(start)) & (F.col("event_time") < F.lit(end)))
    available = window.filter(F.col("event_time") <= F.lit(cutoff)).select(*DETECTOR_COLUMNS)
    # Limit before collecting: a larger scope can never pull an unbounded graph into driver memory.
    rows = available.limit(config.max_window_rows + 1).collect()
    if len(rows) > config.max_window_rows:
        raise DetectionLimitError("Window exceeds bounded driver prototype; choose/review scope before retry")
    return [r.asDict() for r in rows]


def encode_case(case):
    return (json.dumps(case, default=_json_default, sort_keys=True) + "\n").encode()


def case_index_schema():
    from pyspark.sql import types as T
    return T.StructType([T.StructField(n, T.StringType(), False) for n in
                         ("dataset_version", "run_id", "analysis_id", "case_id", "pattern_type", "bundle_uri")] +
                        [T.StructField(n, T.IntegerType(), False) for n in
                         ("participant_count", "unique_edge_count", "evidence_transaction_count")] +
                        [T.StructField(n, T.TimestampType(), False) for n in
                         ("window_start", "window_end", "snapshot_cutoff", "first_event_time", "last_event_time")] +
                        [T.StructField("window_date", T.DateType(), False)])


def case_index_row(case, config, bundle_uri):
    values = {n: case[n] for n in ("dataset_version", "run_id", "analysis_id", "case_id", "pattern_type",
                                  "participant_count", "unique_edge_count", "evidence_transaction_count",
                                  "first_event_time", "last_event_time")}
    start, end, cutoff = config.times()
    values.update({"bundle_uri": bundle_uri, "window_start": start, "window_end": end,
                   "snapshot_cutoff": cutoff, "window_date": start.date()})
    return values


def main():
    import boto3
    from pyspark.sql import SparkSession
    parser = argparse.ArgumentParser()
    for name in ("input-manifest", "output-root", "analysis-id", "window-start", "window-end", "snapshot-cutoff"):
        parser.add_argument("--" + name, required=True)
    args, _ = parser.parse_known_args()
    s3 = boto3.client("s3")
    if "IfNoneMatch" not in s3.meta.service_model.operation_model("PutObject").input_shape.members:
        raise RuntimeError("Glue 5.1 or a compatible SDK is required")
    source, output = urlparse(args.input_manifest), urlparse(args.output_root)
    if source.scheme != "s3" or output.scheme != "s3":
        raise ValueError("Explicit S3 locations required")
    manifest = json.loads(s3.get_object(Bucket=source.netloc, Key=source.path.lstrip("/"))["Body"].read())
    validate_manifest(manifest)
    config = Config(manifest["dataset_version"], manifest["run_id"], args.analysis_id,
                    args.window_start, args.window_end, args.snapshot_cutoff)
    config.times()
    suffix = f"dataset_version={config.dataset_version}/run_id={config.run_id}/analysis_id={config.analysis_id}"
    base = output.path.strip("/")
    def key(zone, tail=""):
        return "/".join(filter(None, [base, zone, suffix, tail]))
    for zone in ("gold/cases", "quality/q2"):
        if s3.list_objects_v2(Bucket=output.netloc, Prefix=key(zone) + "/", MaxKeys=1).get("KeyCount", 0):
            raise ValueError("Q2 namespace exists; never overwrite or reuse a partial attempt")
    report = {"schema_version": 1, "stage": "q2", "status": "FAILED", "config": asdict(config),
              "input_manifest": args.input_manifest, "full_prepared_rows": manifest["accepted_rows"],
              "scope": "Bounded development window only; not full-day or full-dataset detection"}
    spark = (SparkSession.builder.appName("is459-aml-q2-dev").config("spark.sql.session.timeZone", "UTC")
             .config("spark.sql.ansi.enabled", "false").config("spark.sql.shuffle.partitions", "16").getOrCreate())
    try:
        records = collect_window(spark.read.parquet(manifest["inputs"]["transactions"]), manifest, config)
        cases, stats = build_cases(records, config)
        schema = case_index_schema()
        index = []
        for case in cases:
            bundle_key = key("gold/cases", f"bundles/{case['case_id']}.json")
            s3.put_object(Bucket=output.netloc, Key=bundle_key, IfNoneMatch="*", ContentType="application/json",
                          Body=encode_case(case))
            index.append(case_index_row(case, config, f"s3://{output.netloc}/{bundle_key}"))
        index_path = f"s3://{output.netloc}/{key('gold/cases', 'case_index')}/"
        spark.createDataFrame(index, schema).write.mode("errorifexists").partitionBy("window_date").parquet(index_path)
        report.update({"status": "PASSED", "statistics": stats, "case_index_schema": schema.jsonValue(),
                       "outputs": {"case_index": index_path, "bundles": f"s3://{output.netloc}/{key('gold/cases', 'bundles')}/"},
                       "detector_received_labels": False, "rule_version": RULE_VERSION})
    except Exception as error:
        report.update({"error_type": type(error).__name__, "error": str(error)[:2000]})
        raise
    finally:
        report["finished_at_utc"] = datetime.utcnow().isoformat() + "Z"
        try:
            s3.put_object(Bucket=output.netloc, Key=key("quality/q2", "report.json"), IfNoneMatch="*",
                          ContentType="application/json", Body=(json.dumps(report, indent=2) + "\n").encode())
        finally:
            spark.stop()


if __name__ == "__main__":
    main()
