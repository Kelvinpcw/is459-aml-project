"""Synthetic population checks for the monitoring overview; no AWS calls."""
import re
import sqlite3
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from dashboard.data import q1_query, q1_trend_query
from pipeline.release import validate_candidate
from test_release_dashboard import fixture


class OverviewTests(unittest.TestCase):
    def setUp(self):
        candidate, reports = fixture()
        self.release = validate_candidate(candidate, reports)
        self.release['q1']['dates'] = ['2022-09-01', '2022-09-02']
        self.db = sqlite3.connect(':memory:')
        self.addCleanup(self.db.close)
        self.db.row_factory = sqlite3.Row
        self.db.execute("ATTACH DATABASE ':memory:' AS aml")
        self.db.execute('''CREATE TABLE aml.risk_run (
            dataset_version TEXT, run_id TEXT, event_date TEXT,
            sender_bank TEXT, receiver_bank TEXT, payment_format TEXT,
            payment_currency TEXT, receiving_currency TEXT,
            transaction_count INTEGER, laundering_count INTEGER,
            amount_paid_total TEXT, amount_received_total TEXT)''')
        self.db.executemany('INSERT INTO aml.risk_run VALUES (?,?,?,?,?,?,?,?,?,?,?,?)', [
            ('fixture','run','2022-09-01','A','A','ACH','USD','EUR',100,10,'100.00000001','90.00000001'),
            ('fixture','run','2022-09-02','A','B','ACH','EUR','USD',900,0,'900','1000'),
            ('fixture','run','2022-09-01','B','A','Wire','USD','USD',200,20,'200','200'),
            ('fixture','other','2022-09-01','A','B','ACH','USD','USD',5000,5000,'5000','5000'),
        ])

    def query(self, **kwargs):
        if kwargs.get('grain') == 'daily':
            sql = q1_trend_query(self.release, '2022-09-01', '2022-09-02', kwargs['currency'])
        else:
            sql = q1_query(self.release, '2022-09-01', '2022-09-02', min_support=1000, **kwargs)
        # SQLite accepts the aggregate SQL; adapt Athena's date literal syntax only.
        return [dict(row) for row in self.db.execute(re.sub(r"DATE ('[^']*')", r'\1', sql))]

    def test_all_currencies_banks_do_not_duplicate_self_or_cross_bank_payments(self):
        rows = self.query(currency=None, grain='bank')
        by_bank = {r['sender_bank']: r for r in rows}
        self.assertEqual(sum(r['n'] for r in rows), 1200)
        self.assertEqual(by_bank['A']['n'], 1000)
        self.assertAlmostEqual(by_bank['A']['rate'], .01)
        self.assertAlmostEqual(by_bank['A']['lift'], .4)
        self.assertEqual(by_bank['A']['support'], 'supported')
        self.assertEqual(by_bank['B']['support'], 'low_support')
        self.assertTrue(all(r['baseline_n'] == 1200 and r['baseline_l'] == 30 for r in rows))
        sql = q1_query(self.release, '2022-09-01', '2022-09-02', None, grain='bank')
        self.assertNotIn('selected_currency_amount', sql)
        self.assertNotIn('SUM(amount_', sql)

    def test_currency_selection_changes_counts_support_and_baseline_together(self):
        rows = self.query(currency='USD', grain='bank')
        self.assertEqual(sum(r['n'] for r in rows), 300)
        self.assertTrue(all(r['baseline_n'] == 300 and r['baseline_l'] == 30 for r in rows))
        self.assertTrue(all(r['support'] == 'low_support' for r in rows))
        self.assertAlmostEqual(next(r['lift'] for r in rows if r['sender_bank'] == 'A'), 1)
        sql = q1_query(self.release, '2022-09-01', '2022-09-02', 'USD')
        self.assertIn('SUM(amount_paid_total)', sql)
        self.assertNotIn('SUM(amount_received_total)', sql)

    def test_payment_types_compare_labelled_exposure_with_their_size(self):
        types = {r['payment_format']:r for r in self.query(currency=None, grain='format')}
        self.assertEqual((types['ACH']['n'],types['ACH']['l']), (1000,10))
        self.assertEqual((types['Wire']['n'],types['Wire']['l']), (200,20))
        self.assertAlmostEqual(types['Wire']['rate'], .1)
        self.assertAlmostEqual(types['Wire']['lift'], 4)
        self.assertAlmostEqual(types['Wire']['n']/types['Wire']['baseline_n'], 1/6)
        self.assertAlmostEqual(types['Wire']['l']/types['Wire']['baseline_l'], 2/3)
        self.assertEqual(types['Wire']['support'], 'low_support')

    def test_daily_and_route_drilldown_use_same_population_and_identity(self):
        days = self.query(currency=None, grain='daily')
        self.assertEqual([r['event_date'] for r in days], ['2022-09-01', '2022-09-02'])
        self.assertEqual([r['n'] for r in days], [300,900])
        routes = self.query(currency=None, grain='bank_pair', sender_bank='A')
        self.assertEqual(sum(r['n'] for r in routes), 1000)
        self.assertTrue(all(r['sender_bank'] == 'A' and r['baseline_n'] == 1000 for r in routes))
        self.assertEqual({r['receiver_bank'] for r in routes}, {'A', 'B'})


if __name__ == '__main__':
    unittest.main()
