"""AWS Glue 5.1 batch preparation. No detection or label-derived risk scoring."""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from urllib.parse import urlparse

TRANSACTION_COLUMNS = [
    "source_id", "source_record_ordinal", "timestamp_raw", "from_bank_raw",
    "sender_account", "to_bank_raw", "receiver_account", "amount_received_raw",
    "receiving_currency", "amount_paid_raw", "payment_currency", "payment_format",
    "is_laundering_raw",
]
ACCOUNT_COLUMNS = ["bank_name", "bank_id_raw", "account_number", "entity_id", "entity_name"]
AMOUNT_PRECISION = 38
AMOUNT_SCALE = 8
# Reject excess scale before casting: a successful decimal cast can silently round.
AMOUNT_PATTERN = rf"^[+-]?[0-9]+(?:\.[0-9]{{1,{AMOUNT_SCALE}}})?$"


def amount_is_valid(raw_column, typed_column):
    from pyspark.sql import functions as F
    return F.coalesce(F.col(raw_column).rlike(AMOUNT_PATTERN) &
                      F.col(typed_column).isNotNull(), F.lit(False))


def with_typed_amounts(frame):
    from pyspark.sql import functions as F, types as T
    return (frame.withColumn("amount_paid", F.col("amount_paid_raw").cast(T.DecimalType(AMOUNT_PRECISION, AMOUNT_SCALE)))
            .withColumn("amount_received", F.col("amount_received_raw").cast(T.DecimalType(AMOUNT_PRECISION, AMOUNT_SCALE))))


def main(argv=None):
    import boto3
    from pyspark import StorageLevel
    from pyspark.sql import SparkSession, functions as F, types as T

    parser = argparse.ArgumentParser()
    parser.add_argument("--input-root", required=True)
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--max-quarantine-rows", type=int, default=0)
    args, _ = parser.parse_known_args(argv)
    if args.max_quarantine_rows < 0:
        raise ValueError("max-quarantine-rows must be nonnegative")
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", args.run_id):
        raise ValueError("run-id must contain 1-100 letters, digits, underscores or hyphens")
    input_root, output_root = args.input_root.rstrip("/"), args.output_root.rstrip("/")
    source = urlparse(input_root + "/manifest.json")
    destination = urlparse(output_root)
    if source.scheme != "s3" or destination.scheme != "s3":
        raise ValueError("Glue preparation requires explicit s3:// input and output roots")
    s3 = boto3.client("s3")
    if "IfNoneMatch" not in s3.meta.service_model.operation_model("PutObject").input_shape.members:
        raise RuntimeError("Use Glue 5.1 or a newer compatible SDK: conditional S3 report writes are required")
    manifest = json.loads(s3.get_object(Bucket=source.netloc, Key=source.path.lstrip("/"))["Body"].read())
    if manifest.get("schema_version") != 1 or manifest.get("ingestion_columns") != TRANSACTION_COLUMNS:
        raise ValueError("Unsupported ingestion manifest/schema")
    version = manifest["dataset_version"]
    if not re.fullmatch(r"ibm-hi-medium-[0-9a-f]{16}", version):
        raise ValueError("Invalid dataset_version in manifest")
    suffix = f"dataset_version={version}/run_id={args.run_id}"
    report_key = destination.path.strip("/")
    report_key = "/".join(filter(None, [report_key, "quality/preparation", suffix, "report.json"]))
    # Refuse to reuse any output namespace, including a failed attempt.
    for zone in ("curated", "references/labels", "quarantine/preparation", "quality/preparation"):
        prefix = "/".join(filter(None, [destination.path.strip("/"), zone, suffix])) + "/"
        if s3.list_objects_v2(Bucket=destination.netloc, Prefix=prefix, MaxKeys=1).get("KeyCount", 0):
            raise ValueError("run-id already has output. Choose a new run-id; never overwrite a published run")
    report = {"schema_version": 2, "stage": "preparation", "status": "FAILED",
              "dataset_version": version, "run_id": args.run_id, "input_root": input_root,
              "source_manifest": manifest, "started_at_utc": datetime.now(timezone.utc).isoformat(),
              "amount_policy": {"precision": AMOUNT_PRECISION, "scale": AMOUNT_SCALE,
                                "excess_scale": "quarantine_without_rounding"},
              "max_quarantine_rows": args.max_quarantine_rows}
    spark = (SparkSession.builder.appName("is459-aml-preparation")
             .config("spark.sql.session.timeZone", "UTC")
             .config("spark.sql.ansi.enabled", "false")
             .config("spark.sql.legacy.timeParserPolicy", "CORRECTED")
             .config("spark.sql.shuffle.partitions", "16").getOrCreate())
    # UTC is only an internal fixed parsing convention. Do not claim source timestamps are UTC.

    def schema(names):
        return T.StructType([T.StructField(name, T.StringType(), True) for name in names])

    def read_csv(path, names):
        return (spark.read.schema(schema(names)).option("header", True)
                .option("mode", "FAILFAST").option("multiLine", True).csv(path))

    def normalise_bank(column):
        raw = F.trim(F.col(column))
        stripped = F.regexp_replace(raw, r"^0+", "")
        return F.when(raw.rlike(r"^[0-9]+$"), F.when(stripped == "", F.lit("0")).otherwise(stripped))

    def reason(condition, name):
        return F.when(~F.coalesce(condition, F.lit(False)), F.lit(name))

    def write_parquet(frame, zone, name, partitions=()):
        path = f"{output_root}/{zone}/{suffix}/{name}/"
        writer = frame.write.mode("errorifexists").option("compression", "snappy")
        if partitions:
            writer = writer.partitionBy(*partitions)
        writer.parquet(path)
        return path

    try:
        raw = read_csv(input_root + "/transactions.csv.gz", TRANSACTION_COLUMNS).persist(StorageLevel.DISK_ONLY)
        raw_count = raw.count()
        if raw_count != manifest["counts"]["selected_records"]:
            raise ValueError("Transaction row count differs from ingestion manifest")
        if raw.groupBy("source_id").count().filter("count > 1").limit(1).count():
            raise ValueError("Duplicate source IDs in ingestion input")
        expected_hash = manifest["source_files"]["transactions"]["sha256"]
        if not re.fullmatch(r"[0-9a-f]{64}", expected_hash):
            raise ValueError("Invalid source checksum")
        typed = with_typed_amounts(raw.withColumn("sender_bank", normalise_bank("from_bank_raw"))
                 .withColumn("receiver_bank", normalise_bank("to_bank_raw"))
                 .withColumn("sender_account", F.trim("sender_account"))
                 .withColumn("receiver_account", F.trim("receiver_account"))
                 .withColumn("event_time", F.to_timestamp("timestamp_raw", "yyyy/MM/dd HH:mm"))
                 .withColumn("event_date", F.to_date("event_time")))
        errors = [
            reason(F.col("source_record_ordinal").rlike(r"^[1-9][0-9]*$") &
                   F.col("source_record_ordinal").cast("long").isNotNull() &
                   (F.col("source_id") == F.concat(F.lit(expected_hash + ":"), F.col("source_record_ordinal"))), "invalid_source_id"),
            reason(F.col("event_time").isNotNull(), "invalid_timestamp"),
            reason(F.col("sender_bank").isNotNull() & F.col("receiver_bank").isNotNull(), "invalid_bank"),
            reason((F.length("sender_account") > 0) & (F.length("receiver_account") > 0), "missing_account"),
            reason(amount_is_valid("amount_paid_raw", "amount_paid"), "invalid_paid_amount"),
            reason(amount_is_valid("amount_received_raw", "amount_received"), "invalid_received_amount"),
            reason((F.length(F.trim("payment_currency")) > 0) &
                   (F.length(F.trim("receiving_currency")) > 0), "missing_currency"),
            reason(F.length(F.trim("payment_format")) > 0, "missing_payment_format"),
            reason(F.col("is_laundering_raw").isin("0", "1"), "invalid_label"),
        ]
        checked = typed.withColumn("quarantine_reason", F.concat_ws(";", *errors)).persist(StorageLevel.DISK_ONLY)
        accepted = checked.filter(F.col("quarantine_reason") == "")
        rejected = checked.filter(F.col("quarantine_reason") != "")
        accepted_count, rejected_count = accepted.count(), rejected.count()
        if accepted_count + rejected_count != raw_count:
            raise ValueError("Accepted/quarantined transaction counts do not reconcile")
        report.update({"input_rows": raw_count, "accepted_rows": accepted_count,
                       "quarantined_rows": rejected_count,
                       "quarantine_by_reason": [r.asDict() for r in rejected.groupBy("quarantine_reason").count().collect()]})
        if rejected_count > args.max_quarantine_rows:
            raise ValueError("Quarantine exceeds the reviewed limit; inspect report before accepting a reduced population")
        if not accepted_count:
            raise ValueError("No valid transactions remain after validation")
        scope = manifest["development_scope"]
        if accepted.filter((F.col("event_date") < F.lit(scope["start_inclusive"]).cast("date")) |
                           (F.col("event_date") >= F.lit(scope["end_exclusive"]).cast("date"))).limit(1).count():
            raise ValueError("Transactions fall outside the manifest's declared date scope")

        accounts_raw = read_csv(input_root + "/accounts.csv.gz", ACCOUNT_COLUMNS)
        accounts_checked = (accounts_raw.withColumn("bank_id", normalise_bank("bank_id_raw"))
                            .withColumn("account_number", F.trim("account_number"))
                            .withColumn("valid", F.col("bank_id").isNotNull() &
                                        (F.length("account_number") > 0) &
                                        (F.length(F.trim("entity_id")) > 0)))
        accounts = accounts_checked.filter(F.coalesce(F.col("valid"), F.lit(False))).drop("valid")
        invalid_accounts = accounts_checked.filter(~F.coalesce(F.col("valid"), F.lit(False)))
        accounts_count, invalid_accounts_count = accounts.count(), invalid_accounts.count()
        if accounts.groupBy("bank_id", "account_number").count().filter("count > 1").limit(1).count():
            raise ValueError("Normalised bank/account mappings are not unique; joining would multiply transactions")
        sender_map = accounts.select(F.col("bank_id").alias("sender_bank"),
                                     F.col("account_number").alias("sender_account"),
                                     F.col("entity_id").alias("sender_entity_id"),
                                     F.col("entity_name").alias("sender_entity_name"))
        receiver_map = accounts.select(F.col("bank_id").alias("receiver_bank"),
                                       F.col("account_number").alias("receiver_account"),
                                       F.col("entity_id").alias("receiver_entity_id"),
                                       F.col("entity_name").alias("receiver_entity_name"))
        enriched = (accepted.join(sender_map, ["sender_bank", "sender_account"], "left")
                    .join(receiver_map, ["receiver_bank", "receiver_account"], "left")
                    .withColumn("sender_entity_unknown", F.col("sender_entity_id").isNull())
                    .withColumn("receiver_entity_unknown", F.col("receiver_entity_id").isNull())
                    .withColumn("dataset_version", F.lit(version))
                    .withColumn("run_id", F.lit(args.run_id)).persist(StorageLevel.DISK_ONLY))
        if enriched.count() != accepted_count:
            raise ValueError("Account joins changed the transaction count")
        coverage = enriched.agg(
            F.sum(F.col("sender_entity_unknown").cast("long")).alias("unmatched_sender_rows"),
            F.sum(F.col("receiver_entity_unknown").cast("long")).alias("unmatched_receiver_rows"),
        ).first().asDict()
        fact_columns = ["source_id", "source_record_ordinal", "dataset_version", "run_id",
                        "event_time", "event_date", "timestamp_raw", "from_bank_raw", "to_bank_raw",
                        "sender_bank", "sender_account", "receiver_bank", "receiver_account",
                        "amount_paid_raw", "amount_paid", "payment_currency",
                        "amount_received_raw", "amount_received", "receiving_currency",
                        "payment_format", "sender_entity_id", "sender_entity_name",
                        "receiver_entity_id", "receiver_entity_name", "sender_entity_unknown",
                        "receiver_entity_unknown"]
        facts = enriched.select(*fact_columns).withColumn("source_record_ordinal", F.col("source_record_ordinal").cast("long"))
        labels = enriched.select("source_id", "dataset_version", "run_id", "event_date",
                                 F.col("is_laundering_raw").cast("int").alias("is_laundering"))
        outputs = {
            "transactions": write_parquet(facts, "curated", "transactions", ("event_date",)),
            "accounts": write_parquet(accounts, "curated", "accounts"),
            "labels": write_parquet(labels, "references/labels", "transactions", ("event_date",)),
        }
        if rejected_count:
            outputs["quarantined_transactions"] = write_parquet(rejected, "quarantine/preparation", "transactions")
        if invalid_accounts_count:
            outputs["quarantined_accounts"] = write_parquet(invalid_accounts, "quarantine/preparation", "accounts")
        source_format_counts = [row.asDict() for row in enriched.groupBy("payment_format").agg(
            F.count("*").alias("transactions"),
            F.sum(F.col("is_laundering_raw").cast("long")).alias("labelled_laundering")
        ).collect()]
        quarantined_format_counts = [row.asDict() for row in rejected.groupBy("payment_format").agg(
            F.count("*").alias("transactions"),
            F.sum(F.when(F.col("is_laundering_raw") == "1", 1).otherwise(0)).alias("labelled_laundering")
        ).collect()]
        for field in ("transactions", "labelled_laundering"):
            accepted_by_format = {r["payment_format"]: r[field] for r in source_format_counts}
            rejected_by_format = {r["payment_format"]: r[field] for r in quarantined_format_counts}
            reference = manifest["q1_source_reference_by_format"]
            if set(accepted_by_format) | set(rejected_by_format) != set(reference):
                raise ValueError("Payment-format population differs from ingestion reference")
            for payment_format, counts in reference.items():
                if accepted_by_format.get(payment_format, 0) + rejected_by_format.get(payment_format, 0) != counts[field]:
                    raise ValueError("Accepted plus quarantined format/label counts differ from ingestion reference")
        report.update({"status": "PASSED", "input_rows": raw_count, "accepted_rows": accepted_count,
                       "quarantined_rows": rejected_count, "valid_account_mappings": accounts_count,
                       "invalid_account_mappings": invalid_accounts_count, "join_coverage": coverage,
                       "fact_columns": facts.columns, "label_separation_passed": not any("launder" in c.lower() for c in facts.columns),
                       "accepted_by_format": source_format_counts,
                       "quarantined_by_format": quarantined_format_counts,
                       "source_reference_reconciliation_passed": True, "outputs": outputs,
                       "timestamp_policy": "dataset-local event time; UTC used only as a fixed internal parsing convention"})
        print(json.dumps({key: value for key, value in report.items() if key != "source_manifest"}, default=str))
    except Exception as error:
        report["error_type"] = type(error).__name__
        report["error"] = str(error)[:2000]
        raise
    finally:
        report["finished_at_utc"] = datetime.now(timezone.utc).isoformat()
        s3.put_object(Bucket=destination.netloc, Key=report_key,
                      Body=(json.dumps(report, indent=2, default=str) + "\n").encode(),
                      ContentType="application/json", IfNoneMatch="*")
        spark.stop()


if __name__ == "__main__":
    main(sys.argv[1:])
