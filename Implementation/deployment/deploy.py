"""Explicit-profile deployment driver. Each phase is deliberate and auditable."""
import argparse,datetime,hashlib,json,subprocess,uuid,re
from pathlib import Path
import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
from build_stack import ACCOUNT,REGION,BUCKET
ROOT=Path(__file__).resolve().parents[2];REV=ROOT/'Implementation/aws/reviews'
STACK='is459-aml-full-v1';DASHBOARD='is459-aml-dashboard-v1'


def save(name,value):
    def encoder(x):return x.isoformat() if isinstance(x,datetime.datetime) else str(x)
    (REV/name).write_text(json.dumps(value,indent=2,default=encoder)+'\n')


def main():
 p=argparse.ArgumentParser()
 p.add_argument('--profile',required=True);p.add_argument('--region',default=REGION)
 p.add_argument('--phase',required=True,choices=['upload','create','start','status','dashboard','dashboard-status','stop','remove-dashboard'])
 p.add_argument('--dashboard-template',choices=['dashboard-stack.json','dashboard-recovery1-stack.json'],default='dashboard-stack.json')
 p.add_argument('--code-version',default='full-v1')
 p.add_argument('--run-id',default='full-20261028-v1');p.add_argument('--release-id',default='full-20261028-v1')
 args=p.parse_args()
 if not re.fullmatch(r'full-v[1-9][0-9]*',args.code_version):raise ValueError('Invalid immutable code version')
 subprocess.run(['bash','Implementation/scripts/check_aws_profile.sh',args.profile],cwd=ROOT,check=True)
 session=boto3.Session(profile_name=args.profile,region_name=args.region)
 if args.region!=REGION or session.client('sts').get_caller_identity()['Account']!=ACCOUNT:raise ValueError('Wrong project account/region')
 s3=session.client('s3');cfn=session.client('cloudformation');glue=session.client('glue');sf=session.client('stepfunctions',config=Config(retries={'total_max_attempts':1}))
 if args.phase=='upload':
  release=ROOT/'Implementation/releases'/args.code_version;manifest=json.loads((release/'manifest.json').read_text())
  for name,ref in manifest['files'].items():
   body=(release/name).read_bytes()
   if hashlib.sha256(body).hexdigest()!=ref['sha256']:raise ValueError('Frozen code changed')
   try:s3.put_object(Bucket=BUCKET,Key=ref['s3_key'],Body=body,IfNoneMatch='*',Metadata={'sha256':ref['sha256']},ServerSideEncryption='AES256')
   except ClientError as e:
    if e.response['Error']['Code'] not in ('PreconditionFailed','412'):raise
    existing=s3.get_object(Bucket=BUCKET,Key=ref['s3_key'])['Body'].read()
    if hashlib.sha256(existing).hexdigest()!=ref['sha256']:raise ValueError('Conflicting immutable code object')
  save('full-code-upload.json',{'manifest':manifest,'git_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()})
  print('Frozen code objects uploaded/verified; no processing started.')
 elif args.phase=='create':
  body=(ROOT/'Implementation/deployment/full-pipeline-stack.json').read_text()
  result=cfn.create_stack(StackName=STACK,TemplateBody=body,Capabilities=['CAPABILITY_NAMED_IAM'],ClientRequestToken=str(uuid.uuid4()),Parameters=[{'ParameterKey':'CodeVersion','ParameterValue':args.code_version},{'ParameterKey':'RunId','ParameterValue':args.run_id},{'ParameterKey':'ReleaseId','ParameterValue':args.release_id}],OnFailure='DO_NOTHING',Tags=[{'Key':'Project','Value':'is459-aml'},{'Key':'BudgetUSD','Value':'30'}])
  save('full-stack-create.json',result);print(json.dumps(result))
 elif args.phase=='start':
  stack=cfn.describe_stacks(StackName=STACK)['Stacks'][0]
  if stack['StackStatus']!='CREATE_COMPLETE':raise ValueError('Wait for successful stack creation')
  arn=next(x['OutputValue'] for x in stack['Outputs'] if x['OutputKey']=='WorkflowArn')
  marker=REV/'full-workflow-start.json'
  if marker.exists() or (REV/'full-workflow-request.json').exists():raise ValueError('This execution has already been requested. Inspect instead of starting again.')
  current=s3.head_object(Bucket=BUCKET,Key='published/current.json')
  body=json.dumps({'expected_pointer_etag':current['ETag'],'total_budget_usd':30},sort_keys=True)
  save('full-workflow-request.json',{'execution_name':args.run_id,'state_machine':arn,'input':json.loads(body),'budget_authorization':'User explicitly approved US$30 final full-data ceiling on 28 October 2026.'})
  result=sf.start_execution(stateMachineArn=arn,name=args.run_id,input=body)
  save('full-workflow-start.json',result);print(json.dumps(result,default=str))
 elif args.phase=='status':
  result={'stack':cfn.describe_stacks(StackName=STACK)['Stacks'][0]}
  marker=REV/'full-workflow-start.json'
  if marker.exists():result['execution']=sf.describe_execution(executionArn=json.loads(marker.read_text())['executionArn'])
  result['jobs']={}
  for name in ['prepare','risk','detect','evaluate','control']:
   try:result['jobs'][name]=glue.get_job_runs(JobName='is459-aml-full-'+name)['JobRuns']
   except glue.exceptions.EntityNotFoundException:result['jobs'][name]=[]
  save('full-latest-status.json',result)
  print(json.dumps({'stack':result['stack']['StackStatus'],'execution':result.get('execution',{}).get('status'),'jobs':{k:[{'id':x['Id'],'state':x['JobRunState'],'seconds':x.get('ExecutionTime'),'error':x.get('ErrorMessage')} for x in v] for k,v in result['jobs'].items()}},default=str))
 elif args.phase=='dashboard':
  ec2=session.client('ec2');vpcs=ec2.describe_vpcs(Filters=[{'Name':'is-default','Values':['true']}])['Vpcs']
  if len(vpcs)!=1:raise ValueError('Select an authorised existing VPC; no new VPC/NAT is created automatically')
  vpc=vpcs[0]['VpcId'];subnets=ec2.describe_subnets(Filters=[{'Name':'vpc-id','Values':[vpc]},{'Name':'default-for-az','Values':['true']}])['Subnets']
  if not subnets:raise ValueError('No default public subnet is available')
  template=(ROOT/'Implementation/deployment'/args.dashboard_template).read_text()
  result=cfn.create_stack(StackName=DASHBOARD,TemplateBody=template,Capabilities=['CAPABILITY_NAMED_IAM'],ClientRequestToken=str(uuid.uuid4()),Parameters=[{'ParameterKey':'CodeVersion','ParameterValue':args.code_version},{'ParameterKey':'VpcId','ParameterValue':vpc},{'ParameterKey':'SubnetId','ParameterValue':subnets[0]['SubnetId']}],Tags=[{'Key':'Project','Value':'is459-aml'}],OnFailure='DO_NOTHING')
  save('dashboard-stack-create.json',result);print(json.dumps(result))
 elif args.phase=='dashboard-status':
  stack=cfn.describe_stacks(StackName=DASHBOARD)['Stacks'][0];save('dashboard-latest-status.json',stack)
  print(json.dumps({'status':stack['StackStatus'],'outputs':stack.get('Outputs',[])},default=str))
 elif args.phase=='remove-dashboard':
  result=cfn.delete_stack(StackName=DASHBOARD);save('dashboard-stack-delete-request.json',{'requested':True,'response':result});print('Dashboard stack deletion requested; verify terminal deletion before handoff.')
 elif args.phase=='stop':
  marker=REV/'full-workflow-start.json'
  if marker.exists():sf.stop_execution(executionArn=json.loads(marker.read_text())['executionArn'],cause='User project cleanup or budget control')
  stopped=[]
  for name in ['prepare','risk','detect','evaluate','control']:
   job='is459-aml-full-'+name
   active=[r['Id'] for r in glue.get_job_runs(JobName=job)['JobRuns'] if r['JobRunState'] in ('STARTING','RUNNING','WAITING','STOPPING')]
   if active:stopped.append(glue.batch_stop_job_run(JobName=job,JobRunIds=active))
  save('full-stop-request.json',{'responses':stopped});print('Stop requested for known full-project executions; verify terminal states.')

if __name__=='__main__':main()
