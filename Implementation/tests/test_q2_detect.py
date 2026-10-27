"""Q2 structural semantics, input isolation, exact evidence and bounded execution."""
from dataclasses import replace
from datetime import datetime, timedelta
from decimal import Decimal
import itertools
import json
from pathlib import Path
import random
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "jobs"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from q2_detect import (Config, DetectionLimitError, DETECTOR_COLUMNS, build_cases,
                       case_index_row, case_index_schema, collect_window, encode_case, validate_manifest)
from make_q2_input_manifest import make_manifest

CONFIG = Config("ibm-hi-medium-test", "dev-test-v2", "q2-test-v1",
                "2022-09-01T00:00:00", "2022-09-01T01:00:00", "2022-09-01T01:00:00")


def transaction(sid, src, dst, minute=0, unknown=False):
    def pair(n):
        return n if isinstance(n, tuple) else ("1", n)
    src, dst = pair(src), pair(dst)
    row = {"source_id": sid, "dataset_version": CONFIG.dataset_version, "run_id": CONFIG.run_id,
           "event_time": datetime(2022, 9, 1) + timedelta(minutes=minute),
           "sender_bank": src[0], "sender_account": src[1], "receiver_bank": dst[0], "receiver_account": dst[1],
           "amount_paid": Decimal("0.47209301"), "amount_received": Decimal("0.47209301"),
           "payment_currency": "Bitcoin", "receiving_currency": "Bitcoin", "payment_format": "Bitcoin"}
    for side, node in (("sender", src), ("receiver", dst)):
        row.update({f"{side}_entity_id": None if unknown else "E" + str(node),
                    f"{side}_entity_name": None if unknown else "Entity " + str(node),
                    f"{side}_entity_unknown": unknown})
    return row


def manifest(rows):
    return {"schema_version": 1, "stage": "detector_inputs", "preparation_status": "PASSED",
            "dataset_version": CONFIG.dataset_version, "run_id": CONFIG.run_id,
            "accepted_rows": len(rows), "fact_columns": list(DETECTOR_COLUMNS),
            "amount_policy": {"precision": 38, "scale": 8},
            "inputs": {"transactions": "s3://example/curated/transactions/"},
            "timestamp_policy": "dataset-local"}


class Q2CoreTests(unittest.TestCase):
    def test_distinct_fan_degree_and_all_source_evidence(self):
        rows = [transaction(str(i), f"P{i}", "H") for i in range(5)]
        rows += [transaction("duplicate-looking", "P0", "H"), transaction("self", "H", "H")]
        cases, stats = build_cases(rows, CONFIG)
        self.assertEqual([c["pattern_type"] for c in cases], ["fan_in"])
        case = cases[0]
        self.assertEqual((case["participant_count"], case["unique_edge_count"], case["evidence_transaction_count"]), (6, 5, 6))
        self.assertEqual(len({r["source_id"] for r in case["transactions"]}), 6)
        self.assertEqual(stats["self_transaction_rows"], 1)
        fewer = [transaction(str(i), "P", "H") for i in range(8)]
        self.assertEqual(build_cases(fewer, CONFIG)[0], [])

    def test_cycles_2_3_4_rotations_and_bank_account_identity(self):
        rows = [transaction("a", ("1", "SAME"), ("2", "SAME")),
                transaction("b", ("2", "SAME"), ("1", "SAME"))]
        for size in (3, 4):
            nodes = [f"{size}-{n}" for n in range(size)]
            rows += [transaction(f"{size}-{n}", nodes[n], nodes[(n + 1) % size], minute=size - n)
                     for n in range(size)]
        cases, _ = build_cases(rows, CONFIG)
        self.assertEqual(sorted(c["pattern_type"] for c in cases), ["cycle_2", "cycle_3", "cycle_4"])
        for case in cases:
            self.assertEqual(case["participant_count"], len({n["node_id"] for n in case["nodes"]}))

    def test_reverse_directed_cycles_remain_distinct(self):
        rows = [transaction(str(i), a, b) for i, (a, b) in enumerate(itertools.permutations("ABC", 2))]
        cases, _ = build_cases(rows, CONFIG)
        self.assertEqual(sum(c["pattern_type"] == "cycle_3" for c in cases), 2)
        self.assertEqual(sum(c["pattern_type"] == "cycle_2" for c in cases), 3)

    def test_snapshot_and_exclusive_end_prevent_future_leakage(self):
        rows = [transaction(str(i), "H", f"P{i}", minute=i) for i in range(5)]
        rows += [transaction("close", "P0", "H", minute=59), transaction("at-end", "Z", "H", minute=60)]
        early = replace(CONFIG, snapshot_cutoff="2022-09-01T00:03:00")
        cases, stats = build_cases(rows, early)
        self.assertEqual(cases, [])
        self.assertEqual(stats["after_cutoff_rows"], 2)
        self.assertEqual(stats["outside_window_rows"], 1)

    def test_stable_ids_reordering_attempt_identity_and_exact_json(self):
        rows = [transaction(str(i), "H", f"P{i}", unknown=True) for i in range(5)]
        first, _ = build_cases(rows, CONFIG)
        second, _ = build_cases(reversed(rows), replace(CONFIG, analysis_id="attempt-two"))
        self.assertEqual(first[0]["case_id"], second[0]["case_id"])
        decoded = json.loads(encode_case(first[0]))
        self.assertEqual(decoded["transactions"][0]["amount_paid"], "0.47209301")
        self.assertTrue(all(n["entity_unknown"] for n in decoded["nodes"]))

    def test_duplicate_ids_leakage_and_mapping_conflicts_are_rejected(self):
        row = transaction("t", "A", "B")
        with self.assertRaisesRegex(ValueError, "duplicate"):
            build_cases([row, row], CONFIG)
        with self.assertRaisesRegex(ValueError, "labels"):
            build_cases([{**row, "is_laundering": 0}], CONFIG)
        changed = transaction("u", "A", "C")
        changed["sender_entity_id"] = "CONFLICT"
        with self.assertRaisesRegex(ValueError, "mapping"):
            build_cases([row, changed], CONFIG)

    def test_limits_fail_instead_of_truncating(self):
        fan = [transaction(str(i), "H", f"P{i}") for i in range(5)]
        for field, limit in (("max_window_rows", 4), ("max_edges", 4), ("max_case_nodes", 5),
                             ("max_case_evidence", 4), ("max_total_evidence", 4), ("max_bundle_bytes", 1)):
            with self.subTest(field=field), self.assertRaises(DetectionLimitError):
                build_cases(fan, replace(CONFIG, **{field: limit}))
        triangle = [transaction("a", "A", "B"), transaction("b", "B", "C"), transaction("c", "C", "A")]
        with self.assertRaises(DetectionLimitError):
            build_cases(triangle, replace(CONFIG, max_cycle_expansions=1))
        reciprocal = [transaction(str(i), a, b) for i, (a, b) in enumerate(itertools.permutations("ABC", 2))]
        with self.assertRaises(DetectionLimitError):
            build_cases(reciprocal, replace(CONFIG, max_cases=1))

    def test_acyclic_large_fan_does_not_expand_cycle_paths(self):
        rows = [transaction(str(i), "H", f"P{i}") for i in range(301)]
        cases, stats = build_cases(rows, replace(CONFIG, max_cycle_expansions=1))
        self.assertEqual(len(cases), 1)
        self.assertEqual(stats["cycle_expansions"], 0)

    def test_cycle_enumeration_matches_independent_exhaustive_oracle(self):
        rng = random.Random(459)
        names = list("ABCDE")
        for trial in range(15):
            edges = {(a, b) for a, b in itertools.permutations(names, 2) if rng.random() < .4}
            rows = [transaction(str(i), a, b) for i, (a, b) in enumerate(sorted(edges))]
            cases, _ = build_cases(rows, CONFIG)
            actual = {tuple(n["account"] for n in c["nodes"]) for c in cases if c["pattern_type"].startswith("cycle_")}
            expected = set()
            for size in (2, 3, 4):
                for path in itertools.permutations(names, size):
                    if path[0] == min(path) and all((path[i], path[(i + 1) % size]) in edges for i in range(size)):
                        expected.add(path)
            self.assertEqual(actual, expected, trial)

    def test_handoff_strips_all_reference_payloads_and_rejects_extra_inputs(self):
        root = Path(__file__).resolve().parents[1]
        prep = json.loads((root / "aws/reviews/preparation-report-dev-20220901-v2.json").read_text())
        safe = make_manifest(prep)
        validate_manifest(safe)
        for forbidden in ("source_manifest", "accepted_by_format", "labels", "labelled_laundering"):
            self.assertNotIn(forbidden, json.dumps(safe))
        with self.assertRaises(ValueError):
            validate_manifest({**safe, "source_manifest": prep["source_manifest"]})
        with self.assertRaises(ValueError):
            validate_manifest({**safe, "inputs": {**safe["inputs"], "labels": "s3://example/labels"}})


class Q2SparkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from pyspark.sql import SparkSession
        cls.spark = (SparkSession.builder.master("local[1]").appName("is459-q2-regression")
                     .config("spark.ui.enabled", "false").config("spark.sql.session.timeZone", "UTC")
                     .config("spark.sql.shuffle.partitions", "1").getOrCreate())
        cls.spark.sparkContext.setLogLevel("ERROR")

    @classmethod
    def tearDownClass(cls):
        cls.spark.stop()

    def frame(self, rows):
        from pyspark.sql import types as T
        fields = []
        for name in DETECTOR_COLUMNS:
            kind = (T.TimestampType() if name == "event_time" else T.DecimalType(38, 8) if name.startswith("amount_")
                    else T.BooleanType() if name.endswith("_unknown") else T.StringType())
            fields.append(T.StructField(name, kind, True))
        return self.spark.createDataFrame(rows, T.StructType(fields))

    def test_guarded_spark_projection_and_case_index_parquet_roundtrip(self):
        rows = [transaction(str(i), "H", f"P{i}") for i in range(5)] + [transaction("future", "Z", "H", 60)]
        selected = collect_window(self.frame(rows), manifest(rows), CONFIG)
        self.assertEqual(len(selected), 5)
        cases, _ = build_cases(selected, CONFIG)
        index = [case_index_row(c, CONFIG, f"s3://example/{c['case_id']}.json") for c in cases]
        with tempfile.TemporaryDirectory() as directory:
            self.spark.createDataFrame(index, case_index_schema()).write.partitionBy("window_date").parquet(directory + "/index")
            restored = self.spark.read.parquet(directory + "/index")
            self.assertEqual(restored.first().evidence_transaction_count, 5)
            empty = self.spark.createDataFrame([], case_index_schema())
            empty.write.partitionBy("window_date").parquet(directory + "/empty")
            self.assertEqual(self.spark.read.schema(case_index_schema()).parquet(directory + "/empty").count(), 0)

    def test_spark_collection_limit_and_label_schema_guard(self):
        from pyspark.sql import functions as F
        rows = [transaction(str(i), "H", f"P{i}") for i in range(5)]
        with self.assertRaises(DetectionLimitError):
            collect_window(self.frame(rows), manifest(rows), replace(CONFIG, max_window_rows=4))
        with self.assertRaisesRegex(ValueError, "labels"):
            collect_window(self.frame(rows).withColumn("is_laundering", F.lit(0)), manifest(rows), CONFIG)


if __name__ == "__main__":
    unittest.main()
