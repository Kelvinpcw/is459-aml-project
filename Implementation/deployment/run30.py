"""Deliberate fresh-run phases. Private plan/markers; no legacy attempt reuse."""
import argparse,datetime,hashlib,json,re,subprocess,uuid
from pathlib import Path
import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
from build_stack import ACCOUNT,REGION,BUCKET
from build_run30 import PREFIX,STACK_NAME,RUN_ID,CODE_VERSION,BUDGET_USD,build,dashboard
ROOT=Path(__file__).resolve().parents[2]
TERMINAL={'SUCCEEDED','FAILED','STOPPED','TIMEOUT','ERROR','EXPIRED'}


def encode(value):return json.dumps(value,indent=2,default=str)+'\n'
def save(folder,name,value,exclusive=False):
    with (folder/name).open('x' if exclusive else 'w') as f:f.write(encode(value))


def identity(profile):
    subprocess.run(['bash',str(ROOT/'Implementation/scripts/check_aws_profile.sh'),profile],check=True)
    s=boto3.Session(profile_name=profile,region_name=REGION)
    if s.client('sts').get_caller_identity()['Account']!=ACCOUNT:raise ValueError('Wrong project identity')
    return s


def jobs_status(glue):
    result={}
    for name in ('prepare','risk','detect','evaluate','control'):
        try:result[name]=glue.get_job_runs(JobName=PREFIX+'-'+name,MaxResults=100)['JobRuns']
        except glue.exceptions.EntityNotFoundException:result[name]=[]
    return result


def run_jobs_since(glue,started):
    started=datetime.datetime.fromisoformat(str(started))
    return {stage:[r for r in rows if r['StartedOn']>=started] for stage,rows in jobs_status(glue).items()}


def resolve(value,params):
    if isinstance(value,list):return [resolve(v,params) for v in value]
    if not isinstance(value,dict):return value
    if 'Fn::Sub' in value:
        text=value['Fn::Sub']
        if not isinstance(text,str):raise ValueError('Only simple substitutions expected here')
        for key,item in params.items():text=text.replace('${'+key+'}',item)
        return text
    return {key:resolve(item,params) for key,item in value.items()}


def verify_stack(s,template):
    c=s.client('cloudformation');stack=c.describe_stacks(StackName=STACK_NAME)['Stacks'][0]
    if stack['StackStatus'] not in ('CREATE_COMPLETE','UPDATE_COMPLETE'):raise ValueError('Fresh stack not ready')
    actual=c.get_template(StackName=STACK_NAME,TemplateStage='Original')['TemplateBody'];actual=json.loads(actual) if isinstance(actual,str) else actual
    if actual!=template:raise ValueError('Deployed template differs')
    params={v['ParameterKey']:v['ParameterValue'] for v in stack['Parameters']}
    if params!={'RunId':RUN_ID,'ReleaseId':RUN_ID,'CodeVersion':CODE_VERSION}:raise ValueError('Wrong run parameters')
    glue=s.client('glue');iam=s.client('iam')
    for resource in template['Resources'].values():
        p=resource['Properties']
        if resource['Type']=='AWS::IAM::Role':
            props=resolve(p,params);name=props['RoleName']
            if iam.get_role(RoleName=name)['Role']['AssumeRolePolicyDocument']!=props['AssumeRolePolicyDocument']:raise ValueError('Trust policy changed')
            if iam.list_attached_role_policies(RoleName=name)['AttachedPolicies']:raise ValueError('Unexpected attached grant')
            if {x['PolicyName'] for x in props['Policies']}!=set(iam.list_role_policies(RoleName=name)['PolicyNames']):raise ValueError('Unexpected policy names')
            for policy in props['Policies']:
                if iam.get_role_policy(RoleName=name,PolicyName=policy['PolicyName'])['PolicyDocument']!=policy['PolicyDocument']:raise ValueError('Grant differs from reviewed template')
        if resource['Type']=='AWS::Glue::Job':
            expected=resolve(p,params);job=glue.get_job(JobName=p['Name'])['Job']
            for field in ('Command','DefaultArguments','GlueVersion','WorkerType','NumberOfWorkers','Timeout','MaxRetries','ExecutionProperty','JobRunQueuingEnabled','ExecutionClass'):
                if job.get(field)!=expected[field]:raise ValueError('Job differs: '+p['Name']+' / '+field)
            stage=p['Name'].rsplit('-',1)[1]
            if job['Role']!='arn:aws:iam::'+ACCOUNT+':role/'+PREFIX+'-'+stage:raise ValueError('Wrong service role')
    workflow=next(v['OutputValue'] for v in stack['Outputs'] if v['OutputKey']=='WorkflowArn')
    machine=s.client('stepfunctions').describe_state_machine(stateMachineArn=workflow)
    definition=template['Resources']['Workflow']['Properties']['DefinitionString']['Fn::Sub'][0]
    for key in ('PrepareJob','RiskJob','DetectJob','EvaluateJob','ControlJob'):
        definition=definition.replace('${'+key+'}',template['Resources'][key]['Properties']['Name'])
    if json.loads(machine['definition'])!=json.loads(definition):raise ValueError('Workflow definition differs')
    if machine['roleArn']!='arn:aws:iam::'+ACCOUNT+':role/'+PREFIX+'-workflow':raise ValueError('Wrong workflow role')
    return stack,workflow


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--profile',required=True);parser.add_argument('--plan',type=Path,required=True)
    parser.add_argument('--phase',required=True,choices=['upload','create','apply','verify','start','status','stop','dashboard','dashboard-status','remove-dashboard'])
    args=parser.parse_args();plan=json.loads(args.plan.read_text());folder=args.plan.parent
    if plan.get('approved') is not True or plan.get('budget_usd')!=BUDGET_USD or plan.get('run_id')!=RUN_ID or plan.get('code_version')!=CODE_VERSION:raise ValueError('Require this exact approved private plan')
    template=build();raw=(ROOT/'Implementation/deployment/run30-stack.json').read_bytes()
    if json.loads(raw)!=template:raise ValueError('Generated template is stale')
    if plan.get('template_sha256')!=hashlib.sha256(raw).hexdigest():raise ValueError('Plan/template mismatch')
    s=identity(args.profile);s3=s.client('s3');cfn=s.client('cloudformation');sf=s.client('stepfunctions',config=Config(retries={'total_max_attempts':1}));glue=s.client('glue')
    if args.phase=='upload':
        package=ROOT/'Implementation/releases'/CODE_VERSION;manifest=json.loads((package/'manifest.json').read_text())
        for name,ref in manifest['files'].items():
            body=(package/name).read_bytes()
            if hashlib.sha256(body).hexdigest()!=ref['sha256']:raise ValueError('Frozen payload changed')
            try:s3.put_object(Bucket=BUCKET,Key=ref['s3_key'],Body=body,IfNoneMatch='*',Metadata={'sha256':ref['sha256']},ServerSideEncryption='AES256')
            except ClientError as error:
                if error.response['Error']['Code'] not in ('412','PreconditionFailed'):raise
            actual=s3.get_object(Bucket=BUCKET,Key=ref['s3_key'])['Body'].read()
            if hashlib.sha256(actual).hexdigest()!=ref['sha256']:raise ValueError('Immutable uploaded object conflict')
        save(folder,'code-upload.json',{'manifest':manifest,'source_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()});print('Uploaded/verified fresh immutable package; no processing started.')
    elif args.phase=='create':
        if not (folder/'code-upload.json').exists():raise ValueError('Upload and verify code first')
        # Prepare only: the separate apply phase rejects additions/deletions/replacements.
        result=cfn.create_change_set(StackName=STACK_NAME,ChangeSetName='full-run30',ChangeSetType='UPDATE',TemplateBody=raw.decode(),Capabilities=['CAPABILITY_NAMED_IAM'],Parameters=[{'ParameterKey':key,'ParameterValue':value} for key,value in {'CodeVersion':CODE_VERSION,'RunId':RUN_ID,'ReleaseId':RUN_ID}.items()])
        save(folder,'change-set-create.json',result,True);print('Change set prepared; inspect before apply. No jobs started.')
    elif args.phase=='apply':
        change=cfn.describe_change_set(StackName=STACK_NAME,ChangeSetName='full-run30')
        allowed={'PrepareRole','RiskRole','DetectRole','EvaluateRole','ControlRole','PrepareJob','RiskJob','DetectJob','EvaluateJob','ControlJob'}
        if change['Status']!='CREATE_COMPLETE':raise ValueError('Change set not ready')
        for item in change['Changes']:
            r=item['ResourceChange']
            if r['Action']!='Modify' or r['LogicalResourceId'] not in allowed or r.get('Replacement')!='False':raise ValueError('Unexpected resource change: '+str(r))
        if any(r['JobRunState'] not in TERMINAL for rows in jobs_status(glue).values() for r in rows):raise ValueError('Shared jobs active')
        stack=cfn.describe_stacks(StackName=STACK_NAME)['Stacks'][0]
        workflow=next(x['OutputValue'] for x in stack['Outputs'] if x['OutputKey']=='WorkflowArn')
        if sf.list_executions(stateMachineArn=workflow,statusFilter='RUNNING')['executions']:raise ValueError('Shared workflow active')
        save(folder,'change-set-reviewed.json',change)
        cfn.execute_change_set(StackName=STACK_NAME,ChangeSetName='full-run30');save(folder,'stack-update.json',{'submitted':True},True);print('Reviewed existing-stack update submitted; no jobs started.')
    elif args.phase=='verify':
        stack,workflow=verify_stack(s,template)
        if any(r['JobRunState'] not in TERMINAL for rows in jobs_status(glue).values() for r in rows):raise ValueError('Job already active')
        if any(x['name']==RUN_ID for page in sf.get_paginator('list_executions').paginate(stateMachineArn=workflow) for x in page['executions']):raise ValueError('This run identity already used')
        save(folder,'deployment-verified.json',{'status':'VERIFIED','workflow_arn':workflow,'template_sha256':hashlib.sha256(raw).hexdigest(),'observed_at':datetime.datetime.now(datetime.timezone.utc).isoformat()});print('Verified exact deployed jobs/workflow/roles and unused run identity.')
    elif args.phase=='start':
        if (folder/'request.json').exists() or (folder/'start.json').exists():raise ValueError('Attempt already requested; inspect instead of retrying')
        _,workflow=verify_stack(s,template)
        if not (folder/'deployment-verified.json').exists():raise ValueError('Explicit verify phase required')
        current=s3.get_object(Bucket=BUCKET,Key='published/current.json');pointer=json.loads(current['Body'].read())
        if pointer!=plan['previous_pointer']:raise ValueError('Publication changed since approval; coordinate before starting')
        if any(r['JobRunState'] not in TERMINAL for rows in jobs_status(glue).values() for r in rows):raise ValueError('Compute already active')
        for prefix in ('curated/','references/labels/','gold/risk/','gold/cases/','quality/preparation/','quality/q1/','quality/q2/','quality/evaluation/','evaluation/','manifests/detector-inputs/'):
            key=prefix+'dataset_version=ibm-hi-medium-b1b99c68b765580f/run_id='+RUN_ID+'/'
            if s3.list_objects_v2(Bucket=BUCKET,Prefix=key,MaxKeys=1).get('KeyCount',0):raise ValueError('Fresh outputs required')
        key='published/releases/'+RUN_ID+'/'
        if s3.list_objects_v2(Bucket=BUCKET,Prefix=key,MaxKeys=1).get('KeyCount',0):raise ValueError('Release identity already used')
        body={'expected_pointer_etag':current['ETag'],'total_budget_usd':BUDGET_USD}
        save(folder,'request.json',{'workflow':workflow,'execution_name':RUN_ID,'input':body,'plan_sha256':hashlib.sha256(args.plan.read_bytes()).hexdigest()},True)
        result=sf.start_execution(stateMachineArn=workflow,name=RUN_ID,input=json.dumps(body,sort_keys=True));save(folder,'start.json',result,True);print('One new full workflow started; private request/start markers saved.')
    elif args.phase=='status':
        stack=cfn.describe_stacks(StackName=STACK_NAME)['Stacks'][0];jobs={};execution=None
        if (folder/'start.json').exists():
            start=json.loads((folder/'start.json').read_text());execution=sf.describe_execution(executionArn=start['executionArn']);jobs=run_jobs_since(glue,start['startDate'])
        now=datetime.datetime.now(datetime.timezone.utc);compute=0;active=[]
        for stage,rows in jobs.items():
            for row in rows:
                running=row['JobRunState'] not in TERMINAL;seconds=max(row.get('ExecutionTime',0),(now-row['StartedOn']).total_seconds() if running else 0,60)
                compute+=seconds*row.get('NumberOfWorkers',2)/3600*.44
                if running:active.append({'stage':stage,'id':row['Id']})
        guard=compute+plan['prior_spend_reserve_usd']+plan['new_noncompute_reserve_usd']
        save(folder,'status-latest.json',{'at':now,'stack':stack,'execution':execution,'jobs':jobs,'new_compute_estimate_usd':compute,'guard_total_estimate_usd':guard,'active':active,'note':'Conservative elapsed/DPU estimate and reserves, not invoice or billing cap.'})
        if guard>=BUDGET_USD-5 and active:
            if execution and execution['status']=='RUNNING':sf.stop_execution(executionArn=execution['executionArn'],cause='Budget reserve approached')
            for row in active:glue.batch_stop_job_run(JobName=PREFIX+'-'+row['stage'],JobRunIds=[row['id']])
            raise ValueError('Budget stop requested; verify terminal states')
        print(encode({'stack':stack['StackStatus'],'execution':execution['status'] if execution else None,'jobs':{key:[{'state':r['JobRunState'],'seconds':r.get('ExecutionTime'),'error':r.get('ErrorMessage')} for r in rows] for key,rows in jobs.items()},'budget_guard_estimate_usd':round(guard,2),'active':active}))
    elif args.phase=='stop':
        if (folder/'start.json').exists():
            arn=json.loads((folder/'start.json').read_text())['executionArn']
            if sf.describe_execution(executionArn=arn)['status']=='RUNNING':sf.stop_execution(executionArn=arn,cause='User-authorised owned rerun cleanup')
        if not (folder/'start.json').exists():raise ValueError('No owned start marker; inspect before stopping shared jobs')
        start=json.loads((folder/'start.json').read_text())
        for stage,rows in run_jobs_since(glue,start['startDate']).items():
            ids=[r['Id'] for r in rows if r['JobRunState'] not in TERMINAL]
            if ids:glue.batch_stop_job_run(JobName=PREFIX+'-'+stage,JobRunIds=ids)
        save(folder,'stop-request.json',{'at':datetime.datetime.now(datetime.timezone.utc),'terminal_verification_required':True});print('Owned rerun stop requested; verify terminal states.')
    elif args.phase=='dashboard':
        if not (folder/'start.json').exists():raise ValueError('Full workflow must finish before dashboard')
        execution=sf.describe_execution(executionArn=json.loads((folder/'start.json').read_text())['executionArn'])
        if execution['status']!='SUCCEEDED':raise ValueError('Wait for full workflow success')
        from sys import path
        path.insert(0,str(ROOT/'Implementation'))
        from pipeline.release import load_current
        if load_current(s3)['release_id']!=RUN_ID:raise ValueError('New release not current')
        ec2=s.client('ec2');vpcs=ec2.describe_vpcs(Filters=[{'Name':'is-default','Values':['true']}])['Vpcs']
        if len(vpcs)!=1:raise ValueError('One existing authorised default VPC required')
        subnets=ec2.describe_subnets(Filters=[{'Name':'vpc-id','Values':[vpcs[0]['VpcId']]},{'Name':'default-for-az','Values':['true']}])['Subnets']
        if not subnets:raise ValueError('Existing subnet required')
        result=cfn.create_stack(StackName='is459-aml-run30-dashboard',TemplateBody=json.dumps(dashboard()),Capabilities=['CAPABILITY_NAMED_IAM'],ClientRequestToken=str(uuid.uuid4()),OnFailure='DELETE',Parameters=[{'ParameterKey':k,'ParameterValue':v} for k,v in {'CodeVersion':CODE_VERSION,'VpcId':vpcs[0]['VpcId'],'SubnetId':subnets[0]['SubnetId']}.items()],Tags=[{'Key':'Project','Value':'is459-aml'}])
        save(folder,'dashboard-create.json',result,True);print('Temporary private dashboard requested; one-hour terminate timer configured.')
    elif args.phase=='dashboard-status':
        stack=cfn.describe_stacks(StackName='is459-aml-run30-dashboard')['Stacks'][0];save(folder,'dashboard-status.json',stack);print(encode({'state':stack['StackStatus'],'outputs':stack.get('Outputs',[])}))
    else:
        cfn.delete_stack(StackName='is459-aml-run30-dashboard');save(folder,'dashboard-delete-request.json',{'requested_at':datetime.datetime.now(datetime.timezone.utc)});print('Owned temporary dashboard deletion requested; verify instance/volume cleanup.')

if __name__=='__main__':main()
