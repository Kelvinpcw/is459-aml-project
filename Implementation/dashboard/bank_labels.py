"""Bank display names only; never changes Q1 grouping keys or counts."""
from __future__ import annotations

import csv
from pathlib import Path


def normalise_bank_id(value):
    raw = str(value).strip()
    return str(int(raw)) if raw.isascii() and raw.isdigit() else raw


def load_bank_names(path):
    """Read raw accounts or a bank-only CSV with Bank ID and Bank Name headers.

    Repeated names across IDs are valid. Conflicting names for one normalised
    ID fail rather than selecting an arbitrary account's name.
    """
    names = {}
    with Path(path).open(newline='', encoding='utf-8-sig') as source:
        rows = csv.DictReader(source)
        if not {'Bank ID', 'Bank Name'}.issubset(rows.fieldnames or []):
            raise ValueError('Bank lookup requires Bank ID and Bank Name columns')
        for row in rows:
            bank_id = normalise_bank_id(row['Bank ID'] or '')
            name = (row['Bank Name'] or '').strip()
            if not bank_id or not name:
                continue
            if bank_id in names and names[bank_id] != name:
                raise ValueError(f'Conflicting bank names for ID {bank_id}')
            names[bank_id] = name
    return names


def bank_label(bank_id, names):
    key = normalise_bank_id(bank_id)
    name = names.get(key)
    return f'{name} ({key})' if name else f'Unknown bank ({key})'


def segment_label(row, names):
    if 'sender_bank' not in row:
        return str(row['payment_format'])
    if 'receiver_bank' not in row:
        return bank_label(row['sender_bank'], names)
    route = f"{bank_label(row['sender_bank'], names)} → {bank_label(row['receiver_bank'], names)}"
    return route + (f" · {row['payment_format']}" if 'payment_format' in row else '')


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Export bank IDs/names without account or entity data.')
    parser.add_argument('accounts_csv')
    parser.add_argument('output_csv')
    args = parser.parse_args()
    names = load_bank_names(args.accounts_csv)
    with Path(args.output_csv).open('x', newline='', encoding='utf-8') as output:
        writer = csv.writer(output)
        writer.writerow(['Bank ID', 'Bank Name'])
        writer.writerows(sorted(names.items()))
