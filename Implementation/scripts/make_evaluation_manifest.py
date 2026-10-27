"""Trusted handoff for the isolated evaluator; never exposed to Q2 detection."""
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "jobs"))
from evaluate_q2 import canonical_sha, validate_evaluator_manifest


def build(root):
    review = root / "aws/reviews"
    prep = json.loads((review / "preparation-report-dev-20220901-v2.json").read_text())
    detector = json.loads((review / "q2-report-q2-dev-20220901-m00-v1.json").read_text())
    verification = json.loads((review / "q2-cloud-verification-m00-v1.json").read_text())
    replay = json.loads((review / "q2-local-replay-m00-v1.json").read_text())
    if (prep["status"] != "PASSED" or detector["status"] != "PASSED" or verification["status"] != "VERIFIED" or
            not verification["all_bundle_content_matches"] or not verification["case_index_physical_read_validated"]):
        raise ValueError("Require verified complete preparation and frozen cloud Q2 artifacts")
    config = detector["config"]
    prefix = "s3://is459-aml-g2team7-160885259244-us-east-1/"
    prep_suffix = f"dataset_version={config['dataset_version']}/run_id={config['run_id']}"
    q2_suffix = prep_suffix + f"/analysis_id={config['analysis_id']}"
    expected = []
    for inventory in replay["case_inventory"]:
        case = json.loads((root / "data/q2-cloud-m00-v1" / (inventory["case_id"] + ".json")).read_text())
        digest = hashlib.sha256((json.dumps(case, sort_keys=True) + "\n").encode()).hexdigest()
        if digest != inventory["bundle_sha256"]:
            raise ValueError("Saved cloud bundle no longer matches the verified case")
        expected.append({"case_id": inventory["case_id"], "emitted_json_sha256": digest})
    if len(expected) != detector["statistics"]["case_count"]:
        raise ValueError("Frozen case inventory changed")
    manifest = {"schema_version": 1, "stage": "evaluator_inputs",
                **{k: config[k] for k in ("dataset_version", "run_id", "analysis_id")},
                "inputs": {"preparation_report": prefix + f"quality/preparation/{prep_suffix}/report.json",
                           "detector_report": prefix + f"quality/q2/{q2_suffix}/report.json",
                           "annotations": prefix + f"references/annotations/dataset_version={config['dataset_version']}/HI-Medium_Patterns.txt"},
                "preparation_report_sha256": canonical_sha(prep), "detector_report_sha256": canonical_sha(detector),
                "annotations_sha256": prep["source_manifest"]["source_files"]["patterns"]["sha256"],
                "expected_cases": sorted(expected, key=lambda c: c["case_id"])}
    validate_evaluator_manifest(manifest)
    output = root / "aws/manifests/evaluation-input-m00-v1.json"
    output.write_text(json.dumps(manifest, indent=2) + "\n")
    return output


if __name__ == "__main__":
    print(build(Path(__file__).resolve().parents[1]))
