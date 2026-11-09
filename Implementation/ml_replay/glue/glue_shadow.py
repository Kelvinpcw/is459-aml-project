"""Glue adapter for an isolated replay of the verified October 30 input projection."""

from contextlib import closing
from hashlib import sha256
import json
from pathlib import Path
import re
import sys
from tempfile import TemporaryDirectory

from project_facts import rebuild_from_s3
from rank_shortlist import main as rank
from score_payments import Model, ROWS, extract_and_score
from sklearn import __version__ as sklearn_version


MODELS = ("boosted_context", "history_boost", "hi_small")
REPLAY_FILES = ("facts.bin", "cases.bin", "case-ids.s64", "days.u8", "scored.bin", "evidence.u32")
PROJECTION_FILES = {f"replay/{name}" for name in REPLAY_FILES} | {
    "fact-inventory.json", "aux/formats.u8", "aux/banks.u32", "aux/input.json", "source-check.json", "frozen-policy.json"
}
PACKAGE_FILES = PROJECTION_FILES | {f"models/{name}.joblib" for name in MODELS} | {
    f"native/{name}" for name in MODELS
} | {"models/case-shape.joblib", "models/evidence-progress.joblib", "runtime-models.json"}
OUTPUT_FILES = ("ranked_cases.parquet", "payment_alerts.parquet", "model-scores.json", "manifest.json")
HEX = re.compile(r"[0-9a-f]{64}")
ATTEMPT = re.compile(r"[a-z0-9][a-z0-9-]{7,63}")


def read_input_manifest(s3, bucket: str, owner: str, key: str, expected: str) -> dict[str, str]:
    if not key.startswith("ml-shadow/inputs/") or not key.endswith("/input-manifest-direct-facts.json") or ".." in key.split("/"):
        raise ValueError("The job requires an isolated ML input manifest")
    response = s3.get_object(Bucket=bucket, Key=key, ExpectedBucketOwner=owner)
    with closing(response["Body"]) as body:
        raw = body.read(100_000)
    if sha256(raw).hexdigest() != expected:
        raise ValueError("ML input manifest did not match its approved SHA-256")
    document = json.loads(raw)
    files = document["files"]
    if document["release_id"] != "full-20261030-v1" or set(files) != PACKAGE_FILES:
        raise ValueError("Unexpected release or file list in the shadow job manifest")
    if any(not isinstance(value, str) or not HEX.fullmatch(value) for value in files.values()):
        raise ValueError("Each allowed input must have a SHA-256 digest")
    return files


def download(s3, bucket: str, owner: str, prefix: str, name: str, expected: str, root: Path) -> None:
    local = root / name
    local.parent.mkdir(parents=True, exist_ok=True)
    response = s3.get_object(Bucket=bucket, Key=prefix + name, ExpectedBucketOwner=owner)
    digest = sha256()
    with closing(response["Body"]) as body, local.open("xb") as output:
        for chunk in body.iter_chunks(chunk_size=8 * 1024 * 1024):
            digest.update(chunk)
            output.write(chunk)
    if digest.hexdigest() != expected:
        raise ValueError(f"Downloaded input differs from its approved hash: {name}")


def verify_projection(root: Path, hashes: dict[str, str]) -> int:
    source = json.loads((root / "source-check.json").read_text())
    if (source["release_id"], source["facts"], source["snapshots"], source["case_rows"]) != (
        "full-20261030-v1", ROWS, 28, 2_251_155
    ):
        raise ValueError("The projection does not contain the complete October 30 release")
    for name in REPLAY_FILES:
        if source["sha256"][name] != hashes[f"replay/{name}"]:
            raise ValueError(f"Input projection is not the verified release copy: {name}")
    accounts = source["accounts"]
    if type(accounts) is not int or accounts <= 0:
        raise ValueError("Invalid account count in the verified projection")
    return accounts


def execute(root: Path, output: Path, hashes: dict[str, str]) -> None:
    accounts = verify_projection(root, hashes)
    policy = root / "frozen-policy.json"
    runtime = json.loads((root / "runtime-models.json").read_text())
    if runtime["scikit_learn"] != sklearn_version or set(runtime["models"]) != set(MODELS):
        raise ValueError("The supplied runtime does not match the approved payment model versions")
    score_dir = root / "scores"
    score_dir.mkdir(mode=0o700)
    scored = {}
    for name in MODELS:
        entry = runtime["models"][name]
        artifact = root / "models" / f"{name}.joblib"
        if entry["model_sha256"] != hashes[f"models/{name}.joblib"]:
            raise ValueError(f"Unapproved model version: {name}")
        extractor = root / "native" / name
        extractor.chmod(0o700)
        model = Model(name, extractor, artifact, entry["model_sha256"], entry["feature_source_sha256"],
                      entry["score_sha256"], tuple(entry["features"]))
        with TemporaryDirectory(dir=root, prefix=name + "-") as folder:
            scored[name] = extract_and_score(model, extractor, root / "replay", root / "aux", Path(folder),
                                             score_dir / f"{name}.f32", str(accounts))
    frozen = json.loads(policy.read_text())
    pinned_scores = {"boosted_context": "graph_scores", "history_boost": "history_scores",
                     "hi_small": "transfer_scores"}
    for name, field in pinned_scores.items():
        if frozen["artifact_hashes"][field] != scored[name]["reference_score_sha256"]:
            raise ValueError(f"The expected score provenance differs for {name}")
        frozen["artifact_hashes"][field] = scored[name]["score_sha256"]
    executed_policy = root / "executed-policy.json"
    executed_policy.write_text(json.dumps(frozen, indent=2) + "\n")
    rank([
        "--replay", str(root / "replay"), "--input-check", str(root / "source-check.json"),
        "--formats", str(root / "aux"), "--graph-scores", str(score_dir / "boosted_context.f32"),
        "--history-scores", str(score_dir / "history_boost.f32"), "--transfer-scores", str(score_dir / "hi_small.f32"),
        "--case-model", str(root / "models/case-shape.joblib"),
        "--evidence-model", str(root / "models/evidence-progress.joblib"),
        "--policy", str(executed_policy), "--destination", str(output),
    ])
    (output / "model-scores.json").write_text(json.dumps({"frozen_policy_sha256": hashes["frozen-policy.json"],
                                                            "models": scored}, indent=2) + "\n")


def main() -> None:
    from awsglue.utils import getResolvedOptions
    import boto3

    options = getResolvedOptions(sys.argv, ["bucket", "bucket_owner", "input_key", "input_sha256", "attempt"])
    bucket, owner, attempt = (options[name] for name in ("bucket", "bucket_owner", "attempt"))
    if not ATTEMPT.fullmatch(attempt) or not re.fullmatch(r"[0-9]{12}", owner):
        raise ValueError("Require an explicit account and a unique shadow attempt")
    s3 = boto3.client("s3", region_name="us-east-1")
    key = options["input_key"]
    hashes = read_input_manifest(s3, bucket, owner, key, options["input_sha256"])
    prefix = key.removesuffix("input-manifest-direct-facts.json")
    with TemporaryDirectory(prefix="q2-glue-shadow-") as folder:
        root = Path(folder)
        for name in sorted(hashes.keys() - {"replay/facts.bin"}):
            download(s3, bucket, owner, prefix, name, hashes[name], root)
        accounts = rebuild_from_s3(s3, bucket, owner, root / "fact-inventory.json",
                                   root / "replay/facts.bin", root / "replay/days.u8", hashes["replay/facts.bin"])
        if accounts != verify_projection(root, hashes):
            raise ValueError("The archived facts have a different account count")
        output = root / "output"
        execute(root, output, hashes)
        for name in OUTPUT_FILES:
            path = output / name
            with path.open("rb") as body:
                s3.put_object(Bucket=bucket, Key=f"ml-shadow/outputs/{attempt}/{name}", Body=body,
                              IfNoneMatch="*", ExpectedBucketOwner=owner, ServerSideEncryption="AES256")


if __name__ == "__main__":
    main()
