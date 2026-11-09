"""Package a validated replay and its original case references for the TRACE overlay."""

import argparse
from collections import defaultdict
from hashlib import file_digest
import json
from pathlib import Path
import re
import shutil
import sys

import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq


APP_FILES = ("app.py", "ml_replay.py")
REPLAY_FILES = ("manifest.json", "evaluation.json", "ranked_cases.parquet", "payment_alerts.parquet")
ARCHIVE = "published/releases/full-20261030-v1/manifest.json"


def digest(path: Path) -> str:
    with path.open("rb") as stream:
        return file_digest(stream, "sha256").hexdigest()


def index_cases(catalog, cases: pa.Table) -> pa.Table:
    selected = defaultdict(set)
    for row in cases.select(["case_id", "snapshot_cutoff"]).to_pylist():
        selected[row["snapshot_cutoff"].isoformat()].add(row["case_id"])
    batches = []
    for cutoff, ids in sorted(selected.items()):
        source = catalog.table(cutoff).select(["case_id", "bundle_uri", "bundle_member", "bundle_sha256"])
        found = source.filter(pc.is_in(source["case_id"], value_set=pa.array(sorted(ids), type=source["case_id"].type)))
        if len(found) != len(ids) or set(found["case_id"].to_pylist()) != ids:
            raise ValueError(f"Could not match every case to the original index at {cutoff}")
        batches.append(found.append_column("snapshot_cutoff", pa.array([cutoff] * len(found), type=pa.string())))
    result = pa.concat_tables(batches)
    if len(result) != len(cases):
        raise ValueError("The shortlist includes repeated case snapshots")
    return result


def prepare(mirror: Path, source: Path, dashboard: Path, destination: Path, name: str, evaluation_sha: str) -> str:
    from local_cases import LocalCases
    from local_data import LocalObjects
    from pipeline.release import BUCKET

    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{7,63}", name):
        raise ValueError("Require a unique ML replay release name")
    manifest = json.loads((source / "manifest.json").read_text())
    evaluation = source / "evaluation.json"
    if digest(evaluation) != evaluation_sha:
        raise ValueError("The replay evaluator output does not match the reviewed checksum")
    metrics = json.loads(evaluation.read_text())
    archived = mirror / ARCHIVE
    release = json.loads(archived.read_text())
    manifest_sha = digest(source / "manifest.json")
    if (manifest["release_id"] != release["release_id"] or manifest["dataset_version"] != release["dataset_version"]
            or metrics["release_id"] != release["release_id"]
            or metrics["shortlist_manifest_sha256"] != manifest_sha):
        raise ValueError("The replay did not pass evaluation on the pinned release")
    for table in ("ranked_cases", "payment_alerts"):
        artifact = manifest["artifacts"][table]
        if artifact["file"] != table + ".parquet" or digest(source / artifact["file"]) != artifact["sha256"]:
            raise ValueError(f"Replay artifact does not match the evaluator inputs: {table}")

    cases = pq.read_table(source / "ranked_cases.parquet")
    evidence = index_cases(LocalCases(LocalObjects(mirror), release), cases)
    destination.mkdir(mode=0o700, parents=True)
    for file in REPLAY_FILES:
        shutil.copyfile(source / file, destination / file)
    index = destination / "evidence_index.parquet"
    pq.write_table(evidence, index, compression="zstd")
    descriptor = {
        "schema_version": 1,
        "base_release": {"uri": f"s3://{BUCKET}/{ARCHIVE}", "sha256": digest(archived)},
        "shortlist_sha256": manifest_sha,
        "evaluation_sha256": digest(source / "evaluation.json"),
        "evidence_index_sha256": digest(index),
    }
    for file in APP_FILES:
        shutil.copyfile(dashboard / file, destination / file)
    ref = destination / "release.json"
    ref.write_text(json.dumps(descriptor, sort_keys=True, indent=2) + "\n")
    return f"s3://{BUCKET}/published/ml-replays/{name}/release.json {digest(ref)}"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("local_trace", type=Path)
    parser.add_argument("evaluated_replay", type=Path)
    parser.add_argument("dashboard", type=Path)
    parser.add_argument("destination", type=Path)
    parser.add_argument("name")
    parser.add_argument("evaluation_sha")
    args = parser.parse_args()
    sys.path[:0] = [str(args.local_trace), str(args.dashboard.parent)]
    print(prepare(args.local_trace / "mirror", args.evaluated_replay, args.dashboard, args.destination,
                  args.name, args.evaluation_sha))


if __name__ == "__main__":
    main()
