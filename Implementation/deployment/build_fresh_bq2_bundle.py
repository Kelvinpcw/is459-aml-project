"""Package the reviewed Glue sources and pinned Glue 5.1 wheels locally."""

import argparse
from hashlib import file_digest
import json
from pathlib import Path
import shutil
from zipfile import ZipFile

from build_bundle import ROOT, archive, digest
from build_fresh_bq2_stack import CODE


GLUE = ROOT / "Implementation/ml_replay/glue"
IMPLEMENTATION = ROOT / "Implementation"
ML_MODULES = (
    "fresh_inputs.py", "fresh_release.py", "score_batch.py", "batch_projection.py",
    "rank_shortlist.py", "archive_algorithms.py", "score_payments.py", "project_facts.py",
)
JOB_MODULES = ("prepare.py", "q2_detect.py", "q2_distributed.py", "q2_bundle_shards.py", "q2_snapshots.py")
PACKAGES = ("pipeline/__init__.py", "pipeline/release.py", "pipeline/bq2_release.py",
            "dashboard/__init__.py", "dashboard/data.py")


def validate_wheels(path: Path) -> None:
    requirements = (GLUE / "glue-requirements.txt").read_text().splitlines()
    with ZipFile(path) as bundle:
        names = bundle.namelist()
        if len(set(names)) != len(names) or any("/" in name or not name.endswith(".whl") for name in names):
            raise ValueError("Expected a flat Glue wheel bundle with one entry per wheel")
        versions: dict[str, str] = {}
        for name in names:
            package, version, *_ = name.split("-")
            if package in versions:
                raise ValueError(f"Multiple wheels for one dependency: {package}")
            versions[package] = version
            if not (name.endswith("-none-any.whl") or "-cp311-cp311-manylinux" in name and "x86_64" in name):
                raise ValueError(f"Wheel does not target Glue 5.1 CPython 3.11 x86-64: {name}")
        for line in requirements:
            package, version = line.split("==")
            if versions.get(package.replace("-", "_")) != version:
                raise ValueError(f"Glue wheel bundle is missing pinned dependency {line}")
        damaged = bundle.testzip()
        if damaged is not None:
            raise ValueError(f"Wheel bundle failed checksum verification: {damaged}")


def build(destination: Path, wheels: Path) -> dict:
    validate_wheels(wheels)
    modules = {
        **{name: (GLUE / name).read_bytes() for name in ML_MODULES},
        **{name: (IMPLEMENTATION / "jobs" / name).read_bytes() for name in JOB_MODULES},
        **{name: (IMPLEMENTATION / name).read_bytes() for name in PACKAGES},
    }
    entry = (GLUE / "fresh_glue.py").read_bytes()
    for name, source in {**modules, "fresh_glue.py": entry}.items():
        compile(source, name, "exec")
    destination.mkdir(parents=True, exist_ok=False)
    (destination / "fresh_glue.py").write_bytes(entry)
    (destination / "fresh-bq2.zip").write_bytes(archive(modules))
    shutil.copyfile(wheels, destination / "runtime.gluewheels.zip")
    artifacts = {}
    for path in sorted(destination.iterdir()):
        with path.open("rb") as artifact:
            artifacts[path.name] = {"sha256": file_digest(artifact, "sha256").hexdigest(), "bytes": path.stat().st_size}
    version = digest(json.dumps(artifacts, sort_keys=True, separators=(",", ":")).encode())
    prefix = CODE.replace("${CodeVersion}", version)
    manifest = {"schema_version": 1, "code_version": version, "prefix": prefix, "artifacts": artifacts}
    (destination / "package.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--destination", required=True, type=Path)
    parser.add_argument("--wheels", required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(build(args.destination, args.wheels), indent=2))
