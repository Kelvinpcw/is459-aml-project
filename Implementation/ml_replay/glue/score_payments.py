"""Regenerate label-free features and score every October 30 release payment."""

import argparse
from dataclasses import dataclass
from hashlib import file_digest
import json
from pathlib import Path
import shutil
import subprocess
import sys
from tempfile import TemporaryDirectory

from joblib import load
import numpy as np
from sklearn import __version__ as sklearn_version
from threadpoolctl import threadpool_limits


ROWS = 31_898_238
BATCH_ROWS = 196_608


@dataclass(frozen=True)
class Model:
    name: str
    source: Path
    artifact: Path
    artifact_hash: str
    source_hash: str
    expected_score_hash: str
    features: tuple[str, ...]


def sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return file_digest(stream, "sha256").hexdigest()


def read_json(path: Path) -> dict:
    return json.loads(path.read_text())


def models(root: Path) -> tuple[Model, Model, Model]:
    graph = root / "trace-ml-experiment"
    history = root / "trace-q2-triage"
    transfer = root / "trace-kaggle-transfer"
    graph_settings = read_json(graph / "model-freeze.json")
    history_settings = read_json(history / "history_boost-fit.json")
    transfer_settings = read_json(transfer / "transfer-freeze.json")
    saved_payment = read_json(root / "trace-q2-ml-v2/payment-freeze.json")
    saved_transfer = read_json(transfer / "score-manifest.json")
    if any(version != sklearn_version for version in (graph_settings["scikit_learn"],
           history_settings["sklearn"], transfer_settings["sklearn"])):
        raise ValueError(f"Frozen models require their recorded scikit-learn version, found {sklearn_version}")
    return (
        Model("boosted_context", graph / "features.cpp", graph / "work/boosted_context.joblib",
              graph_settings["model_results"]["boosted_context"]["model_sha256"],
              graph_settings["feature_code_sha256"], saved_payment["base_score_sha256"]["boosted_context"],
              tuple(graph_settings["feature_names"])),
        Model("history_boost", history / "history.cpp", history / "work/history_boost.joblib",
              history_settings["models"]["history_boost"]["model_sha256"], history_settings["feature_sha256"],
              saved_payment["base_score_sha256"]["history_boost"], tuple(history_settings["feature_names"])),
        Model("hi_small", transfer / "features.cpp", transfer / "work/transfer.joblib",
              transfer_settings["model_sha256"], transfer_settings["feature_source_sha256"],
              saved_transfer["score_sha256"], tuple(transfer_settings["features"])),
    )


def check_features(model: Model, block: np.ndarray, start: int) -> None:
    missing = np.isnan(block)
    if model.name == "hi_small":
        for gap, previous in (("hours_since_last_pair", "pair_prev_count"),
                              ("hours_since_last_sender_tx", "sender_prev_count")):
            gap_index = model.features.index(gap)
            if not np.array_equal(missing[:, gap_index], block[:, model.features.index(previous)] == 0):
                raise ValueError(f"Missing history disagrees with {previous} at row {start}")
            missing[:, gap_index] = False
    if missing.any() or np.isinf(block).any():
        raise ValueError(f"Unexpected nonfinite feature for {model.name} at row {start}")


def score(model: Model, features: Path, ids: np.ndarray, output: Path) -> dict:
    names = tuple((features.parent / "feature-names.txt").read_text().splitlines())
    if names != model.features or features.stat().st_size != ROWS * len(names) * 4:
        raise ValueError(f"Unexpected feature order or count for {model.name}")
    matrix = np.memmap(features, dtype="<f4", mode="r", shape=(ROWS, len(names)))
    predictor = load(model.artifact)
    values = np.memmap(output, dtype="<f4", mode="w+", shape=(ROWS + 1,))
    values[:] = np.nan
    with threadpool_limits(limits=4):
        for start in range(0, ROWS, BATCH_ROWS):
            part = slice(start, min(ROWS, start + BATCH_ROWS))
            keys, block = ids[part], matrix[part]
            if np.any(keys < 1) or np.any(keys > ROWS) or len(np.unique(keys)) != len(keys):
                raise ValueError(f"Invalid source IDs for {model.name} at row {start}")
            if not np.all(np.isnan(values[keys])):
                raise ValueError(f"Duplicate score for {model.name} at row {start}")
            check_features(model, block, start)
            values[keys] = predictor.predict_proba(block)[:, 1]
            if start % (BATCH_ROWS * 32) == 0 or part.stop == ROWS:
                print(f"{model.name} scored {part.stop:,} / {ROWS:,}", flush=True)
    if not np.all(np.isfinite(values[1:])):
        raise ValueError(f"Incomplete score population for {model.name}")
    if model.name == "hi_small":
        values[0] = 0
    values.flush()
    observed = sha256(output)
    print(f"Completed score file: {model.name} sha256={observed}", flush=True)
    return {"rows": ROWS, "score_sha256": observed, "model_sha256": model.artifact_hash,
            "feature_source_sha256": model.source_hash, "features": list(names),
            "reference_score_sha256": model.expected_score_hash}


def extract_and_score(model: Model, executable: Path, replay: Path, aux: Path, scratch: Path,
                      output: Path, accounts: str) -> dict:
    if model.name == "boosted_context":
        for name in ("formats.u8", "banks.u32"):
            shutil.copyfile(aux / name, scratch / name)
        arguments = [str(replay), str(scratch), accounts]
    elif model.name == "history_boost":
        arguments = [str(replay), str(aux), str(scratch), accounts]
    else:
        arguments = [str(replay), str(aux), str(scratch), str(ROWS), accounts]
    print(f"Extract {len(model.features)} features per payment for {model.name}", flush=True)
    subprocess.run([str(executable), *arguments], check=True)
    if model.name == "boosted_context":
        ids = np.memmap(scratch / "ordinals.u32", dtype="<u4", mode="r", shape=(ROWS,))
    elif model.name == "history_boost":
        metadata = np.memmap(scratch / "payments.bin", dtype=[("id", "<u4"), ("minute", "<i4")],
                             mode="r", shape=(ROWS,))
        ids = metadata["id"]
    else:
        ids = np.memmap(replay / "facts.bin", dtype={"names": ["id"], "formats": ["<u4"],
                        "offsets": [32], "itemsize": 56}, mode="r", shape=(ROWS,))["id"]
    return score(model, scratch / "features.f32", ids, output)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("experiments", type=Path)
    parser.add_argument("attempt", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--cxx", required=True)
    parser.add_argument("--cxx-option", action="append", required=True)
    args = parser.parse_args()
    replay = args.experiments / "trace-q2-full-replay/work"
    source_check = read_json(args.attempt / "source-check.json")
    if (source_check["release_id"], source_check["facts"]) != ("full-20261030-v1", ROWS):
        raise ValueError("The October 30 source verification must pass before scoring")
    args.output.mkdir(mode=0o700)
    aux = args.output / "aux"
    aux.mkdir(mode=0o700)
    prior_aux = args.experiments / "trace-ml-experiment/work"
    subprocess.run([sys.executable, str(prior_aux.parent / "input.py"), str(aux)], check=True)
    for name in ("formats.u8", "banks.u32", "input.json"):
        if sha256(aux / name) != sha256(prior_aux / name):
            raise ValueError(f"Rebuilt payment-format or bank input differs: {name}")
    print("Exact format and bank input parity", flush=True)
    scores = args.output / "scores"
    scores.mkdir(mode=0o700)
    accounts = str(source_check["accounts"])
    results = {}
    for model in models(args.experiments):
        if sha256(model.artifact) != model.artifact_hash or sha256(model.source) != model.source_hash:
            raise ValueError(f"Frozen source or model hash changed for {model.name}")
        with TemporaryDirectory(dir=args.output, prefix=model.name + "-") as folder:
            scratch = Path(folder)
            executable = scratch / "extract_features"
            print(f"Build {model.name} feature extractor from its frozen source", flush=True)
            subprocess.run([args.cxx, "-std=c++20", "-O3", "-pthread", *args.cxx_option, str(model.source),
                            "-o", str(executable)], check=True)
            results[model.name] = extract_and_score(model, executable, replay, aux, scratch,
                                                   scores / f"{model.name}.f32", accounts)
            if results[model.name]["score_sha256"] != model.expected_score_hash:
                raise ValueError(f"Local {model.name} score hash differs from the checkpoint")
    with (args.output / "payment-scores.json").open("x") as stream:
        json.dump({"release_id": source_check["release_id"], "models": results,
                   "scikit_learn": sklearn_version}, stream, indent=2)
        stream.write("\n")


if __name__ == "__main__":
    main()
