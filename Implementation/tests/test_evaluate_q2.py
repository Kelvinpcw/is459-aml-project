"""Evaluator business denominators, annotation matching and full-population joins."""
from copy import deepcopy
from dataclasses import asdict, replace
from datetime import datetime, timedelta
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "jobs"))
from q2_detect import Config, build_cases, encode_case
from evaluate_q2 import (FACT_COLUMNS, MATCH_COLUMNS, collect_evaluation_window,
                         artifact_payloads, canonical_sha, collect_case_index, evaluate,
                         parse_annotations, select_scope, validate_evaluator_manifest, validate_index_row)

CONFIG = Config("ibm-test", "dev-test-v2", "q2-test-v1",
                "2022-09-01T00:00:00", "2022-09-01T00:01:00", "2022-09-01T00:01:00")


def row(sid, sender, receiver, amount="1.00000001", currency="US Dollar", minute=0):
    data = {"source_id": sid, "dataset_version": CONFIG.dataset_version, "run_id": CONFIG.run_id,
            "event_time": datetime(2022, 9, 1) + timedelta(minutes=minute),
            "sender_bank": "1", "sender_account": sender, "receiver_bank": "1", "receiver_account": receiver,
            "amount_paid": Decimal(amount), "amount_received": Decimal(amount),
            "payment_currency": currency, "receiving_currency": "Euro", "payment_format": "ACH"}
    for side, account in (("sender", sender), ("receiver", receiver)):
        data.update({f"{side}_entity_id": "E" + account, f"{side}_entity_name": account,
                     f"{side}_entity_unknown": False})
    return data


def frozen(records, cases_override=None, config=CONFIG):
    cases, stats = build_cases(records, config)
    if cases_override is not None:
        cases = cases_override
        from collections import Counter
        stats.update({"case_count": len(cases), "case_counts_by_pattern": dict(Counter(c["pattern_type"] for c in cases)),
                      "case_evidence_rows_including_case_overlap": sum(len(c["transactions"]) for c in cases)})
    report = {"stage": "q2", "status": "PASSED", "rule_version": "structural-v1", "config": asdict(config),
              "statistics": stats, "detector_received_labels": False, "full_prepared_rows": len(records)}
    return cases, report


def labels(records, positive=()):
    return [{"source_id": r["source_id"], "dataset_version": r["dataset_version"], "run_id": r["run_id"],
             "event_date": r["event_time"].date(), "is_laundering": int(r["source_id"] in positive)} for r in records]


def attempt(records, kind="FAN-OUT", identity="fixture:1"):
    return {"attempt_id": identity, "annotation_type": kind,
            "transactions": [{c: r[c] for c in MATCH_COLUMNS} for r in records]}


class EvaluationTests(unittest.TestCase):
    def test_manifest_pins_reports_and_exact_unique_case_inventory(self):
        manifest = {"schema_version": 1, "stage": "evaluator_inputs", "dataset_version": "ibm-test",
                    "run_id": "dev-test-v2", "analysis_id": "q2-test-v1",
                    "inputs": {"preparation_report": "s3://example/prep", "detector_report": "s3://example/q2",
                               "annotations": "s3://example/annotations"},
                    "preparation_report_sha256": "a" * 64, "detector_report_sha256": "b" * 64,
                    "annotations_sha256": "c" * 64,
                    "expected_cases": [{"case_id": "d" * 64, "emitted_json_sha256": "e" * 64}]}
        validate_evaluator_manifest(manifest)
        self.assertEqual(canonical_sha({"a": 1, "b": 2}), canonical_sha({"b": 2, "a": 1}))
        for changed in ({**manifest, "unexpected": 1}, {**manifest, "expected_cases": manifest["expected_cases"] * 2},
                        {**manifest, "annotations_sha256": "wrong"}):
            with self.assertRaises(ValueError):
                validate_evaluator_manifest(changed)

    def test_index_fields_and_output_artifacts_are_checked_without_mutating_cases(self):
        from q2_detect import case_index_row
        records = [row(str(i), "H", f"P{i}") for i in range(5)]
        cases, report = frozen(records)
        report["outputs"] = {"bundles": "s3://example/bundles/"}
        index = case_index_row(cases[0], CONFIG, "s3://example/bundles/" + cases[0]["case_id"] + ".json")
        validate_index_row(index, cases[0], report)
        with self.assertRaisesRegex(ValueError, "mismatch"):
            validate_index_row({**index, "bundle_uri": "s3://elsewhere/wrong"}, cases[0], report)
        result = evaluate(records, labels(records), cases, report, [])
        before = deepcopy(result)
        payloads = artifact_payloads(result)
        self.assertEqual(result, before)
        self.assertEqual(len(json.loads(payloads["alert_source_ids.json"])["detector"]), 5)
        self.assertNotIn("attempt_evaluation", json.loads(payloads["metrics.json"]))
        self.assertEqual(json.loads(payloads["case_evaluation.jsonl"])["supporting_transactions"], 5)

    def test_overlap_deduplicates_alerts_but_retains_case_support(self):
        records = [row("shared", "H", "A")] + [row(f"out{i}", "H", f"P{i}") for i in range(4)]
        records += [row(f"in{i}", f"S{i}", "A") for i in range(4)] + [row("missed", "Z", "Y", "100")]
        cases, report = frozen(records)
        result = evaluate(records, labels(records, ["shared", "missed"]), cases, report, [])
        measured = result["detector_transaction_metrics"]
        self.assertEqual(result["case_count"], 2)
        self.assertEqual(result["case_evidence_rows_including_overlap"], 10)
        self.assertEqual((measured["population"], measured["positive_labels"], measured["unique_alerted_transactions"]), (10, 2, 9))
        self.assertEqual((measured["true_positive"], measured["false_positive"], measured["false_negative"]), (1, 8, 1))
        self.assertAlmostEqual(measured["precision"], 1 / 9)
        self.assertEqual(measured["recall"], .5)
        self.assertEqual(sum(c["supporting_positive_labels"] for c in result["case_evaluation"]), 2)

    def test_amount_baseline_uses_full_population_payment_currency_and_stable_ties(self):
        records = [row(f"a{i}", "H", f"P{i}", "1") for i in range(5)]
        records += [row("large-outside-cases", "Z", "Y", "100"), row("huge-euro", "U", "V", "99999", "Euro")]
        cases, report = frozen(records)
        result = evaluate(records, labels(records, ["large-outside-cases"]), cases, report, [])
        self.assertEqual(result["amount_baseline_alert_source_ids"], ["a0", "a1", "a2", "a3", "large-outside-cases"])
        self.assertEqual(result["amount_baseline_transaction_metrics"]["true_positive"], 1)
        self.assertEqual(result["detector_transaction_metrics"]["true_positive"], 0)
        self.assertFalse(result["amount_baseline_policy"]["calibrated_for_holdout"])
        usd_audit = next(r for r in result["amount_baseline_policy"]["currency_audit"] if r["payment_currency"] == "US Dollar")
        self.assertEqual(usd_audit["last_selected_amount"], "1.00000000")

    def test_zero_positive_and_zero_annotation_denominators_are_null(self):
        records = [row(str(i), "H", f"P{i}") for i in range(5)]
        cases, report = frozen(records)
        result = evaluate(records, labels(records), cases, report, [])
        metric = result["detector_transaction_metrics"]
        self.assertEqual(metric["precision"], 0)
        self.assertIsNone(metric["recall"])
        self.assertIsNone(metric["lift_vs_population"])
        self.assertIsNone(result["annotation_metrics"]["attempt_recovery"])
        empty_cases, empty_report = frozen(records, [])
        no_alerts = evaluate(records, labels(records, ["0"]), empty_cases, empty_report, [])
        self.assertIsNone(no_alerts["detector_transaction_metrics"]["precision"])
        self.assertEqual(no_alerts["detector_transaction_metrics"]["recall"], 0)

    def test_source_join_rejects_missing_duplicate_foreign_or_invalid_labels(self):
        records = [row(str(i), "H", f"P{i}") for i in range(5)]
        cases, report = frozen(records)
        correct = labels(records)
        variants = [correct[:-1], correct[:-1] + [correct[0]],
                    [{**r, "run_id": "wrong"} for r in correct],
                    [{**r, "event_date": "2022-09-02"} for r in correct],
                    [{**r, "is_laundering": True} for r in correct]]
        for changed in variants:
            with self.subTest(changed=changed[0]), self.assertRaises(ValueError):
                evaluate(records, changed, cases, report, [])

    def test_evidence_tampering_omission_and_future_facts_fail(self):
        records = [row(str(i), "H", f"P{i}") for i in range(5)]
        cases, report = frozen(records)
        changed = deepcopy(cases)
        changed[0]["transactions"][0]["amount_paid"] = "500"
        with self.assertRaisesRegex(ValueError, "evidence"):
            evaluate(records, labels(records), changed, report, [])
        changed = deepcopy(cases)
        changed[0]["transactions"].pop()
        with self.assertRaises(ValueError):
            evaluate(records, labels(records), changed, report, [])
        future = deepcopy(records)
        future[0]["event_time"] += timedelta(minutes=1)
        with self.assertRaisesRegex(ValueError, "Future"):
            evaluate(future, labels(future), cases, report, [])

    def test_ambiguous_duplicate_looking_sources_remain_distinct_and_excluded(self):
        records = [row(str(i), "H", f"P{i}") for i in range(5)]
        records.append(row("same-looking", "H", "P0"))
        cases, report = frozen(records)
        result = evaluate(records, labels(records, [r["source_id"] for r in records]), cases, report, [attempt(records[:5])])
        self.assertEqual(result["detector_transaction_metrics"]["unique_alerted_transactions"], 6)
        self.assertEqual(result["annotation_metrics"]["eligible_attempts"], 0)
        self.assertIn("ambiguous_source_transaction", result["attempt_evaluation"][0]["exclusion_reasons"])
        self.assertEqual(result["attempt_evaluation"][0]["source_candidate_counts"][0], 2)

    def test_missed_attempt_remains_in_denominator_using_all_facts(self):
        records = [row(str(i), "H", f"P{i}") for i in range(5)]
        cases, report = frozen(records, [])  # A frozen detector missed the attempt.
        result = evaluate(records, labels(records, [r["source_id"] for r in records]), cases, report, [attempt(records)])
        self.assertEqual(result["annotation_metrics"]["eligible_attempts"], 1)
        self.assertEqual(result["annotation_metrics"]["attempt_recovery"], 0)
        self.assertEqual(result["attempt_evaluation"][0]["source_candidate_counts"], [1] * 5)

    def test_exact_eighty_percent_is_accepted_and_wrong_hub_is_not(self):
        records = [row(str(i), "H", f"P{i}") for i in range(6)]
        selected = records[:4] + records[5:]
        subset_cases, _ = frozen(selected)
        cases, report = frozen(records, subset_cases)
        result = evaluate(records, labels(records, [r["source_id"] for r in records]), cases, report, [attempt(records[:5])])
        self.assertEqual(result["annotation_metrics"]["attempt_recovery"], 1)
        other = [row("other" + str(i), "OTHER", f"Q{i}") for i in range(5)]
        all_records = records + other
        cases, report = frozen(all_records, subset_cases)
        result = evaluate(all_records, labels(all_records, [r["source_id"] for r in all_records]), cases, report, [attempt(other)])
        self.assertEqual(result["annotation_metrics"]["attempt_recovery"], 0)

    def test_typed_recovery_cannot_pool_multiple_cases(self):
        records = [row(str(i), "H", f"P{i}") for i in range(10)]
        first, _ = frozen(records[:5])
        second, _ = frozen(records[5:])
        cases, report = frozen(records, first + second)
        result = evaluate(records, labels(records, [r["source_id"] for r in records]), cases, report, [attempt(records)])
        self.assertEqual(result["annotation_metrics"]["attempt_recovery"], 0)
        self.assertEqual(result["annotation_metrics"]["detector_type_agnostic_coverage_80pct"], 1)

    def test_cycles_require_the_same_directed_topology(self):
        clockwise = [row("a", "A", "B"), row("b", "B", "C"), row("c", "C", "A")]
        reverse = [row("x", "A", "C"), row("y", "C", "B"), row("z", "B", "A")]
        subset, _ = frozen(clockwise)
        records = clockwise + reverse
        cases, report = frozen(records, subset)
        result = evaluate(records, labels(records, [r["source_id"] for r in records]), cases, report,
                          [attempt(clockwise, "CYCLE", "one"), attempt(reverse, "CYCLE", "two")])
        self.assertEqual(result["annotation_metrics"]["eligible_attempts"], 2)
        self.assertEqual(result["annotation_metrics"]["recovered_attempts"], 1)

    def test_window_cutoff_size_and_annotation_label_conflict_are_explicit(self):
        records = [row(str(i), "H", f"P{i}") for i in range(5)]
        cases, report = frozen(records)
        outside = [row(str(i), "H", f"P{i}", minute=1) for i in range(5)]
        self.assertEqual(select_scope(records + outside, report), records)
        result = evaluate(records, labels(records), cases, report,
                          [attempt(records), attempt(outside, identity="outside"), attempt(records[:2], identity="small")])
        reasons = result["annotation_metrics"]["exclusion_counts_overlapping"]
        self.assertIn("annotation_label_conflict", reasons)
        self.assertIn("outside_declared_window", reasons)
        self.assertIn("below_fan_degree", reasons)
        early = deepcopy(report)
        early["config"]["snapshot_cutoff"] = "2022-09-01T00:00:00"
        self.assertEqual(select_scope(records + outside, early), records)

    def test_label_changes_do_not_mutate_cases_and_holdout_is_not_silently_promoted(self):
        records = [row(str(i), "H", f"P{i}") for i in range(5)]
        cases, report = frozen(records)
        before = [encode_case(c) for c in cases]
        evaluate(records, labels(records), cases, report, [])
        evaluate(records, labels(records, ["0"]), cases, report, [])
        self.assertEqual(before, [encode_case(c) for c in cases])
        changed = deepcopy(report)
        changed["config"].update(window_start="2022-09-09T00:00:00", window_end="2022-09-09T00:01:00", snapshot_cutoff="2022-09-09T00:01:00")
        with self.assertRaisesRegex(ValueError, "holdout"):
            evaluate(records, labels(records), cases, changed, [])

    def test_annotation_parser_checks_checksum_boundaries_and_composite_banks(self):
        text = ("BEGIN LAUNDERING ATTEMPT - CYCLE:  Max 99 hops\r\n"
                "2022/09/01 00:00,001,A,02,B,0.47209301,Bitcoin,0.47209301,Bitcoin,ACH,1\r\n"
                "2022/09/01 00:00,02,B,001,A,0.47209301,Bitcoin,0.47209301,Bitcoin,ACH,1\r\n"
                "END LAUNDERING ATTEMPT - CYCLE\r\n")
        checksum = hashlib.sha256(text.encode()).hexdigest()
        parsed = parse_annotations(text, checksum)
        self.assertEqual(parsed[0]["attempt_id"], checksum + ":1")
        self.assertEqual(parsed[0]["transactions"][0]["sender_bank"], "1")
        self.assertEqual(parsed[0]["transactions"][0]["amount_paid"], Decimal(".47209301"))
        for invalid in (text.replace("END LAUNDERING ATTEMPT - CYCLE", "END LAUNDERING ATTEMPT - FAN-IN"),
                        text.split("END LAUNDERING")[0], text.replace(",ACH,1", ",ACH,0")):
            with self.assertRaises(ValueError):
                parse_annotations(invalid, hashlib.sha256(invalid.encode()).hexdigest())
        with self.assertRaisesRegex(ValueError, "checksum"):
            parse_annotations(text, "0" * 64)


class EvaluationSparkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from pyspark.sql import SparkSession
        cls.spark = (SparkSession.builder.master("local[1]").appName("is459-evaluator-tests")
                     .config("spark.ui.enabled", "false").config("spark.sql.session.timeZone", "UTC")
                     .config("spark.sql.shuffle.partitions", "1").getOrCreate())
        cls.spark.sparkContext.setLogLevel("ERROR")

    @classmethod
    def tearDownClass(cls):
        cls.spark.stop()

    def inputs(self):
        from pyspark.sql import functions as F, types as T
        records = [row(str(i), "H", f"P{i}") for i in range(5)] + [row("outside", "Z", "Y", minute=1)]
        fields = [T.StructField(c, T.TimestampType() if c == "event_time" else T.DecimalType(38, 8)
                               if c.startswith("amount_") else T.StringType()) for c in FACT_COLUMNS]
        facts = self.spark.createDataFrame([{c: r[c] for c in FACT_COLUMNS} for r in records], T.StructType(fields))
        facts = facts.withColumn("event_date", F.to_date("event_time"))
        target = facts.select("source_id", "dataset_version", "run_id", "event_date").withColumn(
            "is_laundering", F.when(F.col("source_id") == "outside", 1).otherwise(0))
        _, report = frozen(records)
        prep = {"status": "PASSED", "schema_version": 2, "label_separation_passed": True,
                "source_reference_reconciliation_passed": True, "quarantined_rows": 0,
                "dataset_version": CONFIG.dataset_version, "run_id": CONFIG.run_id,
                "amount_policy": {"precision": 38, "scale": 8}, "accepted_rows": 6,
                "fact_columns": facts.columns,
                "accepted_by_format": [{"payment_format": "ACH", "transactions": 6, "labelled_laundering": 1}]}
        return facts, target, prep, report

    def test_complete_population_precedes_window_collection(self):
        facts, target, prep, report = self.inputs()
        selected, matched = collect_evaluation_window(facts, target, prep, report)
        self.assertEqual(len(selected), 5)
        self.assertEqual(len(matched), 5)
        self.assertNotIn("is_laundering", selected[0])

    def test_missing_duplicate_and_changed_labels_fail_before_scoring(self):
        from pyspark.sql import functions as F
        facts, target, prep, report = self.inputs()
        changed = target.withColumn("source_id", F.when(F.col("source_id") == "outside", "missing").otherwise(F.col("source_id")))
        with self.assertRaisesRegex(ValueError, "join"):
            collect_evaluation_window(facts, changed, prep, report)
        duplicate = target.filter("source_id != 'outside'").unionByName(target.filter("source_id = '0'"))
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            collect_evaluation_window(facts, duplicate, prep, report)
        with self.assertRaisesRegex(ValueError, "reference"):
            collect_evaluation_window(facts, target.withColumn("is_laundering", F.lit(0)), prep, report)

    def test_precision_and_guarded_population_limits(self):
        from pyspark.sql import functions as F
        facts, target, prep, report = self.inputs()
        with self.assertRaisesRegex(ValueError, "amount"):
            collect_evaluation_window(facts.withColumn("amount_paid", F.col("amount_paid").cast("decimal(38,2)")), target, prep, report)
        report["config"]["max_window_rows"] = 4
        with self.assertRaisesRegex(ValueError, "window"):
            collect_evaluation_window(facts, target, prep, report)

    def test_explicit_case_index_schema_handles_zero_cases(self):
        from q2_detect import case_index_schema, case_index_row
        records = [row(str(i), "H", f"P{i}") for i in range(5)]
        cases, report = frozen(records)
        report["case_index_schema"] = case_index_schema().jsonValue()
        with tempfile.TemporaryDirectory() as directory:
            path = directory + "/empty"
            self.spark.createDataFrame([], case_index_schema()).write.partitionBy("window_date").parquet(path)
            report["outputs"] = {"case_index": path}
            self.assertEqual(collect_case_index(self.spark, report), [])
            path = directory + "/nonempty"
            index = [case_index_row(cases[0], CONFIG, "s3://example/case.json")]
            self.spark.createDataFrame(index, case_index_schema()).write.partitionBy("window_date").parquet(path)
            report["outputs"] = {"case_index": path}
            self.assertEqual(collect_case_index(self.spark, report)[0]["evidence_transaction_count"], 5)


if __name__ == "__main__":
    unittest.main()
