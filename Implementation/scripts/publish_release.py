"""Explicitly profiled CLI: validate all reports/outputs before atomic publication."""
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from pipeline.release import ACCOUNT,REGION,STAGES,verify_ref,validate_candidate,check_outputs,publish


def main():
    import boto3
    p=argparse.ArgumentParser()
    p.add_argument('--profile',required=True);p.add_argument('--region',default=REGION)
    p.add_argument('--candidate',type=Path,required=True);p.add_argument('--expected-pointer-etag')
    p.add_argument('--publish',action='store_true')
    args=p.parse_args()
    session=boto3.Session(profile_name=args.profile,region_name=args.region)
    if args.region!=REGION or session.client('sts').get_caller_identity()['Account']!=ACCOUNT:
        raise ValueError('Wrong project account/region')
    candidate=json.loads(args.candidate.read_text());s3=session.client('s3')
    reports={stage:verify_ref(s3,candidate['reports'][stage]) for stage in STAGES}
    release=validate_candidate(candidate,reports)
    check_outputs(s3,session.client('glue'),release,reports)
    if args.publish: print(json.dumps(publish(s3,release,args.expected_pointer_etag),indent=2))
    else:print(json.dumps({'validated_release':release,'published':False},indent=2))

if __name__=='__main__':main()
