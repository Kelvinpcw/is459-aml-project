"""Deploy/start the diagnosed recovery once; no new IAM grants or full re-run."""
import argparse,hashlib,json,datetime,subprocess,uuid
from pathlib import Path
import boto3
from botocore.exceptions import ClientError
from build_stack import ACCOUNT,REGION,BUCKET
from deploy import save,ROOT,REV,STACK


def main():
    p=argparse.ArgumentParser();p.add_argument('--profile',required=True);p.add_argument('--phase',required=True,choices=['upload','update','status','start']);args=p.parse_args()
    subprocess.run(['bash','Implementation/scripts/check_aws_profile.sh',args.profile],cwd=ROOT,check=True)
    s=boto3.Session(profile_name=args.profile,region_name=REGION)
    if s.client('sts').get_caller_identity()['Account']!=ACCOUNT:raise ValueError('Wrong project account')
    s3=s.client('s3');cfn=s.client('cloudformation');sf=s.client('stepfunctions');glue=s.client('glue')
    if args.phase=='upload':
        release=ROOT/'Implementation/releases/full-v2';manifest=json.loads((release/'manifest.json').read_text())
        for name,ref in manifest['files'].items():
            body=(release/name).read_bytes()
            if hashlib.sha256(body).hexdigest()!=ref['sha256']:raise ValueError('Frozen recovery payload changed')
            try:s3.put_object(Bucket=BUCKET,Key=ref['s3_key'],Body=body,IfNoneMatch='*',Metadata={'sha256':ref['sha256']},ServerSideEncryption='AES256')
            except ClientError as e:
                if e.response['Error']['Code'] not in ('PreconditionFailed','412'):raise
            actual=s3.get_object(Bucket=BUCKET,Key=ref['s3_key'])['Body'].read()
            if hashlib.sha256(actual).hexdigest()!=ref['sha256']:raise ValueError('Conflicting uploaded recovery payload')
        save('full-recovery1-code-upload.json',{'manifest':manifest,'git_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()})
        print('New recovery objects uploaded and downloaded for SHA256 verification; old full-v1 unchanged.')
    elif args.phase=='update':
        proposed=json.loads((ROOT/'Implementation/deployment/recovery1-stack.json').read_text());original=json.loads((ROOT/'Implementation/deployment/full-pipeline-stack.json').read_text())
        actual=cfn.get_template(StackName=STACK,TemplateStage='Original')['TemplateBody']
        if isinstance(actual,str):actual=json.loads(actual)
        if actual!=original:raise ValueError('Stack changed since reviewed initial deployment; inspect before updating')
        for key,value in original['Resources'].items():
            if value['Type']=='AWS::IAM::Role' and proposed['Resources'][key]!=value:raise ValueError('Recovery would change IAM grants')
        for stage in ('prepare','risk','detect','evaluate','control'):
            if any(r['JobRunState'] in ('STARTING','RUNNING','WAITING','STOPPING') for r in glue.get_job_runs(JobName='is459-aml-full-'+stage)['JobRuns']):raise ValueError('Do not update running jobs')
        response=cfn.update_stack(StackName=STACK,TemplateBody=json.dumps(proposed),Capabilities=['CAPABILITY_NAMED_IAM'],Parameters=[{'ParameterKey':k,'UsePreviousValue':True} for k in ('CodeVersion','RunId','ReleaseId')],ClientRequestToken=str(uuid.uuid4()))
        save('full-recovery1-stack-update.json',{'response':response,'all_six_iam_resources_unchanged':True,'template_sha256':hashlib.sha256((ROOT/'Implementation/deployment/recovery1-stack.json').read_bytes()).hexdigest()});print(json.dumps(response))
    elif args.phase=='status':
        stack=cfn.describe_stacks(StackName=STACK)['Stacks'][0];save('full-recovery1-stack-status.json',stack);print(stack['StackStatus'])
    else:
        if (REV/'full-recovery1-request.json').exists() or (REV/'full-recovery1-start.json').exists():raise ValueError('Recovery already requested; inspect instead of starting again')
        stack=cfn.describe_stacks(StackName=STACK)['Stacks'][0]
        if stack['StackStatus']!='UPDATE_COMPLETE':raise ValueError('Wait for verified stack update')
        monitor=json.loads((REV/'full-monitor-latest.json').read_text())
        if monitor['active_paid_resources']:raise ValueError('Previous attempt still active')
        # New remaining timeout estimate: Q1 + Q2 + evaluation + two controls.
        maximum=monitor['prior_compute_estimate_usd']+monitor['full_compute_estimate_usd']+1.65+8.8+1.65+.293334+10+1
        if maximum>=28:raise ValueError('Recovery cannot fit conservative remaining budget')
        prep='quality/preparation/dataset_version=ibm-hi-medium-b1b99c68b765580f/run_id=full-20261028-v1/report.json'
        if json.loads(s3.get_object(Bucket=BUCKET,Key=prep)['Body'].read())['status']!='PASSED':raise ValueError('Reusable preparation did not pass')
        current=s3.get_object(Bucket=BUCKET,Key='published/current.json')
        if json.loads(current['Body'].read())['release_id']!='pilot-20220901-m00-v1':raise ValueError('Prior publication changed; inspect before recovery')
        arn=next(x['OutputValue'] for x in stack['Outputs'] if x['OutputKey']=='RecoveryWorkflowArn')
        body={'expected_pointer_etag':current['ETag'],'total_budget_usd':30}
        save('full-recovery1-request.json',{'state_machine':arn,'name':'full-20261028-recovery1','input':body,'conservative_total_estimate_usd':maximum,'preparation_reused':True,'frozen_detection_settings_unchanged':True})
        result=sf.start_execution(stateMachineArn=arn,name='full-20261028-recovery1',input=json.dumps(body));save('full-recovery1-start.json',result);print(json.dumps(result,default=str))

if __name__=='__main__':main()
