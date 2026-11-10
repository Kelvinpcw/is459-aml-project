"""Score a complete, freshly prepared Q2 batch from a local S3 mirror."""

import argparse
from datetime import date, datetime, timedelta
import json
from pathlib import Path
import re
import shutil
import subprocess
from tempfile import TemporaryDirectory

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
from sklearn import __version__ as sklearn_version

from batch_projection import Batch, Projection, batch_inputs, case_partition, project
from pipeline.release import safe_id, sha
from rank_shortlist import (CASE, RESULT, Policy, ReplayFiles, Settings, binary, export_rankings,
                            read_facts, require, save_table, shortlist)
from score_payments import Model, ScoreResult, feature_ids, score_rows, sha256

PAYMENT_MODELS = ("boosted_context", "history_boost", "hi_small")
CASE_MODELS = ("case-shape", "evidence-progress")
ASSETS = {"category-codes.json", "runtime-models.json", "frozen-policy.json", "native/replay"} | {
    f"native/{name}" for name in PAYMENT_MODELS
} | {f"models/{name}.joblib" for name in (*PAYMENT_MODELS, *CASE_MODELS)}


def verify_bundle(bundle: Path, expected: str) -> dict[str, str]:
    raw = (bundle / "bundle.json").read_bytes()
    require(sha(raw) == expected, "Model bundle does not match its approved SHA-256")
    files: dict[str, str] = json.loads(raw)["files"]
    require(set(files) == ASSETS, "Require the frozen policy, category codes, five models and four extractors")
    for name, checksum in sorted(files.items()):
        require(sha256(bundle / name) == checksum, f"Model bundle artifact changed: {name}")
    return files


def category_codes(bundle: Path) -> tuple[dict[str, int], dict[str, int]]:
    codebooks = json.loads((bundle / "category-codes.json").read_text())
    currencies, formats = (codebooks[key] for key in ("currency_codes", "format_codes"))
    for book in (currencies, formats):
        require(bool(book) and len(book) == len(set(book.values())) and
                all(type(code) is int and 0 <= code < 255 for code in book.values()),
                "Invalid trained category codebook")
    require("ACH" in formats, "Trained format codes must include ACH")
    return currencies, formats


def predict(batch: Batch, projection: Projection, work: Path, bundle: Path,
            hashes: dict[str, str], first_weekday: int) -> dict[str, ScoreResult]:
    runtime = json.loads((bundle / "runtime-models.json").read_text())
    require(runtime["scikit_learn"] == sklearn_version and set(runtime["models"]) == set(PAYMENT_MODELS),
            "The supplied runtime differs from the trained payment models")
    replay, aux = work / "replay", work / "aux"
    counts = [str(batch.payments), str(projection.cases), str(projection.memberships)]
    accounts = str(projection.accounts)
    subprocess.run([bundle / "native/replay", replay, accounts, *counts], check=True)
    results: dict[str, ScoreResult] = {}
    for name in PAYMENT_MODELS:
        entry = runtime["models"][name]
        key = f"models/{name}.joblib"
        require(hashes[key] == entry["model_sha256"], f"Model runtime digest differs: {name}")
        executable = bundle / "native" / name
        model = Model(name, executable, bundle / key, hashes[key], entry["feature_source_sha256"],
                      entry["score_sha256"], tuple(entry["features"]))
        with TemporaryDirectory(dir=work, prefix=name + "-") as folder:
            scratch = Path(folder)
            if name == "boosted_context":
                for file in ("formats.u8", "banks.u32"):
                    shutil.copyfile(aux / file, scratch / file)
                arguments = [replay, scratch, accounts, *counts]
            elif name == "history_boost":
                arguments = [replay, aux, scratch, accounts, counts[0]]
            else:
                arguments = [replay, aux, scratch, counts[0], accounts, str(first_weekday)]
            subprocess.run([executable, *arguments], check=True)
            ids = feature_ids(name, scratch, replay, batch.payments)
            results[name] = score_rows(model, scratch / "features.f32", ids, work / f"{name}.f32", batch.payments)
    return results


def rank_batch(batch: Batch, projection: Projection, work: Path, bundle: Path,
               release_id: str, output: Path, batch_start: date) -> dict:
    raw = json.loads((bundle / "frozen-policy.json").read_text())
    first = batch.snapshots[0].end.date() - timedelta(days=1)
    last = batch.snapshots[-1].end.date() - timedelta(days=1)
    settings = Settings(release_id, batch.dataset_version, first, last, "",
                        raw["seed_percent"], raw["support_percent"], raw["minimum_seeds"], raw["rejoin_cutoff"],
                        Policy(**raw["transfer"]), raw["archive_limit"], raw["standalone_cutoff"])
    replay, aux = work / "replay", work / "aux"
    data = ReplayFiles(binary(replay / "cases.bin", CASE, projection.cases),
                       binary(replay / "scored.bin", RESULT, projection.cases),
                       binary(replay / "case-ids.s64", np.dtype("S64"), projection.cases),
                       binary(replay / "evidence.u32", np.dtype("<u4"), projection.memberships),
                       binary(replay / "days.u8", np.dtype("u1"), batch.payments + 1))
    facts = read_facts(replay, aux, batch.payments, projection.accounts)
    graph, history, transfer = (binary(work / f"{name}.f32", np.dtype("<f4"), batch.payments + 1)
                                for name in PAYMENT_MODELS)
    risk = (graph + history) / 2
    versions = shortlist(data, facts, graph, risk, transfer, settings)
    require(first <= batch_start <= last, "Target batch day must be within the detector snapshots")
    return export_rankings(data, facts, versions, risk, bundle / "models/case-shape.joblib",
                           bundle / "models/evidence-progress.joblib", settings, output,
                           (batch_start - first).days + 1, projection.source_ids.__getitem__,
                           projection.source_ordinals)


def write_evidence_index(batch: Batch, output: Path) -> dict:
    """Resolve every ranked case to the detector's existing evidence locator."""
    columns = ("case_id", "bundle_uri", "bundle_member", "bundle_sha256", "snapshot_cutoff")
    ranked = pq.read_table(output / "ranked_cases.parquet", columns=["case_id", "snapshot_cutoff"])
    by_cutoff: dict[datetime, set[str]] = {}
    for row in ranked.to_pylist():
        by_cutoff.setdefault(row["snapshot_cutoff"], set()).add(row["case_id"])
    resolved = []
    for snap in batch.snapshots:
        if snap.end not in by_cutoff:
            continue
        case_ids = by_cutoff[snap.end]
        matches = pq.read_table(case_partition(batch, snap), columns=list(columns), partitioning=None,
                                filters=[("case_id", "in", sorted(case_ids))]).to_pylist()
        require(len(matches) == len(case_ids) and {row["case_id"] for row in matches} == case_ids and
                all(row["snapshot_cutoff"] == snap.end and all(row[c] for c in columns) for row in matches),
                f"Ranked cases do not resolve to unique detector evidence at {snap.end.isoformat()}")
        for row in matches:
            require(row["bundle_member"] == row["case_id"] + ".json" and
                    re.fullmatch(r"[0-9a-f]{64}", row["bundle_sha256"]) is not None,
                    f"Invalid evidence locator for ranked case {row['case_id']}")
        resolved.extend({**row, "snapshot_cutoff": snap.end.isoformat()} for row in matches)
    require(len(resolved) == len(ranked), "Some ranked cases did not resolve to detector evidence")
    return save_table(pa.Table.from_pylist(resolved, schema=pa.schema([(name, pa.string()) for name in columns])),
                      output / "evidence_index.parquet")


def score_batch(manifest_path: Path, report_path: Path, mirror: Path, bundle: Path,
                bundle_sha256: str, release_id: str, destination: Path) -> None:
    score_fresh_batch(manifest_path, report_path, mirror, bundle, bundle_sha256, release_id, destination, None)


def score_fresh_batch(manifest_path: Path, report_path: Path, mirror: Path, bundle: Path,
                      bundle_sha256: str, release_id: str, destination: Path, batch_start: date | None) -> None:
    safe_id(release_id)
    require(not destination.exists(), f"Fresh ML destination required: {destination}")
    raw_manifest, raw_report = manifest_path.read_bytes(), report_path.read_bytes()
    batch = batch_inputs(json.loads(raw_manifest), json.loads(raw_report), mirror)
    hashes = verify_bundle(bundle, bundle_sha256)
    policy = json.loads((bundle / "frozen-policy.json").read_text())
    require(policy["artifact_hashes"]["case_shape"] == hashes["models/case-shape.joblib"] and
            policy["artifact_hashes"]["evidence_progress"] == hashes["models/evidence-progress.joblib"],
            "Case models do not match the frozen ranking policy")
    currencies, formats = category_codes(bundle)
    first = batch.snapshots[0].end.date() - timedelta(days=1)
    with TemporaryDirectory(prefix=".q2-ml-batch-", dir=destination.parent) as folder:
        work = Path(folder)
        replay, aux, output = (work / part for part in ("replay", "aux", "output"))
        for path in (replay, aux, output):
            path.mkdir()
        projection = project(batch, replay, aux, currencies, formats)
        models = predict(batch, projection, work, bundle, hashes, first.weekday())
        target = batch_start if batch_start is not None else first
        result = rank_batch(batch, projection, work, bundle, release_id, output, target)
        result["artifacts"]["evidence_index"] = write_evidence_index(batch, output)
        result.update(schema_version=1, run_id=batch.run_id, analysis_id=batch.analysis_id,
                      input_manifest_sha256=sha(raw_manifest), detector_report_sha256=sha(raw_report),
                      batch_start=target.isoformat(), cutoff=batch.snapshots[-1].end.date().isoformat(),
                      scored_payments=batch.payments, case_model_sha256={
                          name: hashes[f"models/{name}.joblib"] for name in CASE_MODELS
                      },
                      input_case_snapshots=projection.cases, model_bundle_sha256=bundle_sha256, models=models)
        (output / "manifest.json").write_text(json.dumps(result, indent=2) + "\n")
        output.rename(destination)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("input-manifest", "detector-report", "mirror", "model-bundle", "destination"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--model-bundle-sha256", required=True)
    parser.add_argument("--release-id", required=True)
    args = parser.parse_args()
    score_batch(args.input_manifest, args.detector_report, args.mirror, args.model_bundle,
                args.model_bundle_sha256, args.release_id, args.destination)
