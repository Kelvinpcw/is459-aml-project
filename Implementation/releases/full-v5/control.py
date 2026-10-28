"""Trusted manifest/catalog/publication stages, run under the reviewed gate role."""
import argparse,json,hashlib
from pipeline.release import BUCKET,REGION,validate_candidate,check_outputs,publish
from make_q2_input_manifest import make_manifest


def paths(run):
    suffix=f'dataset_version=ibm-hi-medium-b1b99c68b765580f/run_id={run}/'
    return {'preparation':'quality/preparation/'+suffix+'report.json',
      'q1':'quality/q1/'+suffix+'analysis_id=q1-full-v1/report.json',
      'q2':'quality/q2/'+suffix+'analysis_id=q2-full-v2/report.json',
      'evaluation':'quality/evaluation/'+suffix+'analysis_id=q2-full-v2/evaluation_id=eval-full-v2/report.json',
      'manifest':'manifests/detector-inputs/'+suffix+'manifest.json'}


def report_keys(run,overrides):
    import re
    from pipeline.release import split_uri,safe_id
    safe_id(run)
    keys=paths(run)
    for stage,uri in overrides.items():
        if stage not in ('q1','q2','evaluation'):raise ValueError('Unsupported report override')
        if uri:
            bucket,key=split_uri(uri)
            prefix=keys[stage].rsplit('/',1)[0]+'/attempt='
            if not key.startswith(prefix) or not re.fullmatch(r'[A-Za-z0-9_-]{1,100}/report\.json',key[len(prefix):]):
                raise ValueError('Recovery report escapes the original analysis/evaluation')
            keys[stage]=key
    return keys


def hive_type(kind):
    if isinstance(kind,dict) and kind['type']=='array':return 'array<'+hive_type(kind['elementType'])+'>'
    if isinstance(kind,str):return {'long':'bigint','integer':'int'}.get(kind,kind)
    raise ValueError('Unsupported catalog type')


def register(glue,name,location,columns,partition,values):
    storage={'Columns':columns,'Location':location,'InputFormat':'org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat',
       'OutputFormat':'org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat',
       'SerdeInfo':{'SerializationLibrary':'org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe','Parameters':{'serialization.format':'1'}}}
    # Only a new attempt-specific table may be created; do not overwrite a shared table.
    glue.create_table(DatabaseName='is459_aml_full',TableInput={'Name':name,'TableType':'EXTERNAL_TABLE','StorageDescriptor':storage,
        'PartitionKeys':[{'Name':partition,'Type':'date'}],'Parameters':{'classification':'parquet','EXTERNAL':'TRUE'}})
    partitions=[{'Values':[v],'StorageDescriptor':{**storage,'Location':location+partition+'='+v+'/'}} for v in sorted(set(values))]
    for i in range(0,len(partitions),100):
        response=glue.batch_create_partition(DatabaseName='is459_aml_full',TableName=name,PartitionInputList=partitions[i:i+100])
        if response.get('Errors'):raise ValueError('Catalog partition registration incomplete: '+str(response['Errors']))


def main():
    import boto3
    p=argparse.ArgumentParser()
    p.add_argument('--phase',choices=['manifests','catalog','publish'],required=True)
    p.add_argument('--run-id',required=True);p.add_argument('--release-id',required=True)
    p.add_argument('--q1-report');p.add_argument('--q2-report');p.add_argument('--evaluation-report');
    p.add_argument('--expected-pointer-etag');args,_=p.parse_known_args()
    from pipeline.release import safe_id
    safe_id(args.run_id);safe_id(args.release_id)
    session=boto3.Session(region_name=REGION);s3=session.client('s3');glue=session.client('glue')
    keys=report_keys(args.run_id,{'q1':args.q1_report,'q2':args.q2_report,'evaluation':args.evaluation_report})
    raw={};reports={}
    def read(stage):
        body=s3.get_object(Bucket=BUCKET,Key=keys[stage])['Body'].read(5_000_001)
        if len(body)>5_000_000:raise ValueError('Metadata exceeds bound')
        raw[stage]=body;reports[stage]=json.loads(body)
        if reports[stage]['status']!='PASSED':raise ValueError('Required stage did not pass')
        return reports[stage]
    prep=read('preparation')
    if args.phase=='manifests':
        body=(json.dumps(make_manifest(prep),indent=2)+'\n').encode()
        s3.put_object(Bucket=BUCKET,Key=keys['manifest'],Body=body,IfNoneMatch='*',ContentType='application/json')
    elif args.phase=='catalog':
        q1=read('q1');q2=read('q2');table_suffix=args.run_id.replace('-','_')
        cols=[{'Name':n,'Type':'string'} for n in ['dataset_version','run_id','sender_bank','receiver_bank','payment_format','payment_currency','receiving_currency']]
        cols += [{'Name':'transaction_count','Type':'bigint'},{'Name':'laundering_count','Type':'bigint'},{'Name':'amount_paid_total','Type':'decimal(38,8)'},{'Name':'amount_received_total','Type':'decimal(38,8)'}]
        register(glue,'q1_'+table_suffix,q1['outputs']['daily_counts'],cols,'event_date',prep['source_manifest']['selected_dates'])
        cols=[{'Name':c['name'],'Type':hive_type(c['type'])} for c in q2['case_index_schema']['fields'] if c['name']!='window_date']
        register(glue,'q2_'+table_suffix,q2['outputs']['case_index'],cols,'window_date',[r['window_start'][:10] for r in q2['snapshots']])
    else:
        for stage in ('q1','q2','evaluation'):read(stage)
        suffix=args.run_id.replace('-','_')
        candidate={'schema_version':1,'release_id':args.release_id,'release_kind':'full',
          'reports':{stage:{'uri':f's3://{BUCKET}/{keys[stage]}','sha256':hashlib.sha256(body).hexdigest()} for stage,body in raw.items()},
          'catalog':{'database':'is459_aml_full','q1_table':'q1_'+suffix,'q2_table':'q2_'+suffix}}
        release=validate_candidate(candidate,reports);check_outputs(s3,glue,release,reports)
        print(json.dumps(publish(s3,release,args.expected_pointer_etag)))

if __name__=='__main__':main()
