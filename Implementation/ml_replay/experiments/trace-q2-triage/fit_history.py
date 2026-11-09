"""Compare tree ensembles using only earlier minutes of account history."""
from __future__ import annotations

from hashlib import file_digest
from pathlib import Path
import json
import sys
import time

from joblib import dump
import numpy as np
from sklearn import __version__
from sklearn.ensemble import ExtraTreesClassifier, HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.metrics import average_precision_score
from threadpoolctl import threadpool_limits

ROOT = Path(__file__).resolve().parent
REPLAY = ROOT.parent / "trace-q2-full-replay" / "work"
WORK = ROOT / "work"
TOTAL = 31_898_238
SEED = 459
BATCH = 196_608
DTYPE = np.dtype([("ordinal", "<u4"), ("minute", "<i4")])


def sha(path: Path) -> str:
    with path.open("rb") as stream:
        return file_digest(stream, "sha256").hexdigest()


def main() -> None:
    names = (WORK / "feature-names.txt").read_text().splitlines()
    if not names or (WORK / "features.f32").stat().st_size != TOTAL * len(names) * 4:
        raise ValueError("Account-history feature extraction is incomplete")
    x = np.memmap(WORK / "features.f32", dtype="<f4", mode="r", shape=(TOTAL, len(names)))
    meta = np.memmap(WORK / "payments.bin", dtype=DTYPE, mode="r", shape=(TOTAL,))
    days = np.memmap(REPLAY / "days.u8", dtype="u1", mode="r", shape=(TOTAL+1,))
    labels = np.memmap(REPLAY / "labels-development.u8", dtype="u1", mode="r", shape=(TOTAL+1,))
    manifest = json.loads((REPLAY / "manifest.json").read_text())
    bounds = np.cumsum([0, *(d["facts"] for d in manifest["daily"])])
    if bounds[-1] != TOTAL or len(bounds) != 29:
        raise ValueError("Prepared dates do not reconcile to the release")
    for i in range(28):
        sl = slice(bounds[i], bounds[i+1])
        if not np.all(days[meta["ordinal"][sl]] == i+1) or not np.all(meta["minute"][sl] // 1440 == i):
            raise ValueError(f"Feature dates disagree with the release on September {i+1}")
    first_five = labels[meta["ordinal"][:bounds[5]]]
    positive, negative = np.flatnonzero(first_five == 1), np.flatnonzero(first_five == 0)
    if len(positive) != 7172 or len(positive) + len(negative) != len(first_five):
        raise ValueError("Unexpected fit label population")
    validation = slice(bounds[5], bounds[8])
    validation_labels = labels[meta["ordinal"][validation]]
    if np.count_nonzero(validation_labels == 1) != 6342 or not np.all(validation_labels < 2):
        raise ValueError("Unexpected validation label population")
    result = {
        "release": manifest["release"], "train_days": [1, 5], "validation_days": [6, 8],
        "time_policy": "only timestamps strictly before the payment minute for historical features",
        "feature_names": names, "feature_sha256": sha(ROOT / "history.cpp"),
        "sklearn": __version__, "seed": SEED, "available_training_negatives": len(negative),
        "training_positives": len(positive), "models": {},
    }
    model_name = sys.argv[1]
    models = {
        "history_boost": HistGradientBoostingClassifier(
            max_iter=150, learning_rate=0.075, max_leaf_nodes=31, max_depth=7, min_samples_leaf=30,
            l2_regularization=1.5, categorical_features=[2, 3, 4], early_stopping=False, random_state=SEED),
        "random_forest": RandomForestClassifier(
            n_estimators=48, max_depth=15, min_samples_leaf=12, max_features=0.55,
            n_jobs=5, random_state=SEED),
        "extra_trees": ExtraTreesClassifier(
            n_estimators=64, max_depth=18, min_samples_leaf=10, max_features=0.65,
            n_jobs=5, random_state=SEED),
    }
    model = models[model_name]
    n_neg = 600_000 if model_name == "history_boost" else 240_000
    negative_sample = np.random.default_rng(SEED).choice(negative, n_neg, replace=False)
    pick = np.sort(np.concatenate((positive, negative_sample)))
    target = first_five[pick]
    weights = np.where(target == 1, 3.0, 1.0)
    with threadpool_limits(limits=5):
        started = time.monotonic()
        model.fit(x[pick], target, sample_weight=weights)
        model_path = WORK / f"{model_name}.joblib"
        dump(model, model_path)
        print(model_name, "fit seconds", round(time.monotonic()-started, 1), flush=True)
        temporary = WORK / f"{model_name}.scores.partial"
        values = np.memmap(temporary, dtype="<f4", mode="w+", shape=(TOTAL+1,))
        values[:] = np.nan
        for i in range(28):
            for start in range(bounds[i], bounds[i+1], BATCH):
                end = min(start + BATCH, bounds[i+1])
                block = x[start:end]
                if not np.all(np.isfinite(block)):
                    raise ValueError(f"Unexpected invalid history features in {start}:{end}")
                values[meta["ordinal"][start:end]] = model.predict_proba(block)[:, 1]
            if i in (4, 7, 15, 27):
                print(model_name, "scored through Sep", i+1, flush=True)
        if not np.all(np.isfinite(values[1:])):
            raise ValueError(f"Incomplete payment scores for {model_name}")
        values.flush()
        ap = average_precision_score(validation_labels, values[meta["ordinal"][validation]])
        result["models"][model_name] = {
            "training_negatives_used": n_neg, "positive_weight": 3.0, "negative_weight": 1.0,
            "validation_average_precision": float(ap), "model_sha256": sha(model_path),
            "score_sha256": sha(temporary),
        }
        temporary.rename(WORK / f"{model_name}.scores.f32")
        (ROOT / f"{model_name}-fit.json").write_text(json.dumps(result, indent=2) + "\n")
        print(model_name, "validation average precision", f"{ap:.5%}", flush=True)


if __name__ == "__main__":
    main()
