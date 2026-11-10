"""Train transaction scores in chronological order, freeze on validation, score the full release."""
from hashlib import file_digest
from math import ceil
import json
from pathlib import Path
import sys
import time

from joblib import dump, load
import numpy as np
from sklearn import __version__
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from threadpoolctl import threadpool_limits

from input import REPLAY, ROOT, SOURCE_COUNT, require

N_NEGATIVE = 600_000
SEED = 459
TARGETS = (90, 95, 99, 100)
CATEGORICAL = (2, 3, 4)
PAYMENT_ONLY = 10
BATCH = 180_000
MODELS = ("logistic_context", "boosted_payment_only", "boosted_context")


def sha(path: Path) -> str:
    with path.open("rb") as stream:
        return file_digest(stream, "sha256").hexdigest()


def json_write(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2) + "\n")


class ReleaseFeatures:
    def __init__(self, work: Path):
        self.work = work
        self.manifest = json.loads((REPLAY / "manifest.json").read_text())
        self.names = (work / "feature-names.txt").read_text().splitlines()
        self.offsets = np.cumsum([0, *(day["facts"] for day in self.manifest["daily"])])
        require(int(self.offsets[-1]) == SOURCE_COUNT and len(self.offsets) == 29, "Incomplete date inventory")
        self.ids = np.memmap(work / "ordinals.u32", dtype="<u4", mode="r", shape=(SOURCE_COUNT,))
        self.x = np.memmap(work / "features.f32", dtype="<f4", mode="r", shape=(SOURCE_COUNT, len(self.names)))
        require((work / "features.f32").stat().st_size == 4 * self.x.size
                and (work / "ordinals.u32").stat().st_size == 4 * SOURCE_COUNT,
                "Unexpected model input byte length")

    def day_rows(self, first: int, last: int) -> slice:
        return slice(int(self.offsets[first-1]), int(self.offsets[last]))


def logistic(n: int) -> Pipeline:
    numeric = [i for i in range(n) if i not in CATEGORICAL]
    transforms = ColumnTransformer([
        ("quantitative", StandardScaler(), numeric),
        ("category", OneHotEncoder(handle_unknown="ignore", sparse_output=False, dtype=np.float32),
         list(CATEGORICAL)),
    ])
    return Pipeline([("columns", transforms),
                     ("classifier", LogisticRegression(C=1.0, solver="lbfgs", max_iter=1000, tol=1e-4))])


def boosted() -> HistGradientBoostingClassifier:
    return HistGradientBoostingClassifier(max_iter=115, learning_rate=0.09, max_leaf_nodes=31, max_depth=6,
                                          min_samples_leaf=35, l2_regularization=1.5, early_stopping=False,
                                          categorical_features=list(CATEGORICAL), random_state=SEED)


def fit_inputs(data: ReleaseFeatures) -> tuple[np.ndarray, np.ndarray, np.ndarray, dict]:
    train = data.day_rows(1, 5)
    labels = np.memmap(REPLAY / "labels-development.u8", dtype="u1", mode="r")
    target = labels[data.ids[train]]
    require(bool(np.all(target < 2)), "Training payment does not have a development label")
    positive, negative = np.flatnonzero(target == 1), np.flatnonzero(target == 0)
    require(len(positive) == 7_172, "Unexpected training positives")
    rng = np.random.default_rng(SEED)
    pick = np.sort(np.concatenate((positive, rng.choice(negative, size=N_NEGATIVE, replace=False))))
    y = target[pick]
    weights = np.where(y == 1, 3.0, 1.0)
    return data.x[pick], y, weights, {
        "days": "2022-09-01 through 2022-09-05", "available_payments": len(target),
        "ibm_positive_rows_used": len(positive), "ibm_zero_rows_used": N_NEGATIVE,
        "ibm_zero_rows_available": len(negative), "positive_weight": 3.0, "negative_weight": 1.0,
        "negative_sample_seed": SEED,
    }


def predict(model, data: ReleaseFeatures, rows: slice, columns: int) -> np.ndarray:
    result = np.empty(rows.stop - rows.start, dtype=np.float32)
    for start in range(rows.start, rows.stop, BATCH):
        end = min(start + BATCH, rows.stop)
        values = data.x[start:end, :columns]
        require(bool(np.all(np.isfinite(values))), "Found a non-finite model feature")
        result[start - rows.start:end - rows.start] = model.predict_proba(values)[:, 1]
    return result


def validation_metrics(values: np.ndarray, target: np.ndarray) -> dict:
    positives = target == 1
    known = np.sort(values[positives])[::-1]
    report = {}
    for percent in TARGETS:
        cutoff = known[ceil(len(known) * percent / 100) - 1]
        alert = values >= cutoff
        tp = int(np.count_nonzero(alert & positives))
        n = int(np.count_nonzero(alert))
        report[str(percent)] = {"threshold": float(cutoff), "alerts": n, "true_positive": tp,
                                "recall": tp / len(known), "precision": tp / n}
    return {"payments": len(values), "ibm_positive": len(known),
            "average_precision": float(average_precision_score(target, values)),
            "frozen_validation_targets": report}


def fit(data: ReleaseFeatures) -> None:
    x, y, weights, training = fit_inputs(data)
    val = data.day_rows(6, 8)
    labels = np.memmap(REPLAY / "labels-development.u8", dtype="u1", mode="r")
    val_target = labels[data.ids[val]]
    require(len(val_target) == 5_790_715 and int(val_target.sum()) == 6342 and bool(np.all(val_target < 2)),
            "Validation payment population did not match the published release")
    summary = {}
    models = [(MODELS[0], logistic(len(data.names)), len(data.names)),
              (MODELS[1], boosted(), PAYMENT_ONLY),
              (MODELS[2], boosted(), len(data.names))]
    with threadpool_limits(limits=6):
        for name, model, columns in models:
            started = time.monotonic()
            weight_argument = {"classifier__sample_weight": weights} if name == MODELS[0] else {"sample_weight": weights}
            model.fit(x[:, :columns], y, **weight_argument)
            print(name, "fit", round(time.monotonic() - started, 1), "seconds", flush=True)
            target = data.work / f"{name}.joblib"
            dump(model, target)
            values = predict(model, data, val, columns)
            values.tofile(data.work / f"{name}.validation.f32")
            results = validation_metrics(values, val_target)
            summary[name] = {"feature_count": columns, "model_sha256": sha(target), **results}
            if name == MODELS[0]:
                classifier = model.named_steps["classifier"]
                require(int(classifier.n_iter_[0]) < classifier.max_iter, "Logistic fit did not converge")
                summary[name]["optimizer_converged"] = True
                summary[name]["optimizer_iterations"] = int(classifier.n_iter_[0])
            print(name, "validation AP", f"{results['average_precision']:.5%}", flush=True)
    winner = max(summary, key=lambda name: summary[name]["average_precision"])
    freeze = {
        "release": data.manifest["release"], "training": training,
        "validation_days": "2022-09-06 through 2022-09-08",
        "winner_selection": "Highest average precision on all validation transactions",
        "validation_winner": winner, "scikit_learn": __version__, "model_results": summary,
        "feature_names": data.names, "feature_code_sha256": sha(ROOT / "features.cpp"),
        "fixed_daily_review_cap": 50, "mixed_queue_model_slots": 40, "mixed_queue_structural_slots": 10,
        "fixed_daily_payment_percentiles": [0.1, 0.5, 1, 5, 10],
    }
    json_write(ROOT / "model-freeze.json", freeze)
    print("Selected on validation only:", winner, flush=True)


def score(data: ReleaseFeatures) -> None:
    freeze = json.loads((ROOT / "model-freeze.json").read_text())
    require(freeze["release"] == data.manifest["release"] and freeze["feature_names"] == data.names
            and freeze["feature_code_sha256"] == sha(ROOT / "features.cpp"), "Model freeze differs from the inputs")
    verified_dates = np.memmap(REPLAY / "days.u8", dtype="u1", mode="r")
    checks = np.zeros(SOURCE_COUNT + 1, dtype=bool)
    for day in range(1, 29):
        ordinals = data.ids[data.day_rows(day, day)]
        require(bool(np.all(verified_dates[ordinals] == day)) and not np.any(checks[ordinals])
                and len(np.unique(ordinals)) == len(ordinals), "Scoring stream has missing or repeated payments")
        checks[ordinals] = True
    require(bool(np.all(checks[1:])), "Scoring stream is incomplete")

    with threadpool_limits(limits=6):
        for name, metadata in freeze["model_results"].items():
            target = data.work / f"{name}.joblib"
            require(sha(target) == metadata["model_sha256"], f"Frozen model {name} changed")
            model = load(target)
            scores = np.memmap(data.work / f"{name}.scores.f32", dtype="<f4", mode="w+", shape=(SOURCE_COUNT+1,))
            scores[0] = np.nan
            validation = data.day_rows(6, 8)
            scores[data.ids[validation]] = np.fromfile(data.work / f"{name}.validation.f32", dtype="<f4")
            for first, last in ((1, 5), (9, 16), (17, 28)):
                batch = data.day_rows(first, last)
                values = predict(model, data, batch, metadata["feature_count"])
                scores[data.ids[batch]] = values
                print(name, "scored September", first, "through", last, len(values), flush=True)
            require(bool(np.all(np.isfinite(scores[1:]))), f"Scoring is incomplete for {name}")
            scores.flush()


if __name__ == "__main__":
    data = ReleaseFeatures(Path(sys.argv[1]).resolve())
    {"fit": fit, "score": score}[sys.argv[2]](data)
