"""Q1 additive daily counts and currency-preserving amounts. Prepared, not deployed."""
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from urllib.parse import urlparse


def validate_preparation_contract(prep):
    if prep.get("status") != "PASSED" or not prep.get("label_separation_passed"):
        raise ValueError("Q1 requires a passed preparation report and label-separated facts")
    if (prep.get("schema_version") != 2 or
            prep.get("amount_policy", {}).get("precision") != 38 or
            prep.get("amount_policy", {}).get("scale") != 8 or
            not prep.get("source_reference_reconciliation_passed")):
        raise ValueError("Q1 requires reviewed precision-safe preparation v2; the v1 population excluded valid Bitcoin amounts")


DAILY_GRAIN = ["dataset_version", "run_id", "event_date", "sender_bank", "receiver_bank",
               "payment_format", "payment_currency", "receiving_currency"]


def aggregate_daily(facts, labels, prep):
    """Use the same validated aggregation in Glue and local Spark regressions."""
    from pyspark import StorageLevel
    from pyspark.sql import functions as F
    from pyspark.sql.types import DecimalType

    validate_preparation_contract(prep)
    version, run_id = prep["dataset_version"], prep["run_id"]
    if any("launder" in column.lower() for column in facts.columns):
        raise ValueError("Label-free facts contain a laundering column")
    keys = ["source_id", "dataset_version", "run_id", "event_date"]
    if labels.filter(~F.coalesce(F.col("is_laundering").isin(0, 1), F.lit(False))).limit(1).count():
        raise ValueError("Invalid historical label")
    expected = prep["accepted_rows"]
    if facts.count() != expected or labels.count() != expected:
        raise ValueError("Q1 inputs differ from the accepted preparation population")
    for column in ("amount_paid", "amount_received"):
        if facts.schema[column].dataType != DecimalType(38, 8):
            raise ValueError("Q1 requires exact decimal(38,8) amounts")
        if facts.filter(F.col(column).isNull()).limit(1).count():
            raise ValueError("Q1 amount is null")
    for frame in (facts, labels):
        invalid_identity = (F.col("dataset_version").isNull() | F.col("run_id").isNull() |
                            (F.col("dataset_version") != version) | (F.col("run_id") != run_id))
        for key in keys:
            invalid_identity = invalid_identity | F.col(key).isNull()
        if frame.filter(invalid_identity).limit(1).count():
            raise ValueError("Q1 inputs mix dataset versions/runs or contain null transaction keys")
        if frame.groupBy(*keys).count().filter("count > 1").limit(1).count():
            raise ValueError("Q1 source transactions are not unique")
    joined = facts.join(labels, keys, "inner").persist(StorageLevel.DISK_ONLY)
    if joined.count() != expected:
        raise ValueError("Q1 fact/label join lost or multiplied transactions")
    grain = DAILY_GRAIN
    daily = joined.groupBy(*grain).agg(
        F.count("*").alias("transaction_count"),
        F.sum("is_laundering").cast("long").alias("laundering_count"),
        F.sum("amount_paid").alias("amount_paid_total"),
        F.sum("amount_received").alias("amount_received_total"),
    ).persist(StorageLevel.DISK_ONLY)
    if daily.filter(F.col("amount_paid_total").isNull() | F.col("amount_received_total").isNull()).limit(1).count():
        raise ValueError("A decimal amount total overflowed or is invalid")
    totals = daily.agg(F.sum("transaction_count").alias("transactions"),
                       F.sum("laundering_count").alias("labelled_laundering")).first().asDict()
    if totals["transactions"] != expected:
        raise ValueError("Daily risk counts do not reconcile")
    expected_l = joined.agg(F.sum("is_laundering").alias("laundering")).first()["laundering"]
    if totals["labelled_laundering"] != expected_l:
        raise ValueError("Daily risk laundering counts do not reconcile")
    actual_formats = {row["payment_format"]: (row["transactions"], row["labelled_laundering"])
                      for row in joined.groupBy("payment_format").agg(
                          F.count("*").alias("transactions"),
                          F.sum("is_laundering").alias("labelled_laundering")).collect()}
    expected_formats = {row["payment_format"]: (row["transactions"], row["labelled_laundering"])
                        for row in prep["accepted_by_format"]}
    if actual_formats != expected_formats:
        raise ValueError("Q1 format/label population differs from preparation reference")
    joined.unpersist()
    return daily, totals, grain


def main():
    import boto3
    from pyspark.sql import SparkSession

    parser = argparse.ArgumentParser()
    parser.add_argument("--preparation-report", required=True)
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--analysis-id", required=True)
    parser.add_argument("--attempt-id", default="")
    args, _ = parser.parse_known_args()
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", args.analysis_id):
        raise ValueError("analysis-id must contain 1-100 letters, digits, underscores or hyphens")
    location = urlparse(args.preparation_report)
    output = urlparse(args.output_root)
    if location.scheme != "s3" or output.scheme != "s3":
        raise ValueError("Explicit S3 report and output paths are required")
    s3 = boto3.client("s3")
    if "IfNoneMatch" not in s3.meta.service_model.operation_model("PutObject").input_shape.members:
        raise RuntimeError("Use Glue 5.1 or a newer compatible SDK: conditional S3 report writes are required")
    prep = json.loads(s3.get_object(Bucket=location.netloc, Key=location.path.lstrip("/"))["Body"].read())
    validate_preparation_contract(prep)
    version, run_id = prep["dataset_version"], prep["run_id"]
    suffix = f"dataset_version={version}/run_id={run_id}/analysis_id={args.analysis_id}"
    if args.attempt_id:
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,100}",args.attempt_id):raise ValueError("Invalid attempt ID")
        suffix+="/attempt="+args.attempt_id
    root = args.output_root.rstrip("/")
    for zone in ("gold/risk", "quality/q1"):
        prefix = "/".join(filter(None, [output.path.strip("/"), zone, suffix])) + "/"
        if s3.list_objects_v2(Bucket=output.netloc, Prefix=prefix, MaxKeys=1).get("KeyCount", 0):
            raise ValueError("Q1 run namespace already exists; do not overwrite a published or partial run")
    report = {"schema_version": 1, "stage": "q1", "status": "FAILED",
              "dataset_version": version, "run_id": run_id,
              "analysis_id": args.analysis_id,
              "preparation_report": args.preparation_report}
    spark = (SparkSession.builder.appName("is459-aml-q1")
             .config("spark.sql.session.timeZone", "UTC")
             .config("spark.sql.ansi.enabled", "false")
             .config("spark.sql.shuffle.partitions", "16").getOrCreate())
    try:
        facts = spark.read.parquet(prep["outputs"]["transactions"])
        labels = spark.read.parquet(prep["outputs"]["labels"])
        daily, totals, grain = aggregate_daily(facts, labels, prep)
        path = f"{root}/gold/risk/{suffix}/daily_counts/"
        daily.write.mode("errorifexists").partitionBy("event_date").parquet(path)
        report.update({"status": "PASSED", "totals": totals, "grain": grain,
                       "outputs": {"daily_counts": path},
                       "rate_policy": "Filter first, sum counts across dates, then divide. Never average daily rates.",
                       "currency_policy": "Keep both currency dimensions. Paid and received totals retain their own units."})
    except Exception as error:
        report.update({"error_type": type(error).__name__, "error": str(error)[:2000]})
        raise
    finally:
        report["finished_at_utc"] = datetime.now(timezone.utc).isoformat()
        key = "/".join(filter(None, [output.path.strip("/"), "quality/q1", suffix, "report.json"]))
        try:
            s3.put_object(Bucket=output.netloc, Key=key, Body=(json.dumps(report, indent=2) + "\n").encode(),
                          ContentType="application/json", IfNoneMatch="*")
        finally:
            spark.stop()


if __name__ == "__main__":
    main()
