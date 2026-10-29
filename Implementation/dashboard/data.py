"""Pinned-release SQL and bounded, cancellable Athena reads."""
from __future__ import annotations
import csv,io,json,re,time,uuid,os
from datetime import date
from decimal import Decimal
from pipeline.release import BUCKET,REGION,read_object,sha


def literal(value):
    if not isinstance(value,str) or len(value)>200 or any(ord(c)<32 for c in value):
        raise ValueError('Invalid filter value')
    return "'"+value.replace("'","''")+"'"


def table(release,key):
    values=[release['catalog']['database'],release['catalog'][key]]
    if any(not re.fullmatch(r'[a-z][a-z0-9_]{0,127}',x) for x in values):raise ValueError('Invalid table')
    return '.'.join(values)


def q1_query(release,start,end,currency,side='payment',grain='format',payment_format=None,min_support=1000):
    if side not in ('payment','receiving') or grain not in ('format','bank_pair','segment'):
        raise ValueError('Invalid view')
    start,end=date.fromisoformat(start),date.fromisoformat(end)
    dates=[date.fromisoformat(x) for x in release['q1']['dates']]
    if not min(dates)<=start<=end<=max(dates):raise ValueError('Date filter outside published scope')
    if not isinstance(min_support,int) or not 1<=min_support<=1000000:raise ValueError('Invalid support')
    group={'format':['payment_format'],'bank_pair':['sender_bank','receiver_bank'],
           'segment':['sender_bank','receiver_bank','payment_format']}[grain]
    cols=', '.join(group)
    filters=[f'dataset_version={literal(release["dataset_version"])}',f'run_id={literal(release["run_id"])}',
             f"event_date BETWEEN DATE '{start}' AND DATE '{end}'",f'{side}_currency={literal(currency)}']
    if payment_format:filters.append('payment_format='+literal(payment_format))
    # Only sum the monetary side whose currency is fixed; the other side may mix units.
    amount='amount_paid_total' if side=='payment' else 'amount_received_total'
    return f'''WITH selected AS (SELECT * FROM {table(release,'q1_table')} WHERE {' AND '.join(filters)}),
    baseline AS (SELECT SUM(transaction_count) baseline_n,SUM(laundering_count) baseline_l FROM selected),
    grouped_segments AS (SELECT {cols},SUM(transaction_count) n,SUM(laundering_count) l,
    SUM({amount}) selected_currency_amount FROM selected GROUP BY {cols})
    SELECT g.*,b.baseline_n,b.baseline_l,CAST(g.l AS DOUBLE)/NULLIF(g.n,0) rate,
    (CAST(g.l AS DOUBLE)/NULLIF(g.n,0))/NULLIF(CAST(b.baseline_l AS DOUBLE)/NULLIF(b.baseline_n,0),0) lift,
    CASE WHEN g.n>={min_support} THEN 'supported' ELSE 'low_support' END support
    FROM grouped_segments g CROSS JOIN baseline b ORDER BY CASE WHEN g.n>={min_support} THEN 0 ELSE 1 END, CASE WHEN g.n>={min_support} THEN lift ELSE NULL END DESC,n DESC,{cols} LIMIT 500'''


def q1_trend_query(release,start,end,currency,side='payment',payment_format=None):
    """Daily additive counts from the common Q1 base, never ranked/top-N rows."""
    if side not in ('payment','receiving'):raise ValueError('Invalid currency side')
    start,end=date.fromisoformat(start),date.fromisoformat(end)
    dates=[date.fromisoformat(x) for x in release['q1']['dates']]
    if not min(dates)<=start<=end<=max(dates):raise ValueError('Date filter outside published scope')
    if (end-start).days>=500:raise ValueError('Trend exceeds the bounded display window')
    filters=[f'dataset_version={literal(release["dataset_version"])}',f'run_id={literal(release["run_id"])}',
             f"event_date BETWEEN DATE '{start}' AND DATE '{end}'",f'{side}_currency={literal(currency)}']
    if payment_format:filters.append('payment_format='+literal(payment_format))
    return f"SELECT event_date,SUM(transaction_count) n,SUM(laundering_count) l FROM {table(release,'q1_table')} WHERE {' AND '.join(filters)} GROUP BY event_date ORDER BY event_date"


def case_query(release,pattern=None,limit=200):
    if not isinstance(limit,int) or not 1<=limit<=500:raise ValueError('Invalid display limit')
    where=[f'dataset_version={literal(release["dataset_version"])}',f'run_id={literal(release["run_id"])}',
           f'analysis_id={literal(release["q2"]["analysis_id"])}',
           f"window_date=DATE '{date.fromisoformat(release['q2']['window_start'][:10])}'",
           f"window_end=TIMESTAMP {literal(release['q2']['window_end'].replace('T',' '))}"]
    if pattern:
        if pattern not in ('fan_in','fan_out','cycle_2','cycle_3','cycle_4'):raise ValueError('Invalid pattern')
        where.append('pattern_type='+literal(pattern))
    return f"SELECT * FROM {table(release,'q2_table')} WHERE {' AND '.join(where)} ORDER BY case_id LIMIT {limit}"


def run_query(athena,query,timeout=30,max_rows=500,sleep=time.sleep):
    workgroup=os.environ.get('AML_ATHENA_WORKGROUP','is459-aml-dev')
    if workgroup not in ('is459-aml-dev','is459-aml-dashboard'):raise ValueError('Unexpected project workgroup')
    request=athena.start_query_execution(QueryString=query,WorkGroup=workgroup,ClientRequestToken=str(uuid.uuid4()))
    qid=request['QueryExecutionId']
    print(json.dumps({'aml_query_id':qid,'workgroup':workgroup}),flush=True)
    deadline=time.monotonic()+timeout
    while True:
        status=athena.get_query_execution(QueryExecutionId=qid)['QueryExecution']['Status']
        if status['State']=='SUCCEEDED':break
        if status['State'] in ('FAILED','CANCELLED'):raise RuntimeError(status.get('StateChangeReason','Query failed'))
        if time.monotonic()>=deadline:
            athena.stop_query_execution(QueryExecutionId=qid)
            raise TimeoutError('Query timed out and cancellation was requested')
        sleep(.4)
    rows=[];headers=None;token=None
    while True:
        response=athena.get_query_results(QueryExecutionId=qid,MaxResults=min(max_rows+1,1000),**({'NextToken':token} if token else {}))
        for row in response['ResultSet']['Rows']:
            values=[c.get('VarCharValue') for c in row['Data']]
            if headers is None:headers=values;continue
            rows.append(dict(zip(headers,values)))
            if len(rows)>max_rows:raise ValueError('Query output exceeds display bound')
        token=response.get('NextToken')
        if not token:break
    return rows


def shard_member(raw,member,max_bytes=8_000_000):
    import zipfile
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        if z.namelist().count(member)!=1:raise ValueError('Missing or duplicate shard member')
        info=z.getinfo(member)
        if info.file_size>max_bytes:raise ValueError('Shard member exceeds bound')
        return z.read(info)


def read_evidence_part(s3,part,cache=None):
    cache={} if cache is None else cache
    if part.get('member'):
        uri=part['uri']
        if uri not in cache:
            cache.clear();cache[uri]=read_object(s3,uri)
        body=shard_member(cache[uri],part['member'])
    else:body=read_object(s3,part['uri'])
    if len(body)!=part['bytes'] or sha(body)!=part['sha256']:raise ValueError('Evidence chunk changed')
    return body


def get_case(s3,release,row):
    sharded=bool(row.get('bundle_member'))
    if sharded:
        prefix=release['q2']['bundles']+'shards/'
        if not row['bundle_uri'].startswith(prefix) or not re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}/partition-[0-9]{5}-[0-9]{6}\.zip',row['bundle_uri'][len(prefix):]):raise ValueError('Shard URI escapes pinned release')
        if row['bundle_member']!=row['case_id']+'.json':raise ValueError('Wrong case shard member')
        raw=shard_member(read_object(s3,row['bundle_uri']),row['bundle_member'])
        if sha(raw)!=row['bundle_sha256']:raise ValueError('Case header changed')
    else:
        expected=release['q2']['bundles']+row['case_id']+'.json'
        if row['bundle_uri']!=expected:raise ValueError('Case URI is not in the pinned release')
        raw=read_object(s3,expected)
    case=json.loads(raw)
    for k,value in (('dataset_version',release['dataset_version']),('run_id',release['run_id']),
                    ('analysis_id',release['q2']['analysis_id']),('case_id',row['case_id'])):
        if case[k]!=value:raise ValueError('Case identity differs from pinned release')
    version=case.get('schema_version',1)
    if version not in (1,2,3) or sharded!=(version==3):raise ValueError('Unknown case storage contract')
    count=sum(p['rows'] for p in case['evidence_parts']) if version>=2 else len(case['transactions'])
    if version>=2:
        prefix=release['q2']['bundles'].replace('/bundles/','/evidence/')+row['case_id']+'/'
        for part in case['evidence_parts']:
            if version==3:
                root=release['q2']['bundles']+'shards/'
                if not part['uri'].startswith(root) or not re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}/partition-[0-9]{5}-[0-9]{6}\.zip',part['uri'][len(root):]):raise ValueError('Evidence shard escapes pinned release')
                if not re.fullmatch('evidence/'+re.escape(row['case_id'])+r'/part-[0-9]{6}\.jsonl',part.get('member','')):raise ValueError('Evidence member escapes pinned case')
            elif not part['uri'].startswith(prefix) or not re.fullmatch(r'part-[0-9]{6}\.jsonl',part['uri'][len(prefix):]):raise ValueError('Evidence URI escapes pinned case')
    if count!=case['evidence_transaction_count']:raise ValueError('Case evidence is incomplete')
    return case,raw


def evidence_csv(case):
    output=io.StringIO();rows=case['transactions']
    if not rows:return ''
    writer=csv.DictWriter(output,fieldnames=list(rows[0]));writer.writeheader()
    # Spreadsheet formula escaping; retain exact source evidence in the JSON export.
    for row in rows:
        writer.writerow({k:("'"+v if isinstance(v,str) and v.startswith(('=','+','-','@')) else v) for k,v in row.items()})
    return output.getvalue()


def wilson(l,n):
    if n<=0:return None,None
    z=1.959963984540054;p=l/n;d=1+z*z/n
    center=(p+z*z/(2*n))/d;half=z*((p*(1-p)/n+z*z/(4*n*n))**.5)/d
    return max(0,center-half),min(1,center+half)


def dimension_query(release,side):
    if side not in ('payment','receiving'):raise ValueError('Invalid currency side')
    return f"SELECT DISTINCT {side}_currency AS currency FROM {table(release,'q1_table')} WHERE dataset_version={literal(release['dataset_version'])} AND run_id={literal(release['run_id'])} ORDER BY currency"


def full_evidence_archive(s3,case,max_bytes=50_000_000):
    import zipfile
    parts=case.get('evidence_parts')
    if parts is None:return None
    if sum(p['bytes'] for p in parts)>max_bytes:
        raise ValueError('This export exceeds the in-app download size. Use the complete evidence manifest with the export CLI; no evidence is truncated.')
    output=io.BytesIO();cache={}
    with zipfile.ZipFile(output,'w',compression=zipfile.ZIP_DEFLATED) as archive:
        for i,part in enumerate(parts):
            raw=read_evidence_part(s3,part,cache)
            archive.writestr(f'part-{i:06d}.jsonl',raw)
        archive.writestr('manifest.json',json.dumps(case,indent=2))
    return output.getvalue()


def find_case_query(release,case_id):
    if not re.fullmatch(r'[a-f0-9]{64}',case_id):raise ValueError('Require full case ID')
    return f"SELECT * FROM {table(release,'q2_table')} WHERE dataset_version={literal(release['dataset_version'])} AND run_id={literal(release['run_id'])} AND analysis_id={literal(release['q2']['analysis_id'])} AND case_id={literal(case_id)} LIMIT 1"
