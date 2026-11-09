"""Rebuild the fact and case inputs from the saved October 30 AWS objects."""

import argparse
from hashlib import file_digest
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory


def checksum(path: Path) -> str:
    with path.open("rb") as stream:
        return file_digest(stream, "sha256").hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("experiments", type=Path)
    parser.add_argument("attempt", type=Path)
    args = parser.parse_args()
    replay = args.experiments / "trace-q2-full-replay"
    sys.path.insert(0, str(replay))
    from prepare import PREP, RELEASE, clean_facts, inventory, stage_cases

    if (RELEASE["release_id"], RELEASE["run_id"], PREP["accepted_rows"]) != (
        "full-20261030-v1", "full-20261030-v1", 31_898_238
    ):
        raise ValueError("The local mirror is not the required full October 30 release")
    if (RELEASE["q2"]["case_count"], len(RELEASE["q2"]["snapshots"])) != (2_251_155, 28):
        raise ValueError("The saved Q2 case archive has an unexpected population")

    checksums: dict[str, str] = {}
    with TemporaryDirectory(dir=args.attempt, prefix="source-check-") as directory:
        rebuilt = Path(directory)
        checks = inventory()
        accounts, dates = clean_facts(rebuilt, checks)
        stage_cases(rebuilt, accounts, checks)
        subprocess.run([str(replay / "replay"), str(rebuilt), str(len(accounts))], check=True)
        for name in ("facts.bin", "days.u8", "accounts.json", "cases.bin", "case-ids.s64",
                     "evidence.u32", "scored.bin", "flags.u16", "motifs.u8", "max-degree.u32"):
            observed = checksum(rebuilt / name)
            if observed != checksum(replay / "work" / name):
                raise ValueError(f"Rebuilt {name} differs from the staged replay input")
            checksums[name] = observed
            print(f"Exact reconstructed bytes: {name} sha256={observed}", flush=True)

    summary = {"release_id": RELEASE["release_id"], "dataset_version": RELEASE["dataset_version"],
               "facts": PREP["accepted_rows"], "daily": dates, "accounts": len(accounts),
               "snapshots": len(RELEASE["q2"]["snapshots"]), "case_rows": RELEASE["q2"]["case_count"],
               "evidence_memberships": sum(row["case_evidence_rows_including_case_overlap"]
                                           for row in RELEASE["q2"]["snapshots"]),
               "sha256": checksums}
    with (args.attempt / "source-check.json").open("x") as output:
        json.dump(summary, output, indent=2)
        output.write("\n")
    print("Verified the complete local October 30 fact and case inputs", flush=True)


if __name__ == "__main__":
    main()
