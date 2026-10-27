"""Business-level checks of the production Q1 transformations and query template."""
import sys
import tempfile
import unittest
from datetime import date
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "jobs"))
from q1_risk import aggregate_daily
from pyspark.sql import SparkSession, functions as F


class Q1RiskTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.spark = (SparkSession.builder.master("local[1]").appName("is459-q1-regression")
                     .config("spark.ui.enabled", "false").config("spark.sql.ansi.enabled", "false")
                     .config("spark.sql.shuffle.partitions", "1").getOrCreate())
        cls.spark.sparkContext.setLogLevel("ERROR")

    @classmethod
    def tearDownClass(cls):
        cls.spark.stop()

    def tearDown(self):
        self.spark.catalog.clearCache()

    def inputs(self):
        version, run = "ibm-hi-medium-test", "dev-test-v2"
        # Two legitimate duplicate-looking transactions have different source IDs.
        rows = [("t1", 1, "US Dollar", "Euro", "ACH", "12.34000001"),
                ("t2", 1, "US Dollar", "Euro", "ACH", "12.34000001"),
                ("t3", 2, "US Dollar", "US Dollar", "ACH", "5.00"),
                ("t4", 1, "Euro", "Euro", "ACH", "8.00"),
                ("t5", 1, "Bitcoin", "Bitcoin", "Bitcoin", "0.472093")]
        facts = self.spark.createDataFrame(
            [(sid, version, run, date(2022, 9, day), "10", "20", fmt, paid, received,
              Decimal(amount), Decimal(amount)) for sid, day, paid, received, fmt, amount in rows],
            "source_id string, dataset_version string, run_id string, event_date date, "
            "sender_bank string, receiver_bank string, payment_format string, payment_currency string, "
            "receiving_currency string, amount_paid decimal(38,8), amount_received decimal(38,8)")
        labels = facts.select("source_id", "dataset_version", "run_id", "event_date").withColumn(
            "is_laundering", F.when(F.col("source_id").isin("t1", "t4"), 1).otherwise(0))
        prep = {"schema_version": 2, "status": "PASSED", "label_separation_passed": True,
                "source_reference_reconciliation_passed": True,
                "amount_policy": {"precision": 38, "scale": 8}, "dataset_version": version,
                "run_id": run, "accepted_rows": 5,
                "accepted_by_format": [{"payment_format": "ACH", "transactions": 4, "labelled_laundering": 2},
                                       {"payment_format": "Bitcoin", "transactions": 1, "labelled_laundering": 0}]}
        return facts, labels, prep

    def test_counts_precise_amounts_and_query_population(self):
        facts, labels, prep = self.inputs()
        daily, totals, grain = aggregate_daily(facts, labels, prep)
        self.assertEqual(totals, {"transactions": 5, "labelled_laundering": 2})
        self.assertIn("receiving_currency", grain)
        usd_eur = daily.filter((F.col("payment_currency") == "US Dollar") &
                               (F.col("receiving_currency") == "Euro")).first()
        self.assertEqual(usd_eur.transaction_count, 2)
        self.assertEqual(usd_eur.amount_paid_total, Decimal("24.68000002"))
        with tempfile.TemporaryDirectory() as directory:
            daily.write.partitionBy("event_date").parquet(directory + "/daily")
            restored = self.spark.read.parquet(directory + "/daily")
            restored.createOrReplaceTempView("q1_daily_test")
            sql = (Path(__file__).resolve().parents[1] / "sql/q1_segment_ranking.sql").read_text()
            sql = (sql.replace("is459_aml_dev.q1_daily_counts_dev20220901_v2", "q1_daily_test")
                   .replace("ibm-hi-medium-b1b99c68b765580f", prep["dataset_version"])
                   .replace("dev-20220901-v2", prep["run_id"])
                   .replace("AND DATE '2022-09-01'", "AND DATE '2022-09-02'")
                   .replace("s.n >= 1000", "s.n >= 1"))
            result = self.spark.sql(sql).first()
        self.assertEqual((result.n, result.l), (3, 1))
        self.assertAlmostEqual(result.laundering_rate, 1 / 3)
        self.assertAlmostEqual(result.risk_lift, 1.0)

    def test_duplicate_labels_cannot_multiply_facts(self):
        facts, labels, prep = self.inputs()
        duplicate = labels.filter("source_id != 't2'").unionByName(labels.filter("source_id = 't1'"))
        with self.assertRaisesRegex(ValueError, "not unique"):
            aggregate_daily(facts, duplicate, prep)

    def test_missing_label_match_fails_even_with_same_input_counts(self):
        facts, labels, prep = self.inputs()
        unmatched = labels.withColumn("source_id", F.when(F.col("source_id") == "t5", "missing").otherwise(F.col("source_id")))
        with self.assertRaisesRegex(ValueError, "join lost"):
            aggregate_daily(facts, unmatched, prep)

    def test_changed_labels_fail_independent_preparation_reference(self):
        facts, labels, prep = self.inputs()
        changed = labels.withColumn("is_laundering", F.lit(0))
        with self.assertRaisesRegex(ValueError, "preparation reference"):
            aggregate_daily(facts, changed, prep)

    def test_rejects_rounded_amount_schema_and_label_leakage(self):
        facts, labels, prep = self.inputs()
        with self.assertRaisesRegex(ValueError, "decimal"):
            aggregate_daily(facts.withColumn("amount_paid", F.col("amount_paid").cast("decimal(38,2)")), labels, prep)
        with self.assertRaisesRegex(ValueError, "laundering column"):
            aggregate_daily(facts.withColumn("is_laundering", F.lit(0)), labels, prep)

    def test_null_and_foreign_run_keys_are_rejected(self):
        facts, labels, prep = self.inputs()
        for run in (None, "wrong-run"):
            with self.subTest(run=run), self.assertRaisesRegex(ValueError, "null transaction keys"):
                aggregate_daily(facts.withColumn("run_id", F.lit(run).cast("string")), labels, prep)


if __name__ == "__main__":
    unittest.main()
