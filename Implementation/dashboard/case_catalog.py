"""Page the pinned Q2 case index without querying Athena on every interaction."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from hashlib import sha256
from io import BytesIO
import fcntl
import json
import os
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory

from pipeline.release import split_uri


PAGE_SIZE = 20
FIELDS = (
    'case_id', 'pattern_type', 'participant_count', 'evidence_transaction_count',
    'bundle_uri', 'bundle_member', 'bundle_sha256', 'window_end',
    'dataset_version', 'run_id', 'analysis_id',
)


class CaseCatalog:
    def __init__(self, s3, release, cache_dir=None):
        q2 = release['q2']
        self.total = q2['case_count']
        self.snapshots = {row['window_end']: row for row in q2.get('snapshots') or [q2]}
        bucket, prefix = split_uri(q2['case_index'].rstrip('/') + '/')
        identity = release['dataset_version'], release['run_id'], q2['analysis_id']
        signature = sha256(json.dumps([release['release_id'], identity, q2], sort_keys=True).encode()).hexdigest()
        root = Path(cache_dir or Path.home() / '.cache' / 'trace-q2-catalog')
        root.mkdir(mode=0o700, parents=True, exist_ok=True)
        if root.is_symlink() or root.stat().st_uid != os.getuid() or root.stat().st_mode & 0o077:
            raise ValueError('Case index cache must be owned by the dashboard user and private')
        self.path = root / f'{signature}.sqlite'
        if self.path.is_file():
            return
        with (root / 'build.lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            if self.path.is_file():
                return
            with TemporaryDirectory(dir=root, prefix='build-') as work:
                path = Path(work) / 'cases.sqlite'
                self._build(path, s3, bucket, prefix, identity)
                path.replace(self.path)

    def _build(self, path, s3, bucket, prefix, identity):
        import pyarrow.parquet as parquet

        with closing(sqlite3.connect(path)) as db, ThreadPoolExecutor(max_workers=8) as pool:
            # This file is private staging until all checks pass and it is renamed.
            # A rollback journal is unnecessary and can double the disk work.
            db.execute('PRAGMA journal_mode=OFF')
            db.execute('PRAGMA cache_size=-65536')
            db.execute("""CREATE TABLE cases (
                case_id TEXT NOT NULL, snapshot TEXT NOT NULL, pattern_type TEXT NOT NULL,
                participant_count INTEGER NOT NULL, evidence_transaction_count INTEGER NOT NULL,
                bundle_uri TEXT NOT NULL, bundle_member TEXT, bundle_sha256 TEXT,
                PRIMARY KEY (case_id, snapshot)
            ) WITHOUT ROWID""")
            total = 0
            for end, snapshot in sorted(self.snapshots.items()):
                partition = prefix + f"window_date={snapshot['window_start'][:10]}/"
                pages = s3.get_paginator('list_objects_v2').paginate(Bucket=bucket, Prefix=partition)
                files = [obj['Key'] for page in pages for obj in page.get('Contents', ())
                         if obj['Key'].startswith(partition) and obj['Key'].endswith('.parquet')]

                def read(key):
                    with closing(s3.get_object(Bucket=bucket, Key=key)['Body']) as body:
                        source = parquet.ParquetFile(BytesIO(body.read()))
                    columns = [field for field in FIELDS if field in source.schema.names]
                    result = []
                    for row in source.read(columns=columns).to_pylist():
                        if (row['window_end'].isoformat() != end
                                or (row['dataset_version'], row['run_id'], row['analysis_id']) != identity):
                            continue
                        result.append((row['case_id'], end, row['pattern_type'], row['participant_count'],
                                       row['evidence_transaction_count'], row['bundle_uri'],
                                       row.get('bundle_member'), row.get('bundle_sha256')))
                    return result

                # The primary key is ordered by case ID. Insert each snapshot in
                # that order to avoid random writes across the entire index.
                rows = sorted(row for batch in pool.map(read, files) for row in batch)
                count = len(rows)
                payments = sum(row[4] for row in rows)
                expected_payments = snapshot.get('case_evidence_rows_including_case_overlap')
                if count != snapshot['case_count'] or (expected_payments is not None and payments != expected_payments):
                    raise ValueError(f'Published case index does not match the snapshot ending {end}')
                db.executemany('INSERT INTO cases VALUES (?,?,?,?,?,?,?,?)', rows)
                total += count
                db.commit()
            if total != self.total:
                raise ValueError('Published case index does not match the release case count')
            db.executescript("""
                CREATE INDEX by_snapshot ON cases(snapshot, case_id);
                CREATE INDEX by_pattern ON cases(pattern_type, case_id, snapshot);
                CREATE INDEX by_snapshot_pattern ON cases(snapshot, pattern_type, case_id);
            """)

    def queue(self, snapshot, pattern, page=None):
        if page is None and not pattern:
            return self.total if snapshot is None else self.snapshots[snapshot]['case_count']
        conditions, args = [], []
        if snapshot is not None:
            conditions.append('snapshot = ?')
            args.append(snapshot)
        if pattern:
            conditions.append('pattern_type = ?')
            args.append(pattern)
        where = ' WHERE ' + ' AND '.join(conditions) if conditions else ''
        with closing(sqlite3.connect(self.path.as_uri() + '?mode=ro', uri=True)) as db:
            if page is None:
                return db.execute('SELECT count(*) FROM cases' + where, args).fetchone()[0]
            db.row_factory = sqlite3.Row
            sql = 'SELECT * FROM cases' + where + ' ORDER BY case_id, snapshot LIMIT ? OFFSET ?'
            return [dict(row) for row in db.execute(sql, (*args, PAGE_SIZE, (page - 1) * PAGE_SIZE))]


if __name__ == '__main__':
    import boto3
    from pipeline.release import ACCOUNT, REGION, load_current

    session = boto3.Session(region_name=REGION)
    if session.client('sts').get_caller_identity()['Account'] != ACCOUNT:
        raise ValueError('Wrong AWS project account')
    client = session.client('s3')
    release = load_current(client)
    index = CaseCatalog(client, release)
    print(f"{release['release_id']}: {index.total:,} cases across {len(index.snapshots)} snapshots")
