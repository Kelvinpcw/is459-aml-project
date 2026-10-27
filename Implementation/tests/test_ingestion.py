import csv
import gzip
import hashlib
import json
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from build_development_input import ORIGINAL_HEADER, build_input, sha256


class IngestionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.tx = self.root / "original.csv"
        self.accounts = self.root / "accounts.csv"
        self.patterns = self.root / "patterns.txt"
        self.accounts.write_text("Bank Name,Bank ID,Account Number,Entity ID,Entity Name\nBank,20,A,E,Entity\n")
        self.patterns.write_text("Synthetic evaluation reference\n")

    def tearDown(self):
        self.temp.cleanup()

    def row(self, timestamp="2022/09/01 12:00", label="0"):
        return [timestamp, "020", "SENDER", "030", "RECEIVER", "12.34", "US Dollar",
                "12.34", "US Dollar", "Wire", label]

    def write_rows(self, rows, header=ORIGINAL_HEADER):
        with self.tx.open("w", newline="") as target:
            writer = csv.writer(target)
            writer.writerow(header)
            writer.writerows(rows)

    def build(self, name="out", start=date(2022, 9, 1), end=date(2022, 9, 2)):
        return build_input(self.tx, self.accounts, self.patterns, self.root / name, start, end)

    def read_output(self, name="out"):
        with gzip.open(self.root / name / "transactions.csv.gz", "rt", newline="") as source:
            return list(csv.DictReader(source))

    def test_unsorted_dates_and_duplicate_rows_keep_original_ordinals(self):
        self.write_rows([self.row("2022/09/02 00:00"), self.row(), self.row()])
        manifest = self.build()
        rows = self.read_output()
        digest = sha256(self.tx)
        self.assertEqual([row["source_id"] for row in rows], [digest + ":2", digest + ":3"])
        self.assertEqual([row["sender_account"] for row in rows], ["SENDER", "SENDER"])
        self.assertEqual([row["receiver_account"] for row in rows], ["RECEIVER", "RECEIVER"])
        self.assertEqual(manifest["counts"]["outside_development_scope"], 1)
        self.assertEqual(manifest["counts"]["selected_records"], 2)

    def test_invalid_records_are_quarantined_and_counts_reconcile(self):
        self.write_rows([self.row(), ["bad", "width"], self.row("not-a-timestamp"), self.row("2022/09/04 00:00")])
        manifest = self.build()
        counts = manifest["counts"]
        self.assertEqual(counts["source_records"], 4)
        self.assertEqual(counts["selected_records"] + counts["ingestion_quarantined"] +
                         counts["outside_development_scope"], 4)
        with gzip.open(self.root / "out/ingestion-quarantine.jsonl.gz", "rt") as source:
            rejected = [json.loads(line) for line in source]
        self.assertEqual([r["source_record_ordinal"] for r in rejected], [2, 3])
        self.assertEqual([r["reason"] for r in rejected], ["wrong_column_count", "invalid_timestamp"])

    def test_stable_ids_across_different_date_scopes(self):
        self.write_rows([self.row(), self.row("2022/09/02 00:00")])
        narrow = self.build("narrow")
        wide = self.build("wide", end=date(2022, 9, 3))
        self.assertEqual(self.read_output("narrow")[0]["source_id"], self.read_output("wide")[0]["source_id"])
        self.assertEqual(narrow["dataset_version"], wide["dataset_version"])

    def test_gzip_is_reproducible_and_originals_are_unchanged(self):
        self.write_rows([self.row(label="1")])
        before = {p.name: sha256(p) for p in (self.tx, self.accounts, self.patterns)}
        first, second = self.build("first"), self.build("second")
        self.assertEqual(first, second)
        for filename in ("transactions.csv.gz", "accounts.csv.gz", "ingestion-quarantine.jsonl.gz"):
            self.assertEqual((self.root / "first" / filename).read_bytes(), (self.root / "second" / filename).read_bytes())
        self.assertEqual(before, {p.name: sha256(p) for p in (self.tx, self.accounts, self.patterns)})
        self.assertEqual(first["q1_source_reference_by_format"]["Wire"]["labelled_laundering"], 1)

    def test_refuses_to_overwrite_a_previous_ingestion(self):
        self.write_rows([self.row()])
        self.build()
        with self.assertRaises(FileExistsError):
            self.build()

    def test_rejects_a_changed_header_and_marks_output_incomplete(self):
        self.write_rows([self.row()], header=["wrong", *ORIGINAL_HEADER[1:]])
        with self.assertRaises(ValueError):
            self.build()
        self.assertTrue((self.root / "out/INCOMPLETE.txt").exists())
        self.assertFalse((self.root / "out/manifest.json").exists())

    def test_empty_selection_fails(self):
        self.write_rows([self.row("2022/09/09 00:00")])
        with self.assertRaises(ValueError):
            self.build()
        self.assertTrue((self.root / "out/INCOMPLETE.txt").exists())

    def test_dataset_version_changes_when_account_mapping_changes(self):
        self.write_rows([self.row()])
        first = self.build("first")
        with self.accounts.open("a") as target:
            target.write("Other,30,B,F,Other Entity\n")
        second = self.build("second")
        self.assertNotEqual(first["dataset_version"], second["dataset_version"])


if __name__ == "__main__":
    unittest.main()
