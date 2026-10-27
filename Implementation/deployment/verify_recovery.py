"""Verify exact recovered definitions, original IAM grants and immutable inputs."""
import argparse,boto3,json,re,hashlib,datetime
from deploy import ROOT,REV,STACK,save
from build_stack import ACCOUNT,REGION,BUCKET


def main():
    p=argparse.ArgumentParser();p.add_argument('--profile',required=True);args=p.parse_args()
    s=boto3.Session(profile_name=args.profile,region_name=REGION)
    if s.client('sts').get_caller_identity()['Account']!=ACCOUNT:raise ValueError('Wrong account')
    c=s.client('cloudformation');g=s.client('glue');iam=s.client('iam');s3=s.client('s3');sf=s.client('stepfunctions')
    stack=c.describe_stacks(StackName=STACK)['Stacks'][0]
    if stack['StackStatus']!='UPDATE_COMPLETE':raise ValueError('Update not complete')
    expected=json.loads((ROOT/'Implementation/deployment/recovery1-stack.json').read_text());actual=c.get_template(StackName=STACK,TemplateStage='Original')['TemplateBody']
    if isinstance(actual,str):actual=json.loads(actual)
    if actual!=expected:raise ValueError('Deployed recovery template differs')
    params={r['ParameterKey']:r['ParameterValue'] for r in stack['Parameters']}
    physical={r['LogicalResourceId']:r['PhysicalResourceId'] for r in c.list_stack_resources(StackName=STACK)['StackResourceSummaries']}
    def resolve(x):
        if isinstance(x,list):return [resolve(v) for v in x]
        if not isinstance(x,dict):return x
        if 'Ref' in x:return params.get(x['Ref'],physical.get(x['Ref']))
        if 'Fn::GetAtt' in x:
            key,attribute=x['Fn::GetAtt']
            if attribute!='Arn':raise ValueError('Unsupported attribute')
            return f'arn:aws:iam::{ACCOUNT}:role/'+physical[key]
        if 'Fn::Sub' in x:
            value=x['Fn::Sub'];body,variables=(value,{}) if isinstance(value,str) else value
            variables={k:resolve(v) for k,v in variables.items()}
            return re.sub(r'\$\{([^}]+)\}',lambda m:str(variables[m[1]] if m[1] in variables else params[m[1]]),body)
        return {k:resolve(v) for k,v in x.items()}
    roles=[];jobs=[]
    for key,r in expected['Resources'].items():
        p=resolve(r['Properties'])
        if r['Type']=='AWS::IAM::Role':
            name=p['RoleName'];role=iam.get_role(RoleName=name)['Role']
            if role['AssumeRolePolicyDocument']!=p['AssumeRolePolicyDocument']:raise ValueError('Trust changed: '+name)
            if iam.list_attached_role_policies(RoleName=name)['AttachedPolicies']:raise ValueError('Unexpected attached policies')
            if iam.list_role_policies(RoleName=name)['PolicyNames']!=[x['PolicyName'] for x in p['Policies']]:raise ValueError('Unexpected inline policies')
            for policy in p['Policies']:
                if iam.get_role_policy(RoleName=name,PolicyName=policy['PolicyName'])['PolicyDocument']!=policy['PolicyDocument']:raise ValueError('Policy changed: '+name)
            roles.append({'name':name,'exact_trust_and_grants_match':True})
        elif r['Type']=='AWS::Glue::Job':
            job=g.get_job(JobName=p['Name'])['Job']
            for field in ['Role','Command','GlueVersion','WorkerType','NumberOfWorkers','Timeout','MaxRetries','ExecutionProperty','JobRunQueuingEnabled','ExecutionClass','DefaultArguments']:
                if job.get(field)!=p[field]:raise ValueError('Job mismatch: '+p['Name']+' '+field)
            if any(x['JobRunState'] in ('STARTING','RUNNING','WAITING','STOPPING') for x in g.get_job_runs(JobName=p['Name'])['JobRuns']):raise ValueError('Job unexpectedly active')
            jobs.append({'name':p['Name'],'exact_configuration_matches':True})
    machine=sf.describe_state_machine(stateMachineArn=physical['RecoveryWorkflow']);definition=resolve(expected['Resources']['RecoveryWorkflow']['Properties']['DefinitionString'])
    if json.loads(machine['definition'])!=json.loads(definition):raise ValueError('Recovery definition differs')
    if sf.list_executions(stateMachineArn=physical['RecoveryWorkflow'],maxResults=1)['executions']:raise ValueError('Recovery already started')
    for kind,analysis in [('q1','q1-full-v1'),('q2','q2-full-v2')]:
        suffix='dataset_version=ibm-hi-medium-b1b99c68b765580f/run_id=full-20261028-v1/analysis_id='+analysis+'/attempt=recovery1/'
        for prefix in [('gold/risk/' if kind=='q1' else 'gold/cases/')+suffix,'quality/'+kind+'/'+suffix]:
            if s3.list_objects_v2(Bucket=BUCKET,Prefix=prefix,MaxKeys=1).get('KeyCount'):raise ValueError('Recovery output already exists')
    key='quality/preparation/dataset_version=ibm-hi-medium-b1b99c68b765580f/run_id=full-20261028-v1/report.json';raw=s3.get_object(Bucket=BUCKET,Key=key)['Body'].read()
    if raw!=(REV/'full-preparation-report.json').read_bytes():raise ValueError('Successful preparation report changed')
    save('full-recovery1-deployment-verification.json',{'status':'VERIFIED_BEFORE_RECOVERY','observed_at_singapore':datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat(),
      'account_id':ACCOUNT,'region':REGION,'parameters':params,'all_six_original_iam_grants_unchanged':True,'roles':roles,'jobs':jobs,
      'recovery_definition_matches':True,'recovery_execution_count':0,'recovery_output_prefixes_empty':True,'preparation_report_raw_sha256':hashlib.sha256(raw).hexdigest(),
      'frozen_payload_download_hashes':'full-recovery1-code-upload.json','budget_usd':30})
    print('VERIFIED: original IAM grants unchanged, corrected jobs/workflow exact, preparation unchanged, recovery unstarted and fresh.')

if __name__=='__main__':main()
