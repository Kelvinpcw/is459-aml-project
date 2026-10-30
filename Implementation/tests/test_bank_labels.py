import csv
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from dashboard.bank_labels import bank_label, load_bank_names, segment_label


class BankLabelsTests(unittest.TestCase):
    def lookup(self, rows):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'accounts.csv'
            with path.open('w', newline='') as output:
                writer = csv.writer(output)
                writer.writerow(['Bank ID', 'Bank Name', 'Account Number'])
                writer.writerows(rows)
            return load_bank_names(path)

    def test_names_and_ids_preserve_direction_and_format(self):
        names = self.lookup([['011', 'Bank of Miami', 'A'], ['00214', 'First Bank of Dallas', 'B']])
        row = {'sender_bank': '11', 'receiver_bank': '214'}
        self.assertEqual(segment_label(row, names), 'Bank of Miami (11) → First Bank of Dallas (214)')
        self.assertEqual(segment_label({**row, 'payment_format': 'ACH'}, names),
                         'Bank of Miami (11) → First Bank of Dallas (214) · ACH')
        self.assertEqual(row, {'sender_bank': '11', 'receiver_bank': '214'})
        self.assertEqual(segment_label({'payment_format': 'ACH'}, names), 'ACH')

    def test_duplicate_accounts_and_shared_names_do_not_merge_ids(self):
        names = self.lookup([['001', 'Shared Bank', 'A'], ['1', 'Shared Bank', 'B'], ['2', 'Shared Bank', 'C']])
        self.assertEqual(len(names), 2)
        self.assertNotEqual(bank_label('1', names), bank_label('2', names))

    def test_missing_names_keep_ids_and_conflicting_names_fail(self):
        self.assertEqual(bank_label('00042', {}), 'Unknown bank (42)')
        with self.assertRaisesRegex(ValueError, 'Conflicting bank names'):
            self.lookup([['001', 'One', 'A'], ['1', 'Another', 'B']])


if __name__ == '__main__':
    unittest.main()
