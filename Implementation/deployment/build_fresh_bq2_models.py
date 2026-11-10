"""Repackage approved fitted models with verified target-platform extractors."""

import argparse
import json
from pathlib import Path
import struct

from build_bundle import digest


PAYMENT_MODELS = ("boosted_context", "history_boost", "hi_small")
CASE_MODELS = {"case-shape": "case_shape", "evidence-progress": "evidence_progress"}
EXTRACTORS = ("replay", *PAYMENT_MODELS)
MODEL_ASSETS = {
    *(f"models/{name}.joblib" for name in (*PAYMENT_MODELS, *CASE_MODELS)),
    "category-codes.json", "runtime-models.json", "frozen-policy.json",
}


def check_native(body: bytes, target: str, name: str) -> None:
    if target == "glue":
        compatible = (body.startswith(b"\x7fELF\x02\x01\x01") and len(body) >= 64
                      and struct.unpack_from("<HH", body, 16) in ((2, 62), (3, 62)))
    else:
        cpu = {"mac-arm64": 0x0100000c, "mac-x86_64": 0x01000007}[target]
        compatible = (body.startswith(b"\xcf\xfa\xed\xfe") and len(body) >= 32
                      and struct.unpack_from("<I", body, 4)[0] == cpu
                      and struct.unpack_from("<I", body, 12)[0] == 2)
    if not compatible:
        raise ValueError(f"{name} is not an executable for {target}")


def build(approved: Path, approved_sha256: str, native: Path, destination: Path, target: str) -> str:
    source_manifest = (approved / "bundle.json").read_bytes()
    if digest(source_manifest) != approved_sha256:
        raise ValueError("Approved model bundle manifest hash changed")
    expected = json.loads(source_manifest)["files"]
    native_keys = {f"native/{name}" for name in EXTRACTORS}
    if set(expected) != MODEL_ASSETS | native_keys:
        raise ValueError("Approved manifest must identify five models, their metadata and four extractors")
    assets = {name: (approved / name).read_bytes() for name in MODEL_ASSETS}
    for name, body in assets.items():
        if digest(body) != expected[name]:
            raise ValueError(f"Approved model asset differs from manifest: {name}")
    runtime = json.loads(assets["runtime-models.json"])["models"]
    if set(runtime) != set(PAYMENT_MODELS):
        raise ValueError("Payment runtime has an unexpected estimator set")
    policy = json.loads(assets["frozen-policy.json"])["artifact_hashes"]
    for name in PAYMENT_MODELS:
        if expected[f"models/{name}.joblib"] != runtime[name]["model_sha256"]:
            raise ValueError(f"Payment model hash differs from runtime: {name}")
    for name, policy_key in CASE_MODELS.items():
        if expected[f"models/{name}.joblib"] != policy[policy_key]:
            raise ValueError(f"Case model hash differs from frozen policy: {name}")
    for name in EXTRACTORS:
        body = (native / name).read_bytes()
        check_native(body, target, name)
        assets[f"native/{name}"] = body
    destination.mkdir(parents=True, exist_ok=False)
    for name, body in sorted(assets.items()):
        output = destination / name
        output.parent.mkdir(exist_ok=True)
        output.write_bytes(body)
        if name in native_keys:
            output.chmod(0o700)
    manifest = {"files": {name: digest(body) for name, body in sorted(assets.items())}}
    raw = (json.dumps(manifest, indent=2) + "\n").encode()
    (destination / "bundle.json").write_bytes(raw)
    return digest(raw)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for field in ("approved", "native", "destination"):
        parser.add_argument("--" + field, required=True, type=Path)
    parser.add_argument("--approved-sha256", required=True)
    parser.add_argument("--target", choices=("glue", "mac-arm64", "mac-x86_64"), required=True)
    args = parser.parse_args()
    print(build(args.approved, args.approved_sha256, args.native, args.destination, args.target))
