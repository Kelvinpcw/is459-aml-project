"""Regression for lost six-decimal payments, using the production Spark expressions."""
import json
import sys
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "jobs"))
from prepare import amount_is_valid, with_typed_amounts
from q1_risk import validate_preparation_contract
from pyspark.sql import SparkSession, functions as F


class AmountPrecisionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.spark = (SparkSession.builder.master("local[1]").appName("is459-precision-regression")
                     .config("spark.ui.enabled", "false")
                     .config("spark.sql.ansi.enabled", "false")
                     .config("spark.sql.shuffle.partitions", "1").getOrCreate())
        cls.spark.sparkContext.setLogLevel("ERROR")

    @classmethod
    def tearDownClass(cls):
        cls.spark.stop()

    def test_exact_amounts_survive_parquet_and_currency_grouping(self):
        rows = [("Bitcoin", "0.472093", "0.472093"),
                ("Bitcoin", "0.00000001", "0.00000001"),
                ("US Dollar", "12.34", "12.34")]
        frame = with_typed_amounts(self.spark.createDataFrame(
            rows, ["currency", "amount_paid_raw", "amount_received_raw"]))
        self.assertEqual(frame.filter(~amount_is_valid("amount_paid_raw", "amount_paid")).count(), 0)
        self.assertEqual(frame.filter(~amount_is_valid("amount_received_raw", "amount_received")).count(), 0)
        with tempfile.TemporaryDirectory() as directory:
            frame.write.parquet(directory + "/facts")
            restored = self.spark.read.parquet(directory + "/facts")
            totals = {r["currency"]: r["total"] for r in restored.groupBy("currency").agg(
                F.sum("amount_paid").alias("total")).collect()}
        self.assertEqual(totals, {"Bitcoin": Decimal("0.47209301"), "US Dollar": Decimal("12.34")})

    def test_excess_precision_malformed_and_overflow_are_rejected(self):
        cases = [("0.000000001",), ("NaN",), ("1e3",), ("",), (None,),
                 ("1000000000000000000000000000000",)]
        frame = with_typed_amounts(self.spark.createDataFrame(cases, "amount_paid_raw string")
                                  .withColumn("amount_received_raw", F.col("amount_paid_raw")))
        self.assertEqual(frame.filter(amount_is_valid("amount_paid_raw", "amount_paid")).count(), 0)
        # Casting alone would round the first value to zero; validation must still reject it.
        rounded = frame.filter(F.col("amount_paid_raw") == "0.000000001").first()
        self.assertEqual(rounded.amount_paid, Decimal("0"))


class PreparationContractTests(unittest.TestCase):
    def test_existing_incomplete_population_is_blocked(self):
        path = Path(__file__).resolve().parents[1] / "aws/reviews/preparation-report-dev-20220901-v1.json"
        with self.assertRaisesRegex(ValueError, "v1 population"):
            validate_preparation_contract(json.loads(path.read_text()))

    def test_v2_requires_reconciled_population_and_separated_labels(self):
        report = {"schema_version": 2, "status": "PASSED", "label_separation_passed": True,
                  "source_reference_reconciliation_passed": True,
                  "amount_policy": {"precision": 38, "scale": 8}}
        validate_preparation_contract(report)
        for field in ("source_reference_reconciliation_passed", "label_separation_passed"):
            with self.assertRaises(ValueError):
                validate_preparation_contract({**report, field: False})


if __name__ == "__main__":
    unittest.main()
