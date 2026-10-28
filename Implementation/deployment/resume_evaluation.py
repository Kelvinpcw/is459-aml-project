"""Deliberate evaluator/publisher-only continuation. Never rerun completed stages."""
import argparse,datetime,hashlib,json,subprocess,uuid
from pathlib import Path
import boto3
from botocore.exceptions import ClientError
from deploy import ROOT,REV,STACK,save,execution_arns
from build_stack import ACCOUNT,REGION,BUCKET
from build_evaluation_resume import MAXIMUM_COMPUTE_USD
from build_lineage_evaluation import MAXIMUM_COMPUTE_USD as LINEAGE_COMPUTE_USD
ATTEMPTS={
 "evaluation-resume1":("full-v3","recovery1","EvaluationResumeWorkflow",MAXIMUM_COMPUTE_USD),
 "evaluation-keyed1":("full-v4","evaluation-resume1","KeyedEvaluationWorkflow",MAXIMUM_COMPUTE_USD),
 "evaluation-lineage1":("full-v5","evaluation-keyed1","LineageEvaluationWorkflow",LINEAGE_COMPUTE_USD),
}


def main():
 p=argparse.ArgumentParser();p.add_argument('--profile',required=True);p.add_argument('--attempt',choices=list(ATTEMPTS),default='evaluation-resume1');p.add_argument('--phase',required=True,choices=['upload','update','verify','start','status']);args=p.parse_args()
 subprocess.run(['bash','Implementation/scripts/check_aws_profile.sh',args.profile],cwd=ROOT,check=True)
 s=boto3.Session(profile_name=args.profile,region_name=REGION)
 if s.client('sts').get_caller_identity()['Account']!=ACCOUNT:raise ValueError('Wrong project account')
 cfn=s.client('cloudformation');s3=s.client('s3');sf=s.client('stepfunctions');glue=s.client('glue')
 attempt=args.attempt
 release_version,base_version,workflow_key,maximum_compute=ATTEMPTS[attempt]
 template_path=ROOT/('Implementation/deployment/'+attempt+'-stack.json');template=json.loads(template_path.read_text())
 base=json.loads((ROOT/('Implementation/deployment/'+base_version+'-stack.json')).read_text())
 for key,r in base['Resources'].items():
  if r['Type']=='AWS::IAM::Role' and template['Resources'][key]!=r:raise ValueError('Changed IAM grant')
 if args.phase=='upload':
  folder=ROOT/('Implementation/releases/'+release_version);manifest=json.loads((folder/'manifest.json').read_text())
  for name,ref in manifest['files'].items():
   body=(folder/name).read_bytes()
   if hashlib.sha256(body).hexdigest()!=ref['sha256']:raise ValueError('Frozen payload changed')
   try:s3.put_object(Bucket=BUCKET,Key=ref['s3_key'],Body=body,IfNoneMatch='*',Metadata={'sha256':ref['sha256']},ServerSideEncryption='AES256')
   except ClientError as error:
    if error.response['Error']['Code'] not in ('PreconditionFailed','412'):raise
   actual=s3.get_object(Bucket=BUCKET,Key=ref['s3_key'])['Body'].read()
   if hashlib.sha256(actual).hexdigest()!=ref['sha256']:raise ValueError('Conflicting uploaded code')
  save(attempt+'-code-upload.json',{'manifest':manifest,'git_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()});print('New frozen code uploaded/hash-verified; no processing started.')
 elif args.phase=='update':
  deployed=cfn.get_template(StackName=STACK,TemplateStage='Original')['TemplateBody']
  if isinstance(deployed,str):deployed=json.loads(deployed)
  if deployed!=base:raise ValueError('Live stack changed; inspect before updating')
  for name in ('prepare','risk','detect','evaluate','control'):
   if any(x['JobRunState'] not in ('SUCCEEDED','FAILED','STOPPED','TIMEOUT','ERROR','EXPIRED') for x in glue.get_job_runs(JobName='is459-aml-full-'+name)['JobRuns']):raise ValueError('Project compute active')
  response=cfn.update_stack(StackName=STACK,TemplateBody=json.dumps(template),Capabilities=['CAPABILITY_NAMED_IAM'],Parameters=[{'ParameterKey':k,'UsePreviousValue':True} for k in ('CodeVersion','RunId','ReleaseId')],ClientRequestToken=str(uuid.uuid4()))
  save(attempt+'-stack-update.json',{'response':response,'all_iam_resources_unchanged':True,'template_sha256':hashlib.sha256(template_path.read_bytes()).hexdigest()});print(json.dumps(response))
 elif args.phase=='verify':
  stack=cfn.describe_stacks(StackName=STACK)['Stacks'][0]
  if stack['StackStatus']!='UPDATE_COMPLETE':raise ValueError('Update not complete')
  deployed=cfn.get_template(StackName=STACK,TemplateStage='Original')['TemplateBody']
  if isinstance(deployed,str):deployed=json.loads(deployed)
  if deployed!=template:raise ValueError('Template mismatch')
  params={p['ParameterKey']:p['ParameterValue'] for p in stack['Parameters']}
  if params!={'CodeVersion':'full-v1','RunId':'full-20261028-v1','ReleaseId':'full-20261028-v1'}:raise ValueError('Unexpected attempt parameters')
  iam=s.client('iam')
  def resolve(value):
   if isinstance(value,list):return [resolve(v) for v in value]
   if not isinstance(value,dict):return value
   if 'Fn::Sub' in value:
    text=value['Fn::Sub']
    for k,v in params.items():text=text.replace('${'+k+'}',v)
    return text
   return {k:resolve(v) for k,v in value.items()}
  for r in template['Resources'].values():
   if r['Type']!='AWS::IAM::Role':continue
   props=resolve(r['Properties']);name=props['RoleName']
   if iam.get_role(RoleName=name)['Role']['AssumeRolePolicyDocument']!=props['AssumeRolePolicyDocument']:raise ValueError('Trust changed')
   if iam.list_attached_role_policies(RoleName=name)['AttachedPolicies']:raise ValueError('Unexpected attached policy')
   if set(iam.list_role_policies(RoleName=name)['PolicyNames'])!={p['PolicyName'] for p in props['Policies']}:raise ValueError('Unexpected inline policy')
   for p in props['Policies']:
    if iam.get_role_policy(RoleName=name,PolicyName=p['PolicyName'])['PolicyDocument']!=p['PolicyDocument']:raise ValueError('Policy differs from approved grant')
  for key in ('EvaluateJob','ControlJob'):
   props=template['Resources'][key]['Properties'];job=glue.get_job(JobName=props['Name'])['Job']
   for field in ('Command','DefaultArguments','GlueVersion','WorkerType','NumberOfWorkers','Timeout','MaxRetries','ExecutionProperty','JobRunQueuingEnabled','ExecutionClass'):
    if job.get(field)!=resolve(props[field]):raise ValueError('Job mismatch: '+field)
   expected_role='arn:aws:iam::'+ACCOUNT+':role/is459-aml-full-'+('evaluate' if key=='EvaluateJob' else 'control')
   if job['Role']!=expected_role:raise ValueError('Unexpected job role')
  arn=next(x['OutputValue'] for x in stack['Outputs'] if x['OutputKey']==workflow_key+'Arn');machine=sf.describe_state_machine(stateMachineArn=arn)
  definition=json.loads(template['Resources'][workflow_key]['Properties']['DefinitionString']['Fn::Sub'][0])
  encoded=json.dumps(definition).replace('${EvaluateJob}','is459-aml-full-evaluate').replace('${ControlJob}','is459-aml-full-control')
  if json.loads(machine['definition'])!=json.loads(encoded):raise ValueError('Workflow mismatch')
  if machine['roleArn']!='arn:aws:iam::'+ACCOUNT+':role/is459-aml-full-workflow':raise ValueError('Unexpected workflow role')
  if sf.list_executions(stateMachineArn=arn,maxResults=1)['executions']:raise ValueError('Continuation already started')
  try:
   s3.head_object(Bucket=BUCKET,Key='published/releases/full-20261028-v1/manifest.json')
  except ClientError as error:
   if error.response['Error']['Code'] not in ('404','NoSuchKey','NotFound'):raise
  else:raise ValueError('Full release ID already exists; inspect without overwriting')
  check=json.loads((REV/'evaluation-resume1-readonly-inspection.json').read_text())
  quality='quality/q2/dataset_version=ibm-hi-medium-b1b99c68b765580f/run_id=full-20261028-v1/analysis_id=q2-full-v2/attempt=recovery1/report.json'
  body=s3.get_object(Bucket=BUCKET,Key=quality)['Body'].read()
  if hashlib.sha256(body).hexdigest()!=check['q2_report_sha256']:raise ValueError('Frozen detector report changed')
  q2=json.loads(body)
  if q2['status']!='PASSED' or len(q2['snapshots'])!=28:raise ValueError('Incomplete detection')
  for prefix in ('evaluation/','quality/evaluation/'):
   key=prefix+'dataset_version=ibm-hi-medium-b1b99c68b765580f/run_id=full-20261028-v1/analysis_id=q2-full-v2/evaluation_id=eval-full-v2/attempt='+attempt+'/'
   if s3.list_objects_v2(Bucket=BUCKET,Prefix=key,MaxKeys=1).get('KeyCount'):raise ValueError('Fresh evaluation namespace required')
  save(attempt+'-deployment-verification.json',{'status':'VERIFIED_BEFORE_PROCESSING','workflow_arn':arn,'exact_template_jobs_workflow_roles_match':True,'q2_report_sha256':check['q2_report_sha256'],'fresh_evaluation_prefix':True,'budget_usd':30,'observed_at':datetime.datetime.now(datetime.timezone.utc).isoformat()});print('VERIFIED: unchanged grants, exact code/config, completed detection and fresh evaluation prefix.')
 elif args.phase=='status':
  stack=cfn.describe_stacks(StackName=STACK)['Stacks'][0];print(stack['StackStatus'])
  save(attempt+'-stack-status.json',stack)
 else:
  if (REV/(attempt+'-start.json')).exists() or (REV/(attempt+'-request.json')).exists():raise ValueError('Continuation already requested; inspect instead')
  verified=json.loads((REV/(attempt+'-deployment-verification.json')).read_text())
  if verified['status']!='VERIFIED_BEFORE_PROCESSING':raise ValueError('Verify exact deployment first')
  approval=json.loads((REV/(attempt+'-authorization.json')).read_text())
  if approval.get('approved') is not True or approval.get('template_sha256')!=hashlib.sha256(template_path.read_bytes()).hexdigest():raise ValueError('Exact processing scope not approved')
  costs=json.loads((REV/'full-monitor-latest.json').read_text())
  if costs['active_paid_resources'] or costs['guard_total_estimate_usd']+maximum_compute>=28:raise ValueError('Active processing or insufficient budget reserve')
  current=s3.get_object(Bucket=BUCKET,Key='published/current.json');pointer=json.loads(current['Body'].read())
  if pointer['release_id']!='pilot-20220901-m00-v1':raise ValueError('Publication changed; inspect before proceeding')
  body={'expected_pointer_etag':current['ETag'],'total_budget_usd':30}
  save(attempt+'-request.json',{'state_machine':verified['workflow_arn'],'execution_name':'full-20261028-'+attempt,'input':body,'maximum_new_compute_estimate_usd':maximum_compute,'completed_stages_reused':['preparation','q1','q2','catalog']})
  result=sf.start_execution(stateMachineArn=verified['workflow_arn'],name='full-20261028-'+attempt,input=json.dumps(body));save(attempt+'-start.json',result);print(json.dumps(result,default=str))

if __name__=='__main__':main()
