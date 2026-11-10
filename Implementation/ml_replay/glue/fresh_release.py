"""Evaluate a fresh BQ2 shortlist and prepare its immutable TRACE release."""

from collections import defaultdict
from datetime import date, datetime, time, timedelta
from decimal import Decimal
import json
from math import isfinite
from pathlib import Path
import shutil

import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq

from batch_projection import batch_inputs
from dashboard.data import get_case, read_evidence_part
from pipeline.bq2_release import LocalBQ2Objects, TABLES, release_uri
from pipeline.release import BUCKET, encoded, read_object, safe_id, sha
from q2_detect import EVIDENCE_COLUMNS
from rank_shortlist import KINDS, require
from score_payments import sha256


def score_tables(scores: Path, manifest: dict) -> dict[str, pa.Table]:
    tables = {}
    require(set(manifest["artifacts"]) == TABLES.keys(), "The shortlist artifact list is incomplete")
    for name, count_key in TABLES.items():
        artifact = manifest["artifacts"][name]
        path = scores / (name + ".parquet")
        require(artifact["file"] == path.name and sha256(path) == artifact["sha256"],
                f"Score artifact changed: {path.name}")
        table = pq.read_table(path)
        require(len(table) == artifact["rows"] == manifest[count_key], f"Score row count differs: {path.name}")
        tables[name] = table
    return tables


def facts_by_id(facts_path: Path, count: int, sources: dict[str, date | None], start: date,
                cutoff: date) -> tuple[dict[str, dict], int]:
    """Count the full corpus while materializing only rows needed for evaluation."""
    fields = [*EVIDENCE_COLUMNS, "source_record_ordinal"]
    facts = {}
    source_days: dict[date | None, list[str]] = defaultdict(list)
    for source, day in sources.items():
        source_days[day].append(source)
    population = eligible = 0
    previous = None
    keys = pa.array([], type=pa.string())
    for path in sorted(facts_path.glob("event_date=*/*.parquet")):
        day = date.fromisoformat(path.parent.name.removeprefix("event_date="))
        parquet = pq.ParquetFile(path)
        require(day < cutoff, "Prepared payment partition is at or after the cutoff")
        population += parquet.metadata.num_rows
        if day >= start:
            eligible += parquet.metadata.num_rows
        if day != previous:
            keys = pa.array(source_days[day] + source_days[None], type=pa.string())
            previous = day
        if not len(keys):
            continue
        for chunk in parquet.iter_batches(columns=fields):
            for row in chunk.filter(pc.is_in(chunk["source_id"], value_set=keys)).to_pylist():
                source_id = row["source_id"]
                require(source_id not in facts, "Prepared evidence contains a repeated payment identity")
                facts[source_id] = row
    require(population == count and bool(eligible), "Prepared evidence count differs from the scored population")
    require(facts.keys() == sources.keys(),
            "Scored evidence or reference includes a payment missing from its prepared date partition")
    return facts, eligible


def trace_scope(detector: dict, manifest: dict) -> dict:
    config = detector["config"]
    require(all(config[k] == manifest[k] for k in ("dataset_version", "run_id", "analysis_id")),
            "Detector report and shortlist identities differ")
    outputs = detector["outputs"]
    require(detector["status"] == "PASSED" and outputs["case_index"].endswith("/case_index/") and
            outputs["bundles"] == outputs["case_index"].removesuffix("case_index/") + "bundles/",
            "Detector bundles must belong to the passed case index")
    return {
        "release_id": safe_id(manifest["release_id"]),
        "dataset_version": safe_id(manifest["dataset_version"]),
        "run_id": safe_id(manifest["run_id"]),
        "q2": {"analysis_id": safe_id(manifest["analysis_id"]), "bundles": outputs["bundles"]},
    }


def check_evidence(store, scope: dict, cases: pa.Table, index: pa.Table, first_cutoff: datetime,
                   cutoff: datetime) -> tuple[dict[str, list[set[str]]], dict[str, dict]]:
    indexed = {(row["case_id"], row["snapshot_cutoff"]): row for row in index.to_pylist()}
    require(len(indexed) == len(index), "The evidence index contains repeated case snapshots")
    seen = set()
    highlights_by_kind: dict[str, list[set[str]]] = defaultdict(list)
    evidence = {}
    cache = {}
    for row in cases.to_pylist():
        key = (row["case_id"], row["snapshot_cutoff"].isoformat())
        require(key in indexed and key not in seen and first_cutoff <= row["snapshot_cutoff"] <= cutoff,
                "Each ranked case must resolve once within the current batch cutoffs")
        seen.add(key)
        case, _ = get_case(store, scope, indexed[key])
        require(case["pattern_type"] == row["pattern_type"] and case["snapshot_cutoff"] == key[1]
                and case["window_end"] == key[1], "Ranked case window or pattern differs from detector evidence")
        start = datetime.fromisoformat(case["window_start"])
        payments = set()
        preview_count = len(case["transactions"])
        compared_preview = 0
        for part in case["evidence_parts"]:
            rows = read_evidence_part(store, part, cache).splitlines()
            require(len(rows) == part["rows"], "Case evidence chunk row count differs")
            for line in rows:
                payment = json.loads(line)
                source_id = payment["source_id"]
                require(source_id not in payments, "Case evidence is repeated")
                record = {field: payment[field] for field in EVIDENCE_COLUMNS}
                record["event_time"] = datetime.fromisoformat(record["event_time"])
                for field in ("amount_paid", "amount_received"):
                    record[field] = Decimal(record[field])
                require(start <= record["event_time"] < row["snapshot_cutoff"],
                        "Case evidence is outside the detector window")
                require(evidence.setdefault(source_id, record) == record,
                        "Evidence copies disagree for the same source payment")
                if compared_preview < preview_count:
                    require(case["transactions"][compared_preview] == payment, "Case preview differs from full evidence")
                    compared_preview += 1
                payments.add(source_id)
        highlighted = set(row["highlighted_source_ids"])
        require(len(payments) == case["evidence_transaction_count"] and compared_preview == preview_count
                and bool(highlighted) and len(highlighted) == len(row["highlighted_source_ids"])
                and highlighted <= payments, "Ranked case highlights do not match complete case evidence")
        highlights_by_kind[row["pattern_type"]].append(highlighted)
    require(seen == indexed.keys(), "The evidence index includes unranked cases")
    return highlights_by_kind, evidence


def reference_json(ready: dict, field: str, store: LocalBQ2Objects) -> list[dict] | dict:
    ref = ready[field]
    key = ref["key"]
    require(key.startswith("fresh-bq2/reference/") and key.endswith(".json"), f"Invalid {field} reference key")
    body = read_object(store, f"s3://{BUCKET}/{key}")
    require(sha(body) == ref["sha256"], f"The {field} reference checksum changed")
    return json.loads(body)


def reference_rows(ready: dict, field: str, store: LocalBQ2Objects) -> list[dict]:
    if field not in ready:
        return []
    rows = reference_json(ready, field, store)
    require(isinstance(rows, list) and all(isinstance(row, dict) for row in rows),
            f"The {field} reference must contain a JSON array of objects")
    return rows


def payment_metrics(rows: list[dict], eligible: set[str], alert_ids: set[str]) -> dict:
    labels: dict[str, int] = {}
    for row in rows:
        source_id, label = row["source_id"], row["is_laundering"]
        require(source_id in eligible and source_id not in labels and type(label) is int and label in (0, 1),
                "Payment labels must be binary, unique, and inside the new payment period")
        labels[source_id] = label
    evaluated_alerts = alert_ids & labels.keys()
    positives = sum(labels.values())
    hits = sum(labels[source] for source in evaluated_alerts)
    return {
        "labelled_payments": len(labels),
        "labelled_alerts": len(evaluated_alerts),
        "positive_payments": positives,
        "positive_alerts": hits,
        "payment_precision": hits / len(evaluated_alerts) if evaluated_alerts else None,
        "payment_recall": hits / positives if positives else None,
    }


def complete_label_metrics(document: dict, files: list[dict], population: int,
                           prepared: int, alerts: set[str]) -> dict:
    """Evaluate a fully labelled single-file batch using only its positive ordinals."""
    require(isinstance(document, dict) and set(document) == {"source_sha256", "rows", "positive_ordinals"},
            "Complete labels require a source checksum, total row count and positive ordinals")
    require(len(files) == 1 and document["source_sha256"] == files[0]["sha256"]
            and type(document["rows"]) is int and document["rows"] == population == prepared,
            "Complete labels must cover every prepared payment of this source")
    positives = document["positive_ordinals"]
    require(isinstance(positives, list) and all(type(value) is int and 1 <= value <= population for value in positives)
            and len(set(positives)) == len(positives), "Complete labels contain invalid or repeated positive ordinals")
    labelled = {f"{document['source_sha256']}:{ordinal}" for ordinal in positives}
    hits = len(alerts & labelled)
    return {"labelled_payments": population, "labelled_alerts": len(alerts),
            "positive_payments": len(positives), "positive_alerts": hits,
            "payment_precision": hits / len(alerts) if alerts else None,
            "payment_recall": hits / len(positives) if positives else None}


def pattern_metrics(rows: list[dict], eligible: set[str], facts: dict[str, dict],
                    highlights: dict[str, list[set[str]]]) -> dict:
    counts = {}
    seen = set()
    for row in rows:
        kind = row["pattern_type"]
        annotation_id = safe_id(row["annotation_id"])
        source_ids = row["source_ids"]
        require(isinstance(source_ids, list) and all(isinstance(source, str) for source in source_ids),
                "Pattern annotations need a list of source IDs")
        sources = set(source_ids)
        require(kind in KINDS and annotation_id not in seen and bool(sources & eligible) and
                len(sources) == len(source_ids) and sources <= facts.keys(),
                "Pattern annotations must be unique and cover known payments including the new period")
        seen.add(annotation_id)
        counter = counts.setdefault(kind, {"eligible": 0, "recovered": 0})
        counter["eligible"] += 1
        counter["recovered"] += any(sources <= group for group in highlights.get(kind, []))
    return {"eligible_patterns": len(seen), "recovered_patterns": sum(v["recovered"] for v in counts.values()),
            "by_pattern": counts}


def evaluate_batch(ready: dict, mirror: Path, manifest_path: Path, detector_path: Path,
                   scores: Path, output: Path, evidence_store) -> None:
    manifest_bytes = manifest_path.read_bytes()
    detector_bytes = detector_path.read_bytes()
    detector = json.loads(detector_bytes)
    batch = batch_inputs(json.loads(manifest_bytes), detector, mirror)
    shortlist_bytes = (scores / "manifest.json").read_bytes()
    manifest = json.loads(shortlist_bytes)
    start, cutoff = (datetime.combine(date.fromisoformat(ready[key]), time.min) for key in ("batch_start", "cutoff"))
    require(start < cutoff and batch.snapshots[-1].end == cutoff and manifest["schema_version"] == 1
            and manifest["batch_start"] == start.date().isoformat() and manifest["cutoff"] == cutoff.date().isoformat()
            and manifest["scored_payments"] == batch.payments
            and manifest["input_manifest_sha256"] == sha(manifest_bytes)
            and manifest["detector_report_sha256"] == sha(detector_bytes), "The scores do not belong to the prepared batch")
    scope = trace_scope(detector, manifest)
    store = LocalBQ2Objects(mirror)
    tables = score_tables(scores, manifest)
    labels = reference_rows(ready, "labels", store)
    annotations = reference_rows(ready, "annotations", store)
    ranks: dict[int, str] = {}
    for row in tables["ranked_cases"].to_pylist():
        rank, investigation = row["archive_rank"], row["investigation_id"]
        require(type(rank) is int and rank > 0 and ranks.setdefault(rank, investigation) == investigation
                and all(isfinite(row[key]) and 0 <= row[key] <= 1 for key in ("case_score", "investigation_score")),
                "Ranked case has an invalid investigation rank or model score")
    require(set(ranks) == set(range(1, manifest["investigations"] + 1))
            and len(set(ranks.values())) == len(ranks), "Ranked investigations differ from the manifest")
    highlights, evidence = check_evidence(evidence_store, scope, tables["ranked_cases"],
                                          tables["evidence_index"], start + timedelta(days=1), cutoff)
    print(json.dumps({"stage": "evaluate", "step": "verified_case_evidence",
                      "distinct_evidence_payments": len(evidence)}), flush=True)
    sources = {source: row["event_time"].date() for source, row in evidence.items()}
    alerts = tables["payment_alerts"].select(["source_id", "event_date"]).to_pylist()
    for row in alerts:
        require(sources.setdefault(row["source_id"], row["event_date"]) == row["event_date"],
                "Payment alert date disagrees with case evidence")
    for source in {row["source_id"] for row in labels} | {source for row in annotations for source in row["source_ids"]}:
        sources.setdefault(source, None)
    facts, population = facts_by_id(batch.facts_path, batch.payments, sources, start.date(), cutoff.date())
    print(json.dumps({"stage": "evaluate", "step": "matched_prepared_payments",
                      "population": population, "matched": len(facts)}), flush=True)
    for source, payment in evidence.items():
        require(all(payment[field] == facts[source][field] for field in EVIDENCE_COLUMNS),
                f"Case evidence differs from prepared payment: {source}")
    eligible = {source for source, row in facts.items() if start <= row["event_time"] < cutoff}
    highlighted_ids = set().union(*(group for groups in highlights.values() for group in groups))
    alert_ids = set()
    for row in tables["payment_alerts"].to_pylist():
        source = row["source_id"]
        require(source not in alert_ids and source in facts and (source in eligible or source in highlighted_ids),
                "Payment alert is repeated or outside the current batch and its case evidence")
        original = facts[source]
        require(row["event_date"] == original["event_time"].date()
                and row["source_record_ordinal"] == original["source_record_ordinal"]
                and row["case_evidence"] == (source in highlighted_ids)
                and (row["standalone_alert"] is False or source in eligible)
                and (row["standalone_alert"] is True or row["case_evidence"] is True)
                and isfinite(row["blended_score"]) and 0 <= row["blended_score"] <= 1,
                "Payment alert does not match its prepared payment or case evidence")
        alert_ids.add(source)
    require(highlighted_ids <= alert_ids, "A highlighted payment is missing from the alerts table")
    if "complete_labels" in ready:
        complete = reference_json(ready, "complete_labels", store)
        payment_results = complete_label_metrics(complete, ready["files"], population, batch.payments, alert_ids & eligible)
    else:
        payment_results = payment_metrics(labels, eligible, alert_ids)
    metrics = {
        "schema_version": 1, "status": "PASSED", "release_id": scope["release_id"],
        "shortlist_manifest_sha256": sha(shortlist_bytes), "detector_report_sha256": sha(detector_bytes),
        "ready_sha256": sha(encoded(ready)), "eligible_payments": population,
        "eligible_alerts": len(alert_ids & eligible), "scored_payments": batch.payments,
        **payment_results,
        **pattern_metrics(annotations, eligible, facts, highlights),
    }
    with output.open("xb") as stream:
        stream.write(encoded(metrics))


def stage_release(detector_path: Path, scores: Path, evaluation: Path, destination: Path) -> dict[str, str]:
    manifest_raw = (scores / "manifest.json").read_bytes()
    manifest = json.loads(manifest_raw)
    detector_raw = detector_path.read_bytes()
    evaluation_raw = evaluation.read_bytes()
    metrics = json.loads(evaluation_raw)
    scope = trace_scope(json.loads(detector_raw), manifest)
    require(metrics["status"] == "PASSED" and metrics["release_id"] == scope["release_id"]
            and metrics["shortlist_manifest_sha256"] == sha(manifest_raw)
            and metrics["detector_report_sha256"] == sha(detector_raw), "Require a passed evaluation for this exact shortlist")
    score_tables(scores, manifest)
    uri = release_uri(scope["release_id"])
    prefix = uri.removesuffix("release.json")
    scope.update(schema_version=1, release_kind="fresh-bq2", cutoff=manifest["cutoff"],
                 shortlist={"uri": prefix + "manifest.json", "sha256": sha(manifest_raw)},
                 evaluation={"uri": prefix + "evaluation.json", "sha256": sha(evaluation_raw)})
    destination.mkdir()
    for name in TABLES:
        path = destination / (name + ".parquet")
        shutil.copyfile(scores / path.name, path)
        require(sha256(path) == manifest["artifacts"][name]["sha256"], "Score artifact changed during publication")
    (destination / "manifest.json").write_bytes(manifest_raw)
    (destination / "evaluation.json").write_bytes(evaluation_raw)
    release = encoded(scope)
    (destination / "release.json").write_bytes(release)
    return {"uri": uri, "sha256": sha(release)}
