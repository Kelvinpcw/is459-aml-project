"""Isolated, bounded Q2 development evaluator. Never imported by detection.

The matched-volume amount ranking is an evaluation diagnostic, not a frozen
holdout baseline. Labels and annotations enter only after cases are frozen.
"""
from __future__ import annotations

from collections import Counter, defaultdict
import csv
from datetime import datetime, timezone
from decimal import Decimal, localcontext
import hashlib
import json
import re

EVIDENCE = ["source_id", "event_time", "sender_bank", "sender_account", "receiver_bank",
            "receiver_account", "amount_paid", "payment_currency", "amount_received",
            "receiving_currency", "payment_format"]
FACT_COLUMNS = ["dataset_version", "run_id"] + EVIDENCE
MATCH_COLUMNS = [c for c in EVIDENCE if c != "source_id"]
COUNTS = ("participant_count", "unique_edge_count", "evidence_transaction_count")
POLICY_VERSION = "development-evaluation-v1"


def timestamp(value):
    result = value if isinstance(value, datetime) else datetime.fromisoformat(value)
    if result.tzinfo is not None:
        raise ValueError("Require dataset-local naive event time")
    return result


def normalise_bank(value):
    value = value.strip()
    if not re.fullmatch(r"[0-9]+", value):
        raise ValueError("Invalid annotation bank identity")
    return value.lstrip("0") or "0"


def signature(row):
    values = []
    for name in MATCH_COLUMNS:
        value = row[name]
        if name == "event_time":
            value = timestamp(value)
        elif name.startswith("amount_"):
            value = Decimal(value)
            with localcontext() as context:
                context.prec = 50
                if (not value.is_finite() or value < 0 or value.adjusted() >= 30 or
                        value != value.quantize(Decimal(".00000001"))):
                    raise ValueError("Invalid exact annotation/evidence amount")
        elif not isinstance(value, str) or not value.strip():
            raise ValueError("Missing transaction match field")
        values.append(value)
    return tuple(values)


def node(bank, account):
    return json.dumps([bank, account], separators=(",", ":"), ensure_ascii=True)


def pair(row):
    return (node(row["sender_bank"], row["sender_account"]),
            node(row["receiver_bank"], row["receiver_account"]))


def parse_annotations(text, expected_sha256):
    """Strict block parsing; IDs retain annotation-file checksum and block ordinal."""
    if len(text.encode()) > 5_000_000 or hashlib.sha256(text.encode()).hexdigest() != expected_sha256:
        raise ValueError("Annotation checksum changed")
    attempts, current = [], None
    for line_number, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        begin = re.fullmatch(r"BEGIN LAUNDERING ATTEMPT - ([A-Z-]+)(?::.*)?", line)
        end = re.fullmatch(r"END LAUNDERING ATTEMPT - ([A-Z-]+)", line)
        if begin:
            if current is not None:
                raise ValueError("Nested annotation attempt")
            current = {"attempt_id": f"{expected_sha256}:{len(attempts) + 1}",
                       "annotation_type": begin[1], "line_start": line_number, "transactions": []}
        elif end:
            if current is None or end[1] != current["annotation_type"] or not current["transactions"]:
                raise ValueError("Mismatched or empty annotation attempt")
            attempts.append(current)
            if len(attempts) > 5000:
                raise ValueError("Annotation attempt bound exceeded")
            current = None
        else:
            if current is None:
                raise ValueError("Transaction outside annotation block")
            values = next(csv.reader([line], strict=True))
            if len(values) != 11 or values[-1] != "1":
                raise ValueError("Invalid annotated transaction width/positive label")
            row = {"event_time": datetime.strptime(values[0], "%Y/%m/%d %H:%M"),
                   "sender_bank": normalise_bank(values[1]), "sender_account": values[2].strip(),
                   "receiver_bank": normalise_bank(values[3]), "receiver_account": values[4].strip(),
                   "amount_received": Decimal(values[5]), "receiving_currency": values[6],
                   "amount_paid": Decimal(values[7]), "payment_currency": values[8],
                   "payment_format": values[9]}
            signature(row)
            current["transactions"].append(row)
            if len(current["transactions"]) > 1000:
                raise ValueError("Annotation attempt transaction bound exceeded")
    if current is not None or not attempts:
        raise ValueError("Incomplete or empty annotation file")
    return attempts


def scope(report):
    if (report.get("status") != "PASSED" or report.get("stage") != "q2" or
            report.get("rule_version") != "structural-v1" or report.get("detector_received_labels") is not False or
            report.get("statistics", {}).get("complete_for_declared_window") is not True or
            report.get("statistics", {}).get("truncated") is not False):
        raise ValueError("Require a complete passed frozen label-free Q2 analysis")
    config = report["config"]
    start, end, cutoff = (timestamp(config[k]) for k in ("window_start", "window_end", "snapshot_cutoff"))
    if not start < end or not start <= cutoff <= end or config["min_counterparties"] < 5:
        raise ValueError("Invalid frozen detector scope")
    return config, start, end, cutoff


def select_scope(records, report):
    config, start, end, cutoff = scope(report)
    selected = []
    for record in records:
        if any(record.get(k) != config[k] for k in ("dataset_version", "run_id")):
            raise ValueError("Foreign preparation identity")
        event = timestamp(record["event_time"])
        if start <= event < end and event <= cutoff:
            selected.append(record)
            if len(selected) > config["max_window_rows"]:
                raise ValueError("Evaluator window exceeds the reviewed bound")
    return selected


def topology(edges, pattern, minimum):
    """Derive type/hub/oriented-cycle from actual edges, never from a Max-N header."""
    if pattern not in ("fan_in", "fan_out", "cycle"):
        return None, "unsupported_annotation_type"
    if not edges or any(a == b for a, b in edges):
        return None, "self_or_empty_topology"
    participants = {n for edge in edges for n in edge}
    if pattern in ("fan_in", "fan_out"):
        hubs = {b if pattern == "fan_in" else a for a, b in edges}
        if len(hubs) != 1:
            return None, "invalid_fan_topology"
        hub = next(iter(hubs))
        if len(participants - {hub}) < minimum:
            return None, "below_fan_degree"
        return {"pattern_type": pattern, "hub": hub, "edges": edges}, None
    if pattern == "cycle":
        if not 2 <= len(participants) <= 4:
            return None, "cycle_size_out_of_scope"
        incoming, outgoing = Counter(b for a, b in edges), Counter(a for a, b in edges)
        if any(incoming[n] != 1 or outgoing[n] != 1 for n in participants):
            return None, "invalid_cycle_topology"
        next_node = dict(edges)
        current, seen = min(participants), set()
        while current not in seen:
            seen.add(current)
            current = next_node[current]
        if seen != participants or current != min(participants):
            return None, "disconnected_cycle_topology"
        return {"pattern_type": f"cycle_{len(participants)}", "hub": None, "edges": edges}, None
    return None, "unsupported_annotation_type"


def metrics(population, alerted, labels):
    positive = {sid for sid in population if labels[sid] == 1}
    tp = len(alerted & positive)
    n, l, k = len(population), len(positive), len(alerted)
    precision = tp / k if k else None
    recall = tp / l if l else None
    return {"population": n, "positive_labels": l, "unique_alerted_transactions": k,
            "true_positive": tp, "false_positive": k - tp, "false_negative": l - tp,
            "true_negative": n - l - k + tp, "precision": precision, "recall": recall,
            "lift_vs_population": precision / (l / n) if precision is not None and l else None,
            "precision_status": "measured" if k else "no_alerts",
            "recall_status": "measured" if l else "no_positive_labels"}


def validate_cases(cases, facts, report):
    config, start, end, cutoff = scope(report)
    if len(cases) > config["max_cases"]:
        raise ValueError("Case count exceeds detector bound")
    by_pair = defaultdict(set)
    for sid, row in facts.items():
        by_pair[pair(row)].add(sid)
    validated, seen = [], set()
    for case in cases:
        case_id = case.get("case_id")
        if not isinstance(case_id, str) or not re.fullmatch(r"[a-f0-9]{64}", case_id) or case_id in seen:
            raise ValueError("Missing/duplicate logical case ID")
        seen.add(case_id)
        for key in ("dataset_version", "run_id", "analysis_id", "window_start", "window_end",
                    "snapshot_cutoff", "min_counterparties"):
            if case[key] != config[key]:
                raise ValueError("Case mixes detector identity or time scope")
        logical_keys = ("rule_version", "dataset_version", "run_id", "window_start", "window_end",
                        "snapshot_cutoff", "min_counterparties", "pattern_type", "ordered_nodes")
        logical = {k: case[k] for k in logical_keys}
        digest = hashlib.sha256(json.dumps(logical, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        if case["rule_version"] != report["rule_version"] or digest != case_id:
            raise ValueError("Case logical hash differs from frozen identity")
        ids, edge_counts = set(), Counter()
        for evidence in case["transactions"]:
            if any(any(w in k.lower() for w in ("launder", "label", "annotation")) for k in evidence):
                raise ValueError("Frozen detector evidence contains labels")
            sid = evidence["source_id"]
            if sid in ids or sid not in facts or signature(evidence) != signature(facts[sid]):
                raise ValueError("Duplicate, foreign or changed case evidence")
            ids.add(sid)
            edge_counts[pair(facts[sid])] += 1
        edges = {(e["source"], e["target"]): e["transaction_count"] for e in case["edges"]}
        if len(edges) != len(case["edges"]) or edges != dict(edge_counts):
            raise ValueError("Case topology/counts do not match evidence")
        complete_ids = set().union(*(by_pair[p] for p in edges)) if edges else set()
        if ids != complete_ids:
            raise ValueError("Case omitted supporting source transactions")
        participants = {n for p in edges for n in p}
        node_ids = [n["node_id"] for n in case["nodes"]]
        if (len(set(node_ids)) != len(node_ids) or set(node_ids) != participants or
                case["ordered_nodes"] != node_ids or
                any(n["node_id"] != node(n["bank"], n["account"]) for n in case["nodes"])):
            raise ValueError("Case participants differ from source endpoints")
        pattern = case["pattern_type"]
        declared = "cycle" if pattern in ("cycle_2", "cycle_3", "cycle_4") else pattern
        shape, reason = topology(set(edges), declared, config["min_counterparties"])
        if reason or shape["pattern_type"] != pattern or shape["hub"] != case["hub"]:
            raise ValueError("Case trigger/topology is invalid")
        if [case[c] for c in COUNTS] != [len(participants), len(edges), len(ids)]:
            raise ValueError("Case summary counts differ from evidence")
        times = [timestamp(facts[sid]["event_time"]) for sid in ids]
        if (timestamp(case["first_event_time"]) != min(times) or timestamp(case["last_event_time"]) != max(times)):
            raise ValueError("Case time summaries differ from evidence")
        validated.append({"case": case, "source_ids": ids, "shape": shape})
    stats = report["statistics"]
    if (len(cases) != stats["case_count"] or
            dict(Counter(c["pattern_type"] for c in cases)) != stats["case_counts_by_pattern"] or
            sum(len(c["source_ids"]) for c in validated) != stats["case_evidence_rows_including_case_overlap"]):
        raise ValueError("Case population differs from frozen detector report")
    return validated


def evaluate(records, label_rows, cases, report, attempts):
    config, start, end, cutoff = scope(report)
    # This version deliberately refuses to turn its diagnostic ranking into a holdout claim.
    if start >= datetime(2022, 9, 9) or end > datetime(2022, 9, 9):
        raise ValueError("Formal holdout requires a separately frozen development calibration policy")
    if len(records) != report["statistics"]["scoped_rows"] or len(records) > config["max_window_rows"]:
        raise ValueError("Eligible population differs from detector scope/bound")
    facts = {}
    for row in records:
        if any(any(w in k.lower() for w in ("launder", "label", "annotation")) for k in row):
            raise ValueError("Facts must remain label-free until the evaluator join")
        if not set(FACT_COLUMNS) <= set(row) or any(row[k] != config[k] for k in ("dataset_version", "run_id")):
            raise ValueError("Missing/foreign eligible fact fields")
        event = timestamp(row["event_time"])
        if not start <= event < end or event > cutoff:
            raise ValueError("Future/out-of-window fact reached the evaluator")
        sid = row["source_id"]
        if not isinstance(sid, str) or not sid or sid in facts:
            raise ValueError("Eligible source IDs must be unique")
        if any(not isinstance(row[c], Decimal) for c in ("amount_paid", "amount_received")):
            raise ValueError("Facts require exact typed Decimal amounts")
        signature(row)
        facts[sid] = row
    labels = {}
    for row in label_rows:
        sid = row["source_id"]
        if (sid in labels or sid not in facts or type(row.get("is_laundering")) is not int or
                row["is_laundering"] not in (0, 1) or
                any(row[k] != config[k] for k in ("dataset_version", "run_id")) or
                str(row["event_date"]) != str(timestamp(facts[sid]["event_time"]).date())):
            raise ValueError("Invalid, duplicate, foreign or mismatched evaluation label")
        labels[sid] = row["is_laundering"]
    if set(labels) != set(facts):
        raise ValueError("Missing labels for complete eligible population")
    validated = validate_cases(cases, facts, report)
    alerted = set().union(*(c["source_ids"] for c in validated)) if validated else set()
    currency_population, currency_budget = defaultdict(list), Counter(facts[s]["payment_currency"] for s in alerted)
    for sid, row in facts.items():
        currency_population[row["payment_currency"]].append(sid)
    baseline, currency_audit = set(), []
    for currency, ids in sorted(currency_population.items()):
        ranked = sorted(ids, key=lambda sid: (-Decimal(facts[sid]["amount_paid"]), sid))
        budget = currency_budget[currency]
        selected = ranked[:budget]
        baseline.update(selected)
        currency_audit.append({"payment_currency": currency, "population": len(ids), "matched_alert_budget": budget,
                               "last_selected_amount": format(Decimal(facts[selected[-1]]["amount_paid"]), ".8f") if selected else None})
    if len(baseline) != len(alerted):
        raise ValueError("Amount baseline did not match alert volume")
    matches = defaultdict(list)
    for sid, row in facts.items():
        matches[signature(row)].append(sid)
    audits, eligible_count, recovered = [], Counter(), Counter()
    baseline_recovered = detector_edge_recovered = 0
    attempt_ids = set()
    for attempt in attempts:
        if attempt["attempt_id"] in attempt_ids or not attempt["transactions"]:
            raise ValueError("Duplicate/empty annotated attempt")
        attempt_ids.add(attempt["attempt_id"])
        reference = attempt["transactions"]
        times = [timestamp(r["event_time"]) for r in reference]
        reasons = []
        temporal = all(start <= t < end and t <= cutoff for t in times)
        if not all(start <= t < end for t in times):
            reasons.append("outside_declared_window")
        if any(t > cutoff for t in times):
            reasons.append("after_snapshot_cutoff")
        category = {"FAN-IN": "fan_in", "FAN-OUT": "fan_out", "CYCLE": "cycle"}.get(attempt["annotation_type"], "unsupported")
        shape, reason = topology({pair(r) for r in reference}, category, config["min_counterparties"])
        if reason:
            reasons.append(reason)
        if len({n for r in reference for n in pair(r)}) > config["max_case_nodes"]:
            reasons.append("participant_size_out_of_scope")
        candidates = [matches[signature(r)] for r in reference] if temporal else []
        if temporal:
            if any(not c for c in candidates):
                reasons.append("unmatched_source_transaction")
            if any(len(c) > 1 for c in candidates):
                reasons.append("ambiguous_source_transaction")
            unique = [c[0] for c in candidates if len(c) == 1]
            if len(unique) != len(set(unique)):
                reasons.append("repeated_annotation_source")
            if any(labels[sid] != 1 for sid in unique):
                reasons.append("annotation_label_conflict")
        audit = {"attempt_id": attempt["attempt_id"], "annotation_type": attempt["annotation_type"],
                 "annotation_transaction_count": len(reference), "eligible": not reasons,
                 "exclusion_reasons": reasons, "source_matching": "checked" if temporal else "not_applicable_outside_scope",
                 "source_candidate_counts": [len(c) for c in candidates],
                 "source_candidates": [sorted(c)[:20] for c in candidates],
                 "candidate_diagnostics_capped_at_20": any(len(c) > 20 for c in candidates)}
        if not reasons:
            source_ids = {c[0] for c in candidates}
            pattern = shape["pattern_type"]
            eligible_count[pattern] += 1
            matching_cases = []
            for case in validated:
                same = (case["shape"]["pattern_type"] == pattern and case["shape"]["hub"] == shape["hub"])
                if pattern.startswith("cycle_"):
                    same = same and case["shape"]["edges"] == shape["edges"]
                if same and 5 * len(source_ids & case["source_ids"]) >= 4 * len(source_ids):
                    matching_cases.append(case["case"]["case_id"])
            hit = bool(matching_cases)
            recovered[pattern] += int(hit)
            amount_hit = 5 * len(source_ids & baseline) >= 4 * len(source_ids)
            edge_hit = 5 * len(source_ids & alerted) >= 4 * len(source_ids)
            baseline_recovered += int(amount_hit)
            detector_edge_recovered += int(edge_hit)
            audit.update({"pattern_type": pattern, "recovered": hit, "matching_case_ids": matching_cases,
                          "detector_type_agnostic_coverage_80pct": edge_hit,
                          "amount_baseline_coverage_80pct": amount_hit})
        audits.append(audit)
    eligible = sum(eligible_count.values())
    pattern_metrics = []
    for pattern in ("fan_in", "fan_out", "cycle_2", "cycle_3", "cycle_4"):
        pattern_alerts = set().union(*(c["source_ids"] for c in validated if c["case"]["pattern_type"] == pattern))
        n, hits = eligible_count[pattern], recovered[pattern]
        pattern_metrics.append({"pattern_type": pattern, "eligible_annotated_attempts": n,
                                "recovered_attempts": hits, "attempt_recovery": hits / n if n else None,
                                "transaction_metrics": metrics(set(facts), pattern_alerts, labels)})
    case_audit = [{"case_id": c["case"]["case_id"], "pattern_type": c["case"]["pattern_type"],
                   "supporting_transactions": len(c["source_ids"]),
                   "supporting_positive_labels": sum(labels[s] for s in c["source_ids"])} for c in validated]
    return {"schema_version": 1, "stage": "evaluation", "status": "PASSED", "policy_version": POLICY_VERSION,
            "scope": {k: config[k] for k in ("dataset_version", "run_id", "analysis_id", "window_start", "window_end", "snapshot_cutoff")},
            "benchmark_status": "development_diagnostic_only_not_calibrated_holdout",
            "detector_transaction_metrics": metrics(set(facts), alerted, labels),
            "amount_baseline_transaction_metrics": metrics(set(facts), baseline, labels),
            "amount_baseline_policy": {"mode": "per_payment_currency_matched_alert_volume",
                                       "ordering": "amount_paid descending, source_id ascending for ties",
                                       "calibrated_for_holdout": False, "currency_audit": currency_audit},
            "case_count": len(cases), "case_evidence_rows_including_overlap": sum(len(c["source_ids"]) for c in validated),
            "pattern_metrics": pattern_metrics,
            "annotation_metrics": {"total_file_attempts": len(attempts), "eligible_attempts": eligible,
                                   "recovered_attempts": sum(recovered.values()),
                                   "attempt_recovery": sum(recovered.values()) / eligible if eligible else None,
                                   "detector_type_agnostic_coverage_80pct": detector_edge_recovered / eligible if eligible else None,
                                   "amount_baseline_coverage_80pct": baseline_recovered / eligible if eligible else None,
                                   "denominator_status": "measured" if eligible else "no_eligible_annotated_attempts",
                                   "exclusion_counts_overlapping": dict(Counter(r for a in audits for r in a["exclusion_reasons"]))},
            "interpretation": "Transaction labels assess alerted payments, not case truth. Missing annotations never make a case false. Recovery requires correct type/hub/oriented cycle and >=80% of annotated source transactions in one case. Overlapping case transactions are counted once in headline metrics. No detector inputs are modified.",
            "case_evaluation": case_audit, "attempt_evaluation": audits,
            "detector_alert_source_ids": sorted(alerted), "amount_baseline_alert_source_ids": sorted(baseline)}


def collect_evaluation_window(facts, labels, prep, report):
    """Spark adapter verifies the full preparation join before bounded collection."""
    from pyspark import StorageLevel
    from pyspark.sql import functions as F, types as T
    if (prep.get("status") != "PASSED" or prep.get("schema_version") != 2 or
            not prep.get("label_separation_passed") or not prep.get("source_reference_reconciliation_passed") or
            prep.get("quarantined_rows") != 0 or prep.get("amount_policy", {}).get("scale") != 8 or
            prep.get("amount_policy", {}).get("precision") != 38):
        raise ValueError("Evaluator requires complete precision-safe preparation v2")
    config, start, end, cutoff = scope(report)
    if any(config[k] != prep[k] for k in ("dataset_version", "run_id")):
        raise ValueError("Preparation/detector identity differs")
    if set(facts.columns) != set(prep["fact_columns"]) or not set(FACT_COLUMNS) <= set(facts.columns):
        raise ValueError("Prepared fact schema changed")
    if any(any(w in c.lower() for w in ("launder", "label", "annotation")) for c in facts.columns):
        raise ValueError("Fact schema contains labels")
    keys = ["source_id", "dataset_version", "run_id", "event_date"]
    expected = prep["accepted_rows"]
    if report["full_prepared_rows"] != expected or facts.count() != expected or labels.count() != expected:
        raise ValueError("Full fact/label population differs from passed preparation")
    for col in ("amount_paid", "amount_received"):
        if facts.schema[col].dataType != T.DecimalType(38, 8) or facts.filter(F.col(col).isNull()).limit(1).count():
            raise ValueError("Invalid exact amount facts")
    for frame in (facts, labels):
        invalid = F.lit(False)
        for col in keys:
            invalid = invalid | F.col(col).isNull()
        for col in ("dataset_version", "run_id"):
            invalid = invalid | (F.col(col) != config[col])
        if frame.filter(invalid).limit(1).count() or frame.groupBy("source_id").count().filter("count > 1").limit(1).count():
            raise ValueError("Duplicate/null/foreign fact or label keys")
    if labels.filter(~F.coalesce(F.col("is_laundering").isin(0, 1), F.lit(False))).limit(1).count():
        raise ValueError("Invalid historical label")
    if facts.filter(F.col("event_time").isNull() | (F.to_date("event_time") != F.col("event_date"))).limit(1).count():
        raise ValueError("Invalid fact event date/time")
    joined = facts.join(labels, keys, "inner").persist(StorageLevel.DISK_ONLY)
    try:
        if joined.count() != expected:
            raise ValueError("Full fact/label join lost or multiplied rows")
        actual = {r["payment_format"]: (r["transactions"], r["positive_labels"]) for r in joined.groupBy("payment_format").agg(
            F.count("*").alias("transactions"), F.sum("is_laundering").alias("positive_labels")).collect()}
        reference = {r["payment_format"]: (r["transactions"], r["labelled_laundering"]) for r in prep["accepted_by_format"]}
        if actual != reference:
            raise ValueError("Full labels/formats differ from preparation reference")
        rows = (joined.filter((F.col("event_time") >= start) & (F.col("event_time") < end) & (F.col("event_time") <= cutoff))
                .select(*FACT_COLUMNS, "event_date", "is_laundering").limit(config["max_window_rows"] + 1).collect())
        if len(rows) > config["max_window_rows"] or len(rows) != report["statistics"]["scoped_rows"]:
            raise ValueError("Bounded complete evaluator window does not reconcile")
        records, label_rows = [], []
        for row in rows:
            value = row.asDict()
            records.append({c: value[c] for c in FACT_COLUMNS})
            label_rows.append({c: value[c] for c in keys + ["is_laundering"]})
        return records, label_rows
    finally:
        joined.unpersist()


def canonical_sha(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def validate_evaluator_manifest(manifest):
    required = {"schema_version", "stage", "dataset_version", "run_id", "analysis_id", "inputs",
                "preparation_report_sha256", "detector_report_sha256", "annotations_sha256", "expected_cases"}
    if set(manifest) != required or manifest["schema_version"] != 1 or manifest["stage"] != "evaluator_inputs":
        raise ValueError("Invalid dedicated evaluator manifest")
    for field in ("dataset_version", "run_id", "analysis_id"):
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", manifest[field]):
            raise ValueError("Unsafe evaluator input identity")
    if set(manifest["inputs"]) != {"preparation_report", "detector_report", "annotations"}:
        raise ValueError("Unexpected evaluator input locations")
    for field in ("preparation_report_sha256", "detector_report_sha256", "annotations_sha256"):
        if not re.fullmatch(r"[a-f0-9]{64}", manifest[field]):
            raise ValueError("Invalid input content hash")
    expected = manifest["expected_cases"]
    if len(expected) > 500 or len({c["case_id"] for c in expected}) != len(expected):
        raise ValueError("Duplicate or unbounded expected case inventory")
    for case in expected:
        if set(case) != {"case_id", "emitted_json_sha256"} or any(not re.fullmatch(r"[a-f0-9]{64}", v) for v in case.values()):
            raise ValueError("Invalid frozen case hash inventory")


def validate_index_row(index, case, report):
    config, start, end, cutoff = scope(report)
    strings = {k: case[k] for k in ("dataset_version", "run_id", "analysis_id", "case_id", "pattern_type")}
    strings["bundle_uri"] = report["outputs"]["bundles"] + case["case_id"] + ".json"
    if any(index.get(k) != v for k, v in strings.items()) or any(index.get(k) != case[k] for k in COUNTS):
        raise ValueError("Physical case index identity/count/URI mismatch")
    times = {"window_start": start, "window_end": end, "snapshot_cutoff": cutoff,
             "first_event_time": timestamp(case["first_event_time"]), "last_event_time": timestamp(case["last_event_time"])}
    if any(timestamp(index[k]) != value for k, value in times.items()) or str(index["window_date"]) != str(start.date()):
        raise ValueError("Physical case index time mismatch")


def artifact_payloads(result):
    """Produce compact metrics and separate detailed evidence without mutation."""
    metrics_report = {k: v for k, v in result.items() if k not in
                      ("case_evaluation", "attempt_evaluation", "detector_alert_source_ids", "amount_baseline_alert_source_ids")}
    payloads = {"metrics.json": (json.dumps(metrics_report, indent=2) + "\n").encode(),
                "case_evaluation.jsonl": "".join(json.dumps(r) + "\n" for r in result["case_evaluation"]).encode(),
                "attempt_evaluation.jsonl": "".join(json.dumps(r) + "\n" for r in result["attempt_evaluation"]).encode(),
                "alert_source_ids.json": (json.dumps({"detector": result["detector_alert_source_ids"],
                    "amount_baseline": result["amount_baseline_alert_source_ids"]}, indent=2) + "\n").encode()}
    if any(len(value) > 10_000_000 for value in payloads.values()):
        raise ValueError("Evaluator artifact exceeds bounded output size")
    return payloads


def collect_case_index(spark, report):
    from pyspark.sql.types import StructType
    config, _, _, _ = scope(report)
    # A valid zero-case partition may contain only _SUCCESS; never infer its schema.
    schema = StructType.fromJson(report["case_index_schema"])
    rows = (spark.read.schema(schema).parquet(report["outputs"]["case_index"])
            .limit(config["max_cases"] + 1).collect())
    if len(rows) > config["max_cases"]:
        raise ValueError("Physical case index exceeds the reviewed bound")
    return rows


def main():
    import argparse
    from urllib.parse import urlparse
    import boto3
    from pyspark.sql import SparkSession
    parser = argparse.ArgumentParser()
    for name in ("input-manifest", "output-root", "evaluation-id"):
        parser.add_argument("--" + name, required=True)
    args, _ = parser.parse_known_args()
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", args.evaluation_id):
        raise ValueError("Unsafe evaluation ID")
    s3 = boto3.client("s3")
    if "IfNoneMatch" not in s3.meta.service_model.operation_model("PutObject").input_shape.members:
        raise RuntimeError("Use Glue5.1 with conditional S3 report writes")

    def read_bytes(uri, limit):
        location = urlparse(uri)
        if location.scheme != "s3" or not location.netloc or not location.path.strip("/"):
            raise ValueError("Require explicit S3 object inputs")
        response = s3.get_object(Bucket=location.netloc, Key=location.path.lstrip("/"))
        body = response["Body"]
        try:
            value = body.read(limit + 1)
        finally:
            body.close()
        if len(value) > limit:
            raise ValueError("Evaluator input object exceeds reviewed limit")
        return value

    manifest = json.loads(read_bytes(args.input_manifest, 1_000_000))
    validate_evaluator_manifest(manifest)
    prep = json.loads(read_bytes(manifest["inputs"]["preparation_report"], 1_000_000))
    detector = json.loads(read_bytes(manifest["inputs"]["detector_report"], 1_000_000))
    if (canonical_sha(prep) != manifest["preparation_report_sha256"] or
            canonical_sha(detector) != manifest["detector_report_sha256"]):
        raise ValueError("Frozen quality report contents changed")
    config, _, _, _ = scope(detector)
    if any(config[k] != manifest[k] for k in ("dataset_version", "run_id", "analysis_id")):
        raise ValueError("Manifest and detector identities differ")
    output = urlparse(args.output_root)
    if output.scheme != "s3" or not output.netloc:
        raise ValueError("Explicit S3 output root required")
    suffix = (f"dataset_version={config['dataset_version']}/run_id={config['run_id']}/"
              f"analysis_id={config['analysis_id']}/evaluation_id={args.evaluation_id}")

    def key(zone, tail=""):
        return "/".join(filter(None, [output.path.strip("/"), zone, suffix, tail]))

    for zone in ("evaluation", "quality/evaluation"):
        if s3.list_objects_v2(Bucket=output.netloc, Prefix=key(zone) + "/", MaxKeys=1).get("KeyCount", 0):
            raise ValueError("Evaluation namespace already exists; never overwrite/reuse a partial attempt")
    quality = {"schema_version": 1, "stage": "evaluation", "status": "FAILED", "policy_version": POLICY_VERSION,
               "evaluation_id": args.evaluation_id, "detector_analysis_id": config["analysis_id"],
               "dataset_version": config["dataset_version"], "run_id": config["run_id"],
               "input_manifest": args.input_manifest}
    spark = (SparkSession.builder.appName("is459-aml-evaluation-dev").config("spark.sql.session.timeZone", "UTC")
             .config("spark.sql.shuffle.partitions", "16").getOrCreate())
    try:
        records, label_rows = collect_evaluation_window(spark.read.parquet(prep["outputs"]["transactions"]),
                              spark.read.parquet(prep["outputs"]["labels"]), prep, detector)
        expected = {r["case_id"]: r["emitted_json_sha256"] for r in manifest["expected_cases"]}
        index = collect_case_index(spark, detector)
        if len(index) != len(expected) or {r["case_id"] for r in index} != set(expected):
            raise ValueError("Physical case index differs from pinned inventory")
        cases = []
        for row in index:
            case = json.loads(read_bytes(detector["outputs"]["bundles"] + row["case_id"] + ".json", config["max_bundle_bytes"]))
            emitted = (json.dumps(case, sort_keys=True) + "\n").encode()
            if hashlib.sha256(emitted).hexdigest() != expected[row["case_id"]]:
                raise ValueError("Frozen complete case content changed")
            validate_index_row(row.asDict(), case, detector)
            cases.append(case)
        cases.sort(key=lambda c: c["case_id"])
        annotations = read_bytes(manifest["inputs"]["annotations"], 5_000_000).decode("utf-8")
        attempts = parse_annotations(annotations, manifest["annotations_sha256"])
        result = evaluate(records, label_rows, cases, detector, attempts)
        result["evaluation_id"] = args.evaluation_id
        artifacts = {}
        for name, body in artifact_payloads(result).items():
            object_key = key("evaluation", name)
            s3.put_object(Bucket=output.netloc, Key=object_key, IfNoneMatch="*", Body=body,
                          ContentType="application/json" if name.endswith(".json") else "application/x-ndjson")
            artifacts[name] = {"uri": f"s3://{output.netloc}/{object_key}", "bytes": len(body),
                               "sha256": hashlib.sha256(body).hexdigest()}
        quality.update({"status": "PASSED", "artifacts": artifacts,
                        "benchmark_status": result["benchmark_status"],
                        "eligible_transactions": len(records), "eligible_positive_labels": sum(r["is_laundering"] for r in label_rows),
                        "case_count": len(cases), "eligible_annotated_attempts": result["annotation_metrics"]["eligible_attempts"],
                        "full_prepared_rows_reconciled": prep["accepted_rows"]})
    except Exception as error:
        quality.update({"error_type": type(error).__name__, "error": str(error)[:2000]})
        raise
    finally:
        quality["finished_at_utc"] = datetime.now(timezone.utc).isoformat()
        try:
            s3.put_object(Bucket=output.netloc, Key=key("quality/evaluation", "report.json"), IfNoneMatch="*",
                          Body=(json.dumps(quality, indent=2) + "\n").encode(), ContentType="application/json")
        finally:
            spark.stop()


if __name__ == "__main__":
    main()
