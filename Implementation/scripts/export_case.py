"""Download complete case evidence, including exports larger than the UI limit."""
import argparse,json,re,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from pipeline.release import ACCOUNT,REGION,BUCKET,load_current,read_object,sha,safe_id
from dashboard.data import get_case,evidence_csv,find_case_query,run_query,read_evidence_part


def main():
    import boto3
    p=argparse.ArgumentParser()
    p.add_argument('--profile',required=True);p.add_argument('--region',default=REGION)
    p.add_argument('--case-id',required=True);p.add_argument('--release-id');p.add_argument('--output',type=Path,required=True)
    args=p.parse_args()
    if not re.fullmatch(r'[a-f0-9]{64}',args.case_id):raise ValueError('Require the complete case ID')
    session=boto3.Session(profile_name=args.profile,region_name=args.region)
    if args.region!=REGION or session.client('sts').get_caller_identity()['Account']!=ACCOUNT:raise ValueError('Wrong project account/region')
    s3=session.client('s3')
    release=(json.loads(read_object(s3,f's3://{BUCKET}/published/releases/{safe_id(args.release_id)}/manifest.json')) if args.release_id else load_current(s3))
    if release['q2'].get('case_bundle_schema_version')==3:
        rows=run_query(session.client('athena'),find_case_query(release,args.case_id),max_rows=1)
        if len(rows)!=1:raise ValueError('Case is not present in this pinned release')
        row=rows[0]
    else:row={'case_id':args.case_id,'bundle_uri':release['q2']['bundles']+args.case_id+'.json'}
    case,raw=get_case(s3,release,row)
    args.output.mkdir(parents=True,exist_ok=False)
    (args.output/'case.json').write_bytes(raw)
    if case.get('schema_version',1)>=2:
        rows=0;cache={}
        for number,part in enumerate(case['evidence_parts']):
            body=read_evidence_part(s3,part,cache)
            if sha(body)!=part['sha256'] or len(body)!=part['bytes']:raise ValueError('Evidence artifact changed; export is incomplete')
            (args.output/f'part-{number:06d}.jsonl').write_bytes(body);rows+=len(body.splitlines())
        if rows!=case['evidence_transaction_count']:raise ValueError('Complete evidence row count differs')
    else:(args.output/'transactions.csv').write_text(evidence_csv(case))
    (args.output/'EXPORT_COMPLETE.json').write_text(json.dumps({'release_id':release['release_id'],'case_id':args.case_id,'transactions':case['evidence_transaction_count']},indent=2)+'\n')
    print('Complete evidence exported to '+str(args.output))

if __name__=='__main__':main()
