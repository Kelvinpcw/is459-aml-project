"""Shared S3 paths and local reads for published BQ2 batches."""

from pathlib import Path
from typing import BinaryIO

from pipeline.release import BUCKET, safe_id, split_uri

BQ2_PREFIX = "published/bq2/"
BQ2_CURRENT_URI = f"s3://{BUCKET}/{BQ2_PREFIX}current.json"
TABLES = {"ranked_cases": "case_snapshots", "payment_alerts": "payment_alerts", "evidence_index": "case_snapshots"}


def release_uri(release_id: str) -> str:
    return f"s3://{BUCKET}/{BQ2_PREFIX}{safe_id(release_id)}/release.json"


class LocalBQ2Objects:
    """Read a private filesystem mirror through the same API TRACE uses for S3."""

    def __init__(self, mirror: Path):
        self.mirror = mirror.resolve()

    def get_object(self, Bucket: str, Key: str) -> dict[str, BinaryIO]:
        _, key = split_uri(f"s3://{Bucket}/{Key}")
        path = (self.mirror / key).resolve()
        if not path.is_relative_to(self.mirror):
            raise ValueError("Object is outside the local BQ2 mirror")
        return {"Body": path.open("rb")}
