"""Validate immutable stage reports and atomically publish one consistent release."""
from __future__ import annotations
import hashlib
import json
import re
from datetime import date, datetime, timezone,timedelta
from urllib.parse import urlparse

ACCOUNT = '160885259244'
REGION = 'us-east-1'
BUCKET = 'is459-aml-g2team7-160885259244-us-east-1'
STAGES = ('preparation', 'q1', 'q2', 'evaluation')


def encoded(value):
    return (json.dumps(value, sort_keys=True, indent=2) + '\n').encode()


def sha(body):
    return hashlib.sha256(body).hexdigest()


def safe_id(value):
    if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,100}', value):
        raise ValueError('Invalid identifier')
    return value


def split_uri(uri):
    p = urlparse(uri)
    if p.scheme != 's3' or p.netloc != BUCKET or not p.path.strip('/') or p.query or p.fragment:
        raise ValueError('Require an explicit unsigned project S3 URI')
    if any(x in ('.', '..') for x in p.path.split('/')):
        raise ValueError('Unsafe S3 path')
    return p.netloc, p.path.lstrip('/')


def read_object(s3, uri, limit=10_000_000):
    bucket, key = split_uri(uri)
    response = s3.get_object(Bucket=bucket, Key=key)
    try:
        body = response['Body'].read(limit + 1)
    finally:
        response['Body'].close()
    if len(body) > limit:
        raise ValueError('Object exceeds the declared read bound')
    return body


def verify_ref(s3, ref):
    body = read_object(s3, ref['uri'])
    if sha(body) != ref['sha256']:
        raise ValueError('Pinned artifact bytes changed')
    return json.loads(body)


def validate_candidate(candidate, reports):
    if candidate.get('schema_version') != 1 or candidate.get('release_kind') not in ('pilot', 'full'):
        raise ValueError('Unknown release contract')
    safe_id(candidate['release_id'])
    if set(reports) != set(STAGES) or set(candidate['reports']) != set(STAGES):
        raise ValueError('Every required stage must be present')
    prep, q1, q2, evaluation = (reports[s] for s in STAGES)
    for stage, report in reports.items():
        if report.get('stage') != stage or report.get('status') != 'PASSED':
            raise ValueError('A required stage failed or is incomplete')
    identity = (prep['dataset_version'], prep['run_id'])
    safe_id(identity[0]); safe_id(identity[1])
    for report in (q1, q2.get('config', q2), evaluation):
        if (report.get('dataset_version'), report.get('run_id')) != identity:
            raise ValueError('Stage dataset/preparation identities disagree')
    if not prep.get('label_separation_passed') or prep.get('quarantined_rows') != 0:
        raise ValueError('Preparation completeness/separation gate failed')
    if not prep.get('source_reference_reconciliation_passed') or prep['accepted_rows'] != prep['input_rows']:
        raise ValueError('Preparation population does not reconcile')
    if q1['totals']['transactions'] != prep['accepted_rows'] or evaluation['full_prepared_rows_reconciled'] != prep['accepted_rows']:
        raise ValueError('Branch/evaluation populations differ')
    positives = sum(x['labelled_laundering'] for x in prep['accepted_by_format'])
    if q1['totals']['labelled_laundering'] != positives:
        raise ValueError('Q1 labels do not reconcile')
    if q2.get('detector_received_labels') is not False:
        raise ValueError('Q2 input separation is not established')
    stats = q2['statistics']
    if not stats.get('complete_for_declared_window') or stats.get('truncated') is not False:
        raise ValueError('Partial/truncated detection cannot publish')
    if evaluation['detector_analysis_id'] != q2['config']['analysis_id'] or evaluation['case_count'] != stats['case_count']:
        raise ValueError('Evaluation does not belong to the selected detection')
    if evaluation['eligible_transactions'] != stats['scoped_rows']:
        raise ValueError('Evaluator eligible population differs from detection scope')
    suffix = f'dataset_version={identity[0]}/run_id={identity[1]}/'
    expected = {'q1': 'gold/risk/'+suffix+'analysis_id='+q1['analysis_id']+'/',
                'q2': 'gold/cases/'+suffix+'analysis_id='+q2['config']['analysis_id']+'/'}
    for stage in ('q1', 'q2'):
        for uri in reports[stage]['outputs'].values():
            _, key = split_uri(uri)
            if not key.startswith(expected[stage]):
                raise ValueError('Output URI escapes selected analysis')
    catalog = candidate['catalog']
    for value in catalog.values():
        if not re.fullmatch(r'[a-z][a-z0-9_]{0,127}', value):
            raise ValueError('Invalid catalog identifier')
    if set(catalog) != {'database', 'q1_table', 'q2_table'}:
        raise ValueError('Require explicit immutable Catalog tables')
    dates = sorted(prep['source_manifest']['selected_dates'])
    if not dates:
        raise ValueError('No reporting dates')
    for value in dates: date.fromisoformat(value)
    config = q2['config']
    start, end, cutoff = (datetime.fromisoformat(config[k]) for k in ('window_start','window_end','snapshot_cutoff'))
    if not start < end or not start <= cutoff <= end :
        raise ValueError('Invalid detection scope')
    if end.date()<date.fromisoformat(dates[0]) or start.date()>date.fromisoformat(dates[-1]):raise ValueError('Detection does not overlap prepared dates')
    warnings = []
    if candidate['release_kind'] == 'pilot':
        warnings.append('Development pilot: Q1 and Q2 have the separate scopes shown; this is not a full-data release.')
    else:
        counts = prep['source_manifest']['counts']
        if counts['selected_records'] != counts['source_records'] or counts['outside_development_scope'] != 0:
            raise ValueError('A full release requires complete source accounting')
        if not q2.get('distributed_processing') or not evaluation.get('frozen_calibration_sha256'):
            raise ValueError('Full release requires distributed detection and frozen calibration evidence')
        if not evaluation.get('holdout_evaluation_complete'):
            raise ValueError('Full release requires completed eligible-population holdout evaluation')
        ends={(date.fromisoformat(d)+timedelta(days=1)).isoformat()+'T00:00:00' for d in dates}
        snapshots=q2.get('snapshots',[])
        if len(snapshots)!=len(ends) or {x['window_end'] for x in snapshots}!=ends:raise ValueError('Full release requires every declared daily snapshot')
        if evaluation['eligible_positive_labels']!=positives:raise ValueError('Full evaluation positive counts do not reconcile')
    if q2.get('snapshots') and any(x.get('cycle_excluded_nodes_above_degree',0) for x in q2['snapshots']):
        warnings.append('Cycle detection excludes nodes above its declared degree threshold; see snapshot coverage. Fan evidence remains complete.')
    if evaluation.get('eligible_positive_labels', 0) == 0:
        warnings.append('No positive labels in this detector window: recall and lift are not measurable.')
    if evaluation.get('eligible_annotated_attempts', 0) == 0:
        warnings.append('No eligible annotated attempts: recovery is not measurable. Unannotated cases are not proven false.')
    return {'schema_version': 1, 'release_id': candidate['release_id'], 'release_kind': candidate['release_kind'],
            'dataset_version':identity[0], 'run_id':identity[1], 'reports':candidate['reports'], 'catalog':catalog,
            'q1':{'analysis_id':q1['analysis_id'],'dates':dates,'daily_counts':q1['outputs']['daily_counts']},
            'q2':{'analysis_id':config['analysis_id'],'window_start':config['window_start'],'window_end':config['window_end'],
                  'snapshot_cutoff':config['snapshot_cutoff'],'case_count':stats['case_count'], 'snapshots':q2.get('snapshots',[]),'case_bundle_schema_version':q2.get('case_bundle_schema_version',1), **q2['outputs']},
            'evaluation':{'evaluation_id':evaluation['evaluation_id'],'metrics':evaluation['artifacts']['metrics.json']},
            'timestamp_policy':prep['timestamp_policy'], 'warnings':warnings,
            'created_at_utc':datetime.now(timezone.utc).isoformat()}


def check_outputs(s3, glue, release, reports):
    for stage, table_key, path_key in (('q1','q1_table','daily_counts'),('q2','q2_table','case_index')):
        location = glue.get_table(DatabaseName=release['catalog']['database'], Name=release['catalog'][table_key])['Table']['StorageDescriptor']['Location']
        if location.rstrip('/') != reports[stage]['outputs'][path_key].rstrip('/'):
            raise ValueError('Catalog location differs from pinned release')
        uri = reports[stage]['outputs'][path_key].rstrip('/')+'/'
        bucket, key = split_uri(uri)
        # Glue's S3 committer need not emit _SUCCESS. Read the actual immutable
        # Parquet outputs and reconcile them against the pinned PASSED reports.
        import io
        import pyarrow.parquet as pq
        import pyarrow.compute as pc
        files=[]
        for page in s3.get_paginator('list_objects_v2').paginate(Bucket=bucket,Prefix=key):
            files.extend(x for x in page.get('Contents',[]) if x['Key'].endswith('.parquet'))
        total_rows=n=l=0
        for obj in files:
            if obj['Size']>512_000_000:raise ValueError('Parquet file exceeds release-verification bound')
            response=s3.get_object(Bucket=bucket,Key=obj['Key'],IfMatch=obj['ETag'])
            try:body=response['Body'].read(512_000_001)
            finally:response['Body'].close()
            if len(body)!=obj['Size']:raise ValueError('Parquet object changed while verifying')
            columns=['dataset_version','run_id']+(['transaction_count','laundering_count'] if stage=='q1' else ['analysis_id','case_id'])
            data=pq.ParquetFile(io.BytesIO(body)).read(columns=columns)
            total_rows+=data.num_rows
            for name,value in [('dataset_version',release['dataset_version']),('run_id',release['run_id'])]+([] if stage=='q1' else [('analysis_id',release['q2']['analysis_id'])]):
                if data[name].null_count or pc.any(pc.not_equal(data[name],value)).as_py():raise ValueError('Physical table contains a foreign identity')
            if stage=='q1':
                n+=pc.sum(data['transaction_count']).as_py() or 0
                l+=pc.sum(data['laundering_count']).as_py() or 0
        if stage=='q1' and (n,l)!=(reports['q1']['totals']['transactions'],reports['q1']['totals']['labelled_laundering']):
            raise ValueError('Physical Q1 counts differ from the completed report')
        if stage=='q2' and total_rows!=reports['q2']['statistics']['case_count']:
            raise ValueError('Physical case index population differs from completed detection')
    if release['release_kind']=='full':
        report=reports['evaluation'];calibration=verify_ref(s3,report['calibration'])
        if report['calibration']['sha256']!=report['frozen_calibration_sha256'] or calibration.get('frozen') is not True:raise ValueError('Calibration hash/freeze gate failed')
        if not calibration.get('development_analyses') or any(datetime.fromisoformat(x['window_end'])>datetime(2022,9,9) for x in calibration['development_analyses']):raise ValueError('Calibration includes holdout/future evidence')
        if calibration.get('recovery_improvement_target_pp')!=5:raise ValueError('Numerical improvement target was not frozen as reviewed')
    for ref in reports['evaluation']['artifacts'].values():
        body = read_object(s3, ref['uri'])
        if sha(body) != ref['sha256'] or len(body) != ref['bytes']:
            raise ValueError('Evaluator artifact differs from its passed report')


def publish(s3, release, expected_pointer_etag=None):
    """Immutable release first; CAS pointer last. Failure leaves prior pointer intact."""
    body = encoded(release)
    release_key = 'published/releases/'+safe_id(release['release_id'])+'/manifest.json'
    s3.put_object(Bucket=BUCKET, Key=release_key, Body=body, IfNoneMatch='*', ContentType='application/json', ServerSideEncryption='AES256')
    pointer = encoded({'schema_version':1,'release_id':release['release_id'], 'manifest_uri':'s3://'+BUCKET+'/'+release_key,'sha256':sha(body)})
    condition = {'IfMatch':expected_pointer_etag} if expected_pointer_etag else {'IfNoneMatch':'*'}
    s3.put_object(Bucket=BUCKET, Key='published/current.json', Body=pointer, ContentType='application/json', ServerSideEncryption='AES256', **condition)
    return json.loads(pointer)


def load_current(s3):
    """Read current once; every query thereafter uses this immutable snapshot."""
    pointer = json.loads(read_object(s3, 's3://'+BUCKET+'/published/current.json'))
    release = verify_ref(s3, {'uri':pointer['manifest_uri'],'sha256':pointer['sha256']})
    if release['release_id'] != pointer['release_id']:
        raise ValueError('Current pointer identity mismatch')
    return release
