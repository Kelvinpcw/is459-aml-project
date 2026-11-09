"""Fit and freeze the Kaggle-style payment model using HI-Small only."""
from __future__ import annotations

import json
from hashlib import file_digest
from pathlib import Path

from joblib import dump, load
import numpy as np
from sklearn import __version__
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import average_precision_score, precision_recall_curve
from threadpoolctl import threadpool_limits

from prepare_transfer import FACT, MEDIUM, ROOT, SMALL, SMALL_ROWS, SOURCE_COUNT, require

FREEZE = ROOT / "transfer-freeze.json"
MODEL = ROOT / "work" / "transfer.joblib"
BATCH = 220_000
THREADS = 4
LOOKBACKS = (60, 360, 1440, 4320, 10080)
EARLIER_FLOORS = (0.95, 0.8, 0.5, 0.2, 0.05, 0.01)
NO_SEED = np.iinfo(np.int32).max


def checksum(path: Path) -> str:
    with path.open("rb") as stream:
        return file_digest(stream, "sha256").hexdigest()


def write_json(path: Path, value: dict) -> None:
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(value, indent=2) + "\n")
    temp.replace(path)


def matrix(folder: Path, size: int) -> tuple[np.memmap, list[str]]:
    fields = (folder / "feature-names.txt").read_text().splitlines()
    path = folder / "features.f32"
    require(len(fields) == 29 and path.stat().st_size == 4 * size * len(fields),
            f"Incomplete 29-feature matrix in {folder}")
    return np.memmap(path, dtype="<f4", mode="r", shape=(size, len(fields))), fields


def direct_f1_threshold(labels: np.ndarray, scores: np.ndarray) -> float:
    precision, recall, thresholds = precision_recall_curve(labels, scores)
    f1 = 2 * precision * recall / np.maximum(precision + recall, 1e-12)
    return float(thresholds[int(np.argmax(f1[:-1]))])


def later_seed_minutes(sender: np.ndarray, receiver: np.ndarray, minutes: np.ndarray,
                       seeds: np.ndarray) -> np.ndarray:
    """Find the earliest later alert that shares either account with a payment."""
    t = minutes.astype(np.uint64)
    seed_at = t[seeds]
    shift = np.uint64(32)
    times = np.sort(np.concatenate(((sender[seeds].astype(np.uint64) << shift) | seed_at,
                                    (receiver[seeds].astype(np.uint64) << shift) | seed_at,
                                    [np.iinfo(np.uint64).max])).astype(np.uint64))
    result = np.full(len(t), NO_SEED, dtype=np.int32)
    # Process bounded chunks to avoid extra full release-sized integer arrays.
    for start in range(0, len(t), BATCH):
        stop = start + BATCH
        block = slice(start, stop)
        for account in (sender, receiver):
            peers = account[block].astype(np.uint64)
            keys = (peers << shift) | t[block]
            found = times[np.searchsorted(times, keys, side="right")]
            linked = (found >> shift) == peers
            result[block] = np.minimum(result[block], np.where(
                linked, (found & np.uint64(0xffffffff)).astype(np.int32), NO_SEED))
    return result


def metrics(labels: np.ndarray, flags: np.ndarray) -> dict:
    positives = int(np.count_nonzero(labels))
    tp = int(np.count_nonzero(labels & flags))
    alerts = int(np.count_nonzero(flags))
    return {"rows": len(labels), "positive_labels": positives, "alerts": alerts,
            "true_positive": tp, "false_positive": alerts - tp,
            "precision": tp / alerts if alerts else None, "recall": tp / positives if positives else None,
            "f1": 2 * tp / (alerts + positives) if alerts + positives else 0}


def calibrate_retro(facts: np.ndarray, labels: np.ndarray, scores: np.ndarray,
                    threshold: float) -> dict:
    direct = scores >= threshold
    baseline = metrics(labels, direct)
    best = (baseline["f1"], -baseline["alerts"], 0, 1.0)
    choice = {"minutes": 0, "floor": 1.0, "validation": baseline}
    later = later_seed_minutes(facts["sender"], facts["receiver"], facts["minute"], direct)
    for window in LOOKBACKS:
        timely = (later != NO_SEED) & (later - facts["minute"] <= window)
        for floor in EARLIER_FLOORS:
            report = metrics(labels, direct | (timely & (scores >= floor)))
            key = (report["f1"], -report["alerts"], -window, floor)
            if key > best:
                best = key
                choice = {"minutes": window, "floor": floor, "validation": report}
    return choice


def predict(model: HistGradientBoostingClassifier, features: np.ndarray,
            positions: np.ndarray) -> np.ndarray:
    out = np.empty(len(positions), dtype=np.float32)
    for start in range(0, len(positions), BATCH):
        block = slice(start, start + BATCH)
        out[block] = model.predict_proba(features[positions[block]])[:, 1]
    return out


def fit() -> None:
    source = json.loads((SMALL / "manifest.json").read_text())
    facts = np.memmap(SMALL / "facts.bin", dtype=FACT, mode="r", shape=(SMALL_ROWS,))
    features, fields = matrix(SMALL, SMALL_ROWS)
    labels = np.memmap(SMALL / "labels.u8", dtype="u1", mode="r", shape=(SMALL_ROWS + 1,))
    order = np.argsort(facts["minute"], kind="stable").astype(np.uint32)
    times = facts["minute"][order]
    boundaries = times[[int(0.6 * SMALL_ROWS), int(0.8 * SMALL_ROWS)]]
    first, second = np.searchsorted(times, boundaries)
    train, val, test = order[:first], order[first:second], order[second:]
    require(bool(times[first-1] < times[first] and times[second-1] < times[second]),
            "A same-minute group crossed a split")
    train_y, val_y, test_y = (labels[facts["id"][part]] for part in (train, val, test))
    require(len(train_y) + len(val_y) + len(test_y) == SMALL_ROWS
            and int(train_y.sum() + val_y.sum() + test_y.sum()) == source["positive_labels"],
            "HI-Small splits did not reconcile")
    print("HI-Small time split", [(len(y), int(y.sum())) for y in (train_y, val_y, test_y)],
          "fitting a balanced histogram gradient boosting model", flush=True)
    model = HistGradientBoostingClassifier(
        max_iter=300, class_weight="balanced", categorical_features=[3, 4, 5],
        early_stopping=True, validation_fraction=0.1, random_state=0,
    )
    with threadpool_limits(limits=THREADS):
        model.fit(features[train], train_y)
        val_score = predict(model, features, val)
        test_score = predict(model, features, test)
    high = direct_f1_threshold(val_y, val_score)
    low = min(high, float(np.quantile(val_score, 0.98)))
    retro = calibrate_retro(facts[val], val_y, val_score, high)
    direct_test = test_score >= high
    later_test = later_seed_minutes(facts["sender"][test], facts["receiver"][test],
                                    facts["minute"][test], direct_test)
    retro_test = direct_test | ((later_test != NO_SEED)
                               & (later_test - facts["minute"][test] <= retro["minutes"])
                               & (test_score >= retro["floor"]))
    dump(model, MODEL)
    config = {
        "estimator": "HistGradientBoostingClassifier", "sklearn": __version__, "seed": 0,
        "model_sha256": checksum(MODEL), "fitted_iterations": int(model.n_iter_),
        "feature_source_sha256": checksum(ROOT / "features.cpp"), "features": fields,
        "training_data_sha256": source["sha256"], "train_rows": len(train), "train_positives": int(train_y.sum()),
        "validation_rows": len(val), "validation_positives": int(val_y.sum()),
        "test_rows": len(test), "test_positives": int(test_y.sum()), "cutoff_minutes": list(map(int, boundaries)),
        "decision_cutoff": high, "cutoff_basis": "Maximize IBM-positive F1 on HI-Small validation only",
        "delayed_lookback": retro,
        "graph_policy": {"strong_score": high, "support_score": low, "minimum_strong_payments": 2,
                         "support_basis": "98th score percentile on HI-Small validation, capped at strong score",
                         "required_shape": "Five distinct fan peers or all cycle legs",
                         "queue": "Rank surviving cases by payment scores across required links and allow five priority slots per pattern before filling by score"},
        "review_capacity_per_day": 50, "validation_direct": metrics(val_y, val_score >= high),
        "small_test_direct": metrics(test_y, direct_test), "small_test_lookback": metrics(test_y, retro_test),
        "small_test_average_precision": float(average_precision_score(test_y, test_score)),
        "same_minute_policy": "History only from strictly earlier minutes. Graph evidence at the daily snapshot cutoff.",
    }
    write_json(FREEZE, config)
    print("Frozen on HI-Small", high, low, "lookback", retro["minutes"], retro["floor"],
          "source test", config["small_test_direct"], flush=True)


def score() -> None:
    config = json.loads(FREEZE.read_text())
    require(checksum(MODEL) == config["model_sha256"], "Frozen payment model identity changed")
    features, fields = matrix(ROOT / "work" / "medium", SOURCE_COUNT)
    require(fields == config["features"], "Transfer feature order changed")
    facts = np.memmap(MEDIUM / "facts.bin", dtype=FACT, mode="r", shape=(SOURCE_COUNT,))
    model = load(MODEL)
    dest = ROOT / "work" / "medium.scores.f32"
    tmp = dest.with_suffix(".part")
    scores = np.memmap(tmp, dtype="<f4", mode="w+", shape=(SOURCE_COUNT+1,))
    scores[:] = np.nan
    with threadpool_limits(limits=THREADS):
        for start in range(0, SOURCE_COUNT, BATCH):
            block = slice(start, start + BATCH)
            ids = facts["id"][block]
            require(len(np.unique(ids)) == len(ids) and bool(np.all(np.isnan(scores[ids]))),
                    "Duplicate published source IDs during transfer")
            scores[ids] = model.predict_proba(features[block])[:, 1]
            if (start // BATCH) % 20 == 0 or start + BATCH >= SOURCE_COUNT:
                print(f"Scored {min(start+BATCH, SOURCE_COUNT):,} / {SOURCE_COUNT:,} HI-Medium payments",
                      flush=True)
    require(bool(np.all(np.isfinite(scores[1:])) and np.isnan(scores[0])),
            "Transfer did not produce exactly one finite score per source payment")
    scores[0] = 0
    scores.flush()
    tmp.replace(dest)
    write_json(ROOT / "score-manifest.json", {"model_sha256": config["model_sha256"],
              "score_sha256": checksum(dest), "scored_rows": SOURCE_COUNT})
