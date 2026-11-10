"""Run one stage of the fresh BQ2 workflow against a local mirror or S3."""

import argparse
from base64 import b64encode
from contextlib import closing
from dataclasses import dataclass
from datetime import date, timedelta
from hashlib import file_digest, sha256
import json
import os
from pathlib import Path, PurePosixPath
import re
from shutil import copyfile, copyfileobj
from tempfile import NamedTemporaryFile, TemporaryDirectory
from typing import Protocol

from pipeline.release import ACCOUNT, BUCKET, REGION, encoded, safe_id, sha, split_uri

STAGES = ("prepare", "detect", "score", "evaluate", "publish")
CURRENT = "published/bq2/current.json"
SCALE_CHECK = "published/bq2/scale-check.json"
MAX_OBJECT = 64 * 1024 * 1024
HEX = re.compile(r"[0-9a-f]{64}")


@dataclass(frozen=True)
class Object:
    body: bytes
    etag: str


class Store(Protocol):
    def read(self, key: str) -> Object: ...
    def current(self, key: str) -> Object | None: ...
    def write(self, key: str, body: bytes, previous: str | None) -> None: ...
    def download(self, key: str, path: Path) -> None: ...
    def upload(self, key: str, path: Path, digest: str) -> None: ...


def object_key(value: str) -> str:
    if (not isinstance(value, str) or value != PurePosixPath(value).as_posix() or
            not re.fullmatch(r"[A-Za-z0-9_.=/\-]+", value) or value.startswith("/") or
            any(part in (".", "..") for part in value.split("/"))):
        raise ValueError(f"Invalid object key: {value!r}")
    return value


class LocalStore:
    def __init__(self, root: Path):
        self.root = root

    def read(self, key: str) -> Object:
        path = self.root / object_key(key)
        if path.stat().st_size > MAX_OBJECT:
            raise ValueError(f"Object exceeds the batch demo limit: {key}")
        body = path.read_bytes()
        return Object(body, sha(body))

    def current(self, key: str) -> Object | None:
        try:
            return self.read(key)
        except FileNotFoundError:
            return None

    def write(self, key: str, body: bytes, previous: str | None) -> None:
        import fcntl

        path = self.root / object_key(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        with (self.root / ".fresh-bq2-write.lock").open("ab") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            if path.exists():
                existing = self.read(key)
                if previous is None and key not in (CURRENT, SCALE_CHECK) and existing.body == body:
                    return
                if existing.etag != previous:
                    raise FileExistsError(f"Object changed before publication: {key}")
            elif previous is not None:
                raise FileNotFoundError(key)
            with NamedTemporaryFile(dir=path.parent, delete=False) as temp:
                scratch = Path(temp.name)
                try:
                    temp.write(body)
                    temp.flush()
                    os.replace(scratch, path)
                finally:
                    scratch.unlink(missing_ok=True)

    def download(self, key: str, path: Path) -> None:
        copyfile(self.root / object_key(key), path)

    def upload(self, key: str, path: Path, digest: str) -> None:
        target = self.root / object_key(key)
        target.parent.mkdir(parents=True, exist_ok=True)
        with path.open("rb") as source, target.open("xb") as destination:
            copyfileobj(source, destination)


class S3Store:
    def __init__(self, client):
        self.client = client

    def read(self, key: str) -> Object:
        reply = self.client.get_object(Bucket=BUCKET, Key=object_key(key), ExpectedBucketOwner=ACCOUNT)
        with closing(reply["Body"]) as body:
            if reply["ContentLength"] > MAX_OBJECT:
                raise ValueError(f"Object exceeds the batch demo limit: {key}")
            return Object(body.read(), reply["ETag"].strip('"'))

    def current(self, key: str) -> Object | None:
        # Use an exact-prefix listing so absence is distinguishable from denied access.
        reply = self.client.list_objects_v2(Bucket=BUCKET, Prefix=key, MaxKeys=1,
                                            ExpectedBucketOwner=ACCOUNT)
        if not reply.get("Contents") or reply["Contents"][0]["Key"] != key:
            return None
        return self.read(key)

    def write(self, key: str, body: bytes, previous: str | None) -> None:
        from botocore.exceptions import ClientError

        condition = {"IfNoneMatch": "*"} if previous is None else {"IfMatch": f'"{previous}"'}
        try:
            self.client.put_object(Bucket=BUCKET, Key=object_key(key), Body=body,
                                   ExpectedBucketOwner=ACCOUNT, ServerSideEncryption="AES256", **condition)
        except ClientError as error:
            if (previous is None and key not in (CURRENT, SCALE_CHECK) and
                    error.response["Error"]["Code"] in ("PreconditionFailed", "412") and
                    self.read(key).body == body):
                return
            raise

    def download(self, key: str, path: Path) -> None:
        reply = self.client.get_object(Bucket=BUCKET, Key=object_key(key), ExpectedBucketOwner=ACCOUNT)
        with closing(reply["Body"]) as body, path.open("xb") as stream:
            copyfileobj(body, stream, length=8 * 1024 * 1024)

    def upload(self, key: str, path: Path, digest: str) -> None:
        from botocore.exceptions import ClientError

        checksum = b64encode(bytes.fromhex(digest)).decode("ascii")
        with path.open("rb") as stream:
            try:
                self.client.put_object(Bucket=BUCKET, Key=object_key(key), Body=stream, IfNoneMatch="*",
                                       ExpectedBucketOwner=ACCOUNT, ServerSideEncryption="AES256",
                                       ChecksumSHA256=checksum)
            except ClientError as error:
                if error.response["Error"]["Code"] not in ("PreconditionFailed", "412"):
                    raise
                current = self.client.head_object(Bucket=BUCKET, Key=key, ExpectedBucketOwner=ACCOUNT,
                                                  ChecksumMode="ENABLED")
                if current.get("ChecksumSHA256") != checksum:
                    raise

    def download_case_index(self, scratch: Path, prefix: str) -> None:
        objects = self.client.get_paginator("list_objects_v2")
        for page in objects.paginate(Bucket=BUCKET, Prefix=prefix, ExpectedBucketOwner=ACCOUNT):
            for entry in page.get("Contents", ()):
                key = object_key(entry["Key"])
                if re.fullmatch(r"window_date=\d{4}-\d{2}-\d{2}/part-[\w.-]+\.parquet",
                                key.removeprefix(prefix)):
                    path = scratch / key
                    path.parent.mkdir(parents=True, exist_ok=True)
                    self.download(key, path)


class S3Evidence:
    """Keep requested immutable case shards on disk during evaluation."""

    def __init__(self, store: S3Store, cache: Path):
        self.store = store
        self.cache = cache

    def get_object(self, Bucket: str, Key: str) -> dict:
        if Bucket != BUCKET:
            raise ValueError("Case evidence must be in the project bucket")
        path = self.cache / object_key(Key)
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            self.store.download(Key, path)
        return {"Body": path.open("rb")}


def reference(ref: dict, prefix: str, suffix: str) -> tuple[str, str]:
    if not isinstance(ref, dict) or set(ref) != {"key", "sha256"}:
        raise ValueError("Input references require a key and SHA-256")
    key, checksum = object_key(ref["key"]), ref["sha256"]
    if (not key.startswith(prefix) or not key.endswith(suffix) or
            not isinstance(checksum, str) or not HEX.fullmatch(checksum)):
        raise ValueError(f"Input outside its allowed prefix, type or checksum contract: {key}")
    return key, checksum


def parse_ready(raw: bytes) -> dict:
    value = json.loads(raw)
    required = {"schema_version", "dataset_version", "history_start", "batch_start", "cutoff", "files", "accounts"}
    references = ("labels", "complete_labels", "annotations")
    if (not isinstance(value, dict) or not required <= set(value) <= required | set(references) or
            type(value["schema_version"]) is not int or value["schema_version"] != 1):
        raise ValueError("Unsupported fresh BQ2 ready manifest")
    if not safe_id(value["dataset_version"]).startswith("fresh-bq2-"):
        raise ValueError("Require an isolated fresh-bq2 dataset identifier")
    history, start, cutoff = (date.fromisoformat(value[field]) for field in ("history_start", "batch_start", "cutoff"))
    if (not history <= start < cutoff or (cutoff - history).days > 29 or
            (history.isoformat(), start.isoformat(), cutoff.isoformat()) !=
            (value["history_start"], value["batch_start"], value["cutoff"])):
        raise ValueError("Require a nonempty batch and at most 29 days of supplied transactions")
    if not isinstance(value["files"], list) or not 1 <= len(value["files"]) <= 32:
        raise ValueError("Require 1–32 transaction CSV references")
    files = [reference(row, "fresh-bq2/incoming/", ".csv") for row in value["files"]]
    accounts = reference(value["accounts"], "fresh-bq2/incoming/", ".csv")
    if not files or len({key for key, _ in [*files, accounts]}) != len(files) + 1:
        raise ValueError("Require unique transaction CSVs and a separate account CSV")
    if "labels" in value and "complete_labels" in value:
        raise ValueError("Supply either individual or complete payment labels")
    for name in references:
        if name in value:
            reference(value[name], "fresh-bq2/reference/", ".json")
    return value


def hash_file(path: Path) -> str:
    with path.open("rb") as stream:
        return file_digest(stream, "sha256").hexdigest()


def materialize(store: Store, scratch: Path, key: str, checksum: str) -> None:
    path = scratch / key
    path.parent.mkdir(parents=True, exist_ok=True)
    store.download(key, path)
    if hash_file(path) != checksum:
        raise ValueError(f"Pinned object bytes changed: {key}")


def persist_stage(store: Store, scratch: Path, stage_dir: str, paths: list[Path], identity: str) -> None:
    files: dict[str, str] = {}
    for path in sorted(paths):
        key = path.relative_to(scratch).as_posix()
        files[key] = hash_file(path)
        store.upload(key, path, files[key])
    store.write(stage_dir + "/inventory.json", encoded({"identity": identity, "files": files}), None)


def restore_stage(store: Store, scratch: Path, stage_dir: str, identity: str, prefixes: tuple[str, ...],
                  include_data: bool) -> None:
    inventory = json.loads(store.read(stage_dir + "/inventory.json").body)
    if inventory["identity"] != identity:
        raise ValueError(f"Stage outputs belong to another batch: {stage_dir}")
    for key, checksum in inventory["files"].items():
        object_key(key)
        if not key.startswith((stage_dir + "/", *prefixes)):
            raise ValueError(f"Unexpected artifact in stage inventory: {key}")
        if include_data or key.startswith(stage_dir + "/"):
            materialize(store, scratch, key, checksum)


def load_bundle(store: Store, path: Path, bundle_uri: str, checksum: str) -> None:
    from score_batch import ASSETS

    _, prefix = split_uri(bundle_uri)
    if not prefix.startswith("fresh-bq2/models/") or not prefix.endswith("/"):
        raise ValueError("Require an immutable fresh BQ2 model prefix")
    raw = store.read(prefix + "bundle.json").body
    files = json.loads(raw)["files"]
    if sha(raw) != checksum or set(files) != ASSETS:
        raise ValueError("Model bundle does not match the approved manifest")
    path.mkdir()
    (path / "bundle.json").write_bytes(raw)
    for name, digest in files.items():
        body = store.read(prefix + name).body
        if sha(body) != digest:
            raise ValueError(f"Model bundle artifact changed: {name}")
        target = path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(body)
        if name.startswith("native/"):
            target.chmod(0o700)


def release_is_current(current: Object | None, release_id: str, cutoff: str) -> bool:
    if current is None:
        return False
    value = json.loads(current.body)
    if value["release_id"] == release_id:
        return True
    if date.fromisoformat(value["cutoff"]) >= date.fromisoformat(cutoff):
        raise ValueError("Fresh release cutoff must advance the published BQ2 view")
    return False


def run_stage(store: Store, scratch: Path, stage: str, ready_key: str, ready_etag: str, attempt: str,
              bundle_uri: str, bundle_sha256: str, local_bundle: Path | None, pointer: str) -> str:
    safe_id(attempt)
    if (stage not in STAGES or not object_key(ready_key).startswith("fresh-bq2/incoming/") or
            not ready_key.endswith("/ready.json") or not HEX.fullmatch(bundle_sha256)
            or pointer not in (CURRENT, SCALE_CHECK)):
        raise ValueError("Invalid fresh BQ2 stage, manifest key or model digest")
    ready_object = store.read(ready_key)
    if ready_object.etag != ready_etag:
        raise ValueError("Ready manifest differs from the ETag supplied at workflow start")
    ready = parse_ready(ready_object.body)
    namespace = pointer if pointer == SCALE_CHECK else ""
    identity = sha256((sha(ready_object.body) + bundle_sha256 + namespace).encode()).hexdigest()
    release_id = "fresh-" + identity
    current = store.current(pointer)
    if release_is_current(current, release_id, ready["cutoff"]):
        return "already-published"

    root = f"fresh-bq2/runs/{attempt}"
    stage_dir = root + "/" + stage
    work = scratch / stage_dir
    work.mkdir(parents=True)
    manifest = scratch / root / "prepare/detector-inputs.json"
    detector = scratch / root / "detect/detector-report.json"
    scores = scratch / root / "score"
    evaluation = scratch / root / "evaluate/evaluation.json"
    suffix = f"dataset_version={ready['dataset_version']}/run_id={attempt}/"
    facts_prefix, cases_prefix = "curated/" + suffix, "gold/cases/" + suffix
    dependencies = {
        "prepare": (), "detect": ("prepare",), "score": ("prepare", "detect"),
        "evaluate": ("prepare", "detect", "score"), "publish": ("detect", "score", "evaluate"),
    }
    prefixes = {"prepare": (facts_prefix,), "detect": (cases_prefix,), "score": (), "evaluate": ()}
    cloud = isinstance(store, S3Store)
    for prior in dependencies[stage]:
        restore_stage(store, scratch, root + "/" + prior, identity, prefixes[prior],
                      not cloud or stage != "detect")

    if stage == "prepare":
        from fresh_inputs import prepare_batch

        for row in [*ready["files"], ready["accounts"]]:
            materialize(store, scratch, row["key"], row["sha256"])
        prepare_batch(ready, attempt, scratch, work)
    elif stage == "detect":
        from fresh_inputs import ANALYSIS_ID, detect_batch

        first = date.fromisoformat(ready["history_start"])
        cutoff = date.fromisoformat(ready["cutoff"])
        if cloud:
            from q2_snapshots import main as detect_distributed

            detect_distributed([
                "--input-manifest", f"s3://{BUCKET}/{manifest.relative_to(scratch).as_posix()}",
                "--output-root", f"s3://{BUCKET}", "--analysis-id", ANALYSIS_ID,
                "--first-snapshot-end", (first + timedelta(days=1)).isoformat(),
                "--last-snapshot-end", cutoff.isoformat(),
                "--max-cycle-path-rows", "200000000", "--max-output-cost-usd", "10",
            ])
            quality = f"quality/q2/{suffix}analysis_id={ANALYSIS_ID}/report.json"
            (work / "detector-report.json").write_bytes(store.read(quality).body)
        else:
            detect_batch(manifest, scratch, work, first, cutoff)
    elif stage == "score":
        from fresh_inputs import ANALYSIS_ID
        from score_batch import score_fresh_batch

        if cloud:
            _, index = split_uri(json.loads(detector.read_bytes())["outputs"]["case_index"])
            if index != cases_prefix + f"analysis_id={ANALYSIS_ID}/case_index/":
                raise ValueError("Case index does not identify this batch")
            store.download_case_index(scratch, index)
        bundle = local_bundle if local_bundle is not None else scratch / "bundle"
        if local_bundle is None:
            load_bundle(store, bundle, bundle_uri, bundle_sha256)
        work.rmdir()
        score_fresh_batch(manifest, detector, scratch, bundle, bundle_sha256, release_id, work,
                          date.fromisoformat(ready["batch_start"]))
    elif stage == "evaluate":
        from fresh_release import evaluate_batch
        from pipeline.bq2_release import LocalBQ2Objects

        for name in ("labels", "complete_labels", "annotations"):
            if name in ready:
                ref = ready[name]
                materialize(store, scratch, ref["key"], ref["sha256"])
        evidence_store = S3Evidence(store, scratch / "evidence-cache") if cloud else LocalBQ2Objects(scratch)
        evaluate_batch(ready, scratch, manifest, detector, scores, evaluation, evidence_store)
    else:
        from fresh_release import stage_release

        destination = work / "release"
        release = stage_release(detector, scores, evaluation, destination)
        _, release_key = split_uri(release["uri"])
        if release_key != f"published/bq2/{release_id}/release.json":
            raise ValueError("Release pointer does not identify this batch")
        for file in sorted(destination.iterdir(), key=lambda path: (path.name == "release.json", path.name)):
            store.upload(release_key.removesuffix("release.json") + file.name, file, hash_file(file))
        # Compare against the pointer read at stage start. A concurrent run cannot move it backward.
        store.write(pointer, encoded({**release, "release_id": release_id, "cutoff": ready["cutoff"]}),
                    current.etag if current is not None else None)
        return "published"

    paths = [file for folder in (work, *(scratch / prefix for prefix in prefixes[stage]))
             for file in folder.rglob("*") if file.is_file()]
    persist_stage(store, scratch, stage_dir, paths, identity)
    return "passed"


def run_local(mirror: Path, ready_key: str, bundle: Path, bundle_sha256: str, attempt: str) -> dict[str, str]:
    store = LocalStore(mirror)
    etag = store.read(ready_key).etag
    results: dict[str, str] = {}
    for stage in STAGES:
        with TemporaryDirectory(prefix="fresh-bq2-") as folder:
            results[stage] = run_stage(store, Path(folder), stage, ready_key, etag, attempt, "",
                                       bundle_sha256, bundle, CURRENT)
        if results[stage] == "already-published":
            break
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("stage", "ready-key", "attempt-id", "model-bundle-sha256"):
        parser.add_argument("--" + name, required=True)
    for name in ("ready-etag", "bucket", "bucket-owner", "model-bundle-uri", "release-pointer",
                 "local-mirror", "local-bundle"):
        parser.add_argument("--" + name)
    args, _ = parser.parse_known_args()
    if args.stage == "local" and args.local_mirror and args.local_bundle:
        print(json.dumps(run_local(Path(args.local_mirror), args.ready_key, Path(args.local_bundle),
                                   args.model_bundle_sha256, args.attempt_id), indent=2))
        return
    if args.bucket != BUCKET or args.bucket_owner != ACCOUNT or not args.ready_etag or not args.model_bundle_uri:
        raise ValueError("Require the project bucket, owner, ready ETag and approved model bundle URI")
    import boto3

    with TemporaryDirectory(prefix="fresh-bq2-") as folder:
        status = run_stage(S3Store(boto3.client("s3", region_name=REGION)), Path(folder),
                           args.stage, args.ready_key, args.ready_etag, args.attempt_id,
                           args.model_bundle_uri, args.model_bundle_sha256, None, args.release_pointer)
        print(json.dumps({"stage": args.stage, "attempt": args.attempt_id, "status": status}))


if __name__ == "__main__":
    main()
