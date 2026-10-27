"""Generate an on-demand, isolated full-run stack. No deployment on import."""
import json
from pathlib import Path

ACCOUNT='160885259244';REGION='us-east-1';BUCKET='is459-aml-g2team7-160885259244-us-east-1'
DATASET='ibm-hi-medium-b1b99c68b765580f'

def sub(value):return {'Fn::Sub':value} if '${' in value else value
def ref(value):return {'Ref':value}
def attr(name,value):return {'Fn::GetAtt':[name,value]}
def trust(service):return {'Version':'2012-10-17','Statement':[{'Effect':'Allow','Principal':{'Service':service},'Action':'sts:AssumeRole'}]}
def allow(actions,resources):return {'Effect':'Allow','Action':actions,'Resource':resources}

def build():
 r={};root='s3://'+BUCKET;arn='arn:aws:s3:::'+BUCKET
 suffix='dataset_version='+DATASET+'/run_id=${RunId}/'
 facts='curated/'+suffix+'transactions/';labels='references/labels/'+suffix+'transactions/'
 prep='quality/preparation/'+suffix+'report.json';q1='gold/risk/'+suffix+'analysis_id=q1-full-v1/'
 q2='gold/cases/'+suffix+'analysis_id=q2-full-v2/'
 evalsuffix=suffix+'analysis_id=q2-full-v2/evaluation_id=eval-full-v2/'
 ev='evaluation/'+evalsuffix;eq='quality/evaluation/'+evalsuffix
 qp1='quality/q1/'+suffix+'analysis_id=q1-full-v1/';qp2='quality/q2/'+suffix+'analysis_id=q2-full-v2/'
 manifest='manifests/detector-inputs/'+suffix+'manifest.json'
 annotations='references/annotations/dataset_version='+DATASET+'/HI-Medium_Patterns.txt'
 scripts='scripts/${CodeVersion}/'
 def role(name,reads,writes,extra=None,denies=None):
  prefixes=reads+writes+[scripts,'temporary/full/'+name+'/']
  policies=[allow('s3:GetBucketLocation',arn),{'Effect':'Allow','Action':'s3:ListBucket','Resource':arn,'Condition':{'StringLike':{'s3:prefix':[sub(x.rstrip('/')+'*') for x in prefixes]}}},
    allow('s3:GetObject',[sub(value) for x in reads+[scripts] for value in ([arn+'/'+x.rstrip('/'),arn+'/'+x+'*'] if x.endswith('/') else [arn+'/'+x])]),
    allow(['s3:GetObject','s3:PutObject','s3:DeleteObject','s3:AbortMultipartUpload'],[sub(arn+'/'+x.rstrip('/')+'/*') if x.endswith('/') else sub(arn+'/'+x) for x in writes+['temporary/full/'+name+'/']]),
    allow(['logs:CreateLogGroup','logs:CreateLogStream','logs:PutLogEvents'],'arn:aws:logs:'+REGION+':'+ACCOUNT+':log-group:/is459/aml/full/'+name+'/*')]
  if denies:policies.append({'Effect':'Deny','Action':'s3:GetObject*','Resource':[arn+'/'+x+'*' for x in denies]})
  policies+=extra or []
  key=name.title()+'Role'
  r[key]={'Type':'AWS::IAM::Role','Properties':{'RoleName':'is459-aml-full-'+name,'AssumeRolePolicyDocument':trust('glue.amazonaws.com'),'Policies':[{'PolicyName':'project-data-only','PolicyDocument':{'Version':'2012-10-17','Statement':policies}}]}}
  return key
 prep_role=role('prepare',['raw/full-v1/'],['curated/'+suffix,'references/labels/'+suffix,'quality/preparation/'+suffix,'quarantine/preparation/'+suffix])
 q1_role=role('risk',[facts,labels,prep],[q1,qp1])
 q2_role=role('detect',[facts,manifest],[q2,qp2],denies=['raw/','references/','gold/risk/','evaluation/','quality/preparation/','quality/q1/','quality/evaluation/'])
 eval_role=role('evaluate',[facts,labels,prep,q2,qp2,annotations],[ev,eq],denies=['raw/','gold/risk/','quality/q1/'])
 catalog_resources=['arn:aws:glue:'+REGION+':'+ACCOUNT+':catalog','arn:aws:glue:'+REGION+':'+ACCOUNT+':database/is459_aml_full','arn:aws:glue:'+REGION+':'+ACCOUNT+':table/is459_aml_full/q*']
 gate_role=role('control',[prep,qp1,qp2,q1,q2,ev,eq],[manifest,'published/releases/${ReleaseId}/','published/current.json'],extra=[allow(['glue:CreateTable','glue:GetTable','glue:BatchCreatePartition','glue:GetPartitions'],catalog_resources)])
 r['FullDatabase']={'Type':'AWS::Glue::Database','Properties':{'CatalogId':ACCOUNT,'DatabaseInput':{'Name':'is459_aml_full','Description':'Isolated full-data AML release tables'}}}
 common={'--job-language':'python','--job-bookmark-option':'job-bookmark-disable','--enable-metrics':'false','--enable-observability-metrics':'false','--enable-job-insights':'false','--enable-spark-ui':'false','--extra-py-files':root+'/'+scripts+'jobs.zip'}
 def job(key,name,role_key,script,workers,timeout,arguments):
  args={**common,'--custom-logGroup-prefix':'/is459/aml/full/'+name,'--TempDir':root+'/temporary/full/'+name+'/',**arguments}
  r[key]={'Type':'AWS::Glue::Job','Properties':{'Name':'is459-aml-full-'+name,'Role':attr(role_key,'Arn'),'Command':{'Name':'glueetl','PythonVersion':'3','ScriptLocation':sub(root+'/'+scripts+script)},'GlueVersion':'5.1','WorkerType':'G.1X','NumberOfWorkers':workers,'Timeout':timeout,'MaxRetries':0,'ExecutionProperty':{'MaxConcurrentRuns':1},'JobRunQueuingEnabled':False,'ExecutionClass':'STANDARD','DefaultArguments':{k:sub(v) if '${' in str(v) else v for k,v in args.items()},'Tags':{'Project':'is459-aml','Phase':'full-data','BudgetUSD':'30'}}}
 job('PrepareJob','prepare',prep_role,'prepare.py',5,45,{'--input-root':root+'/raw/full-v1','--output-root':root,'--run-id':'${RunId}','--max-quarantine-rows':'0'})
 job('RiskJob','risk',q1_role,'q1_risk.py',5,45,{'--preparation-report':root+'/'+prep,'--output-root':root,'--analysis-id':'q1-full-v1'})
 job('DetectJob','detect',q2_role,'q2_snapshots.py',10,120,{'--input-manifest':root+'/'+manifest,'--output-root':root,'--analysis-id':'q2-full-v2','--first-snapshot-end':'2022-09-02T00:00:00','--last-snapshot-end':'2022-09-29T00:00:00','--max-cycle-degree':'64','--max-cycle-path-rows':'200000000','--max-output-cost-usd':'10'})
 job('EvaluateJob','evaluate',eval_role,'evaluate_distributed.py',5,45,{'--preparation-report':root+'/'+prep,'--detector-report':root+'/'+qp2+'report.json','--annotations':root+'/'+annotations,'--annotations-sha256':'392d748d8d76efc1a96f6dc29ad8dd282c815de96537f0296bb0a7fa96ec4130','--output-root':root,'--evaluation-id':'eval-full-v2'})
 job('ControlJob','control',gate_role,'control.py',2,10,{'--run-id':'${RunId}','--release-id':'${ReleaseId}'})
 job_arns=['arn:aws:glue:'+REGION+':'+ACCOUNT+':job/is459-aml-full-'+n for n in ['prepare','risk','detect','evaluate','control']]
 r['WorkflowRole']={'Type':'AWS::IAM::Role','Properties':{'RoleName':'is459-aml-full-workflow','AssumeRolePolicyDocument':trust('states.amazonaws.com'),'Policies':[{'PolicyName':'only-full-jobs','PolicyDocument':{'Version':'2012-10-17','Statement':[allow(['glue:StartJobRun','glue:GetJobRun','glue:GetJobRuns','glue:BatchStopJobRun'],job_arns)]}}]}}
 def task(name,next_state=None,phase=None,end=False):
  state={'Type':'Task','Resource':'arn:aws:states:::glue:startJobRun.sync','Parameters':{'JobName':'${'+name+'}'},'ResultPath':None}
  if phase:
   state['Parameters']['Arguments']={'--phase':phase}
   if phase=='publish':state['Parameters']['Arguments']['--expected-pointer-etag.$']='$.expected_pointer_etag'
  state['End']=True if end else False
  if not end:state.pop('End');state['Next']=next_state
  return state
 states={'Prepare':task('PrepareJob','MakeManifest'),'MakeManifest':task('ControlJob','Branches','manifests'),
  'Branches':{'Type':'Parallel','Branches':[{'StartAt':'Risk','States':{'Risk':task('RiskJob',end=True)}},{'StartAt':'Detect','States':{'Detect':task('DetectJob',end=True)}}],'ResultPath':None,'Next':'Catalog'},
  'Catalog':task('ControlJob','Evaluate','catalog'),'Evaluate':task('EvaluateJob','Publish'),'Publish':task('ControlJob',phase='publish',end=True),
  'Failed':{'Type':'Fail','Error':'PipelineFailed','Cause':'A required stage failed. Prior published release is retained; choose a new attempt after diagnosis.'}}
 for name,state in states.items():
  if state['Type'] in ('Task','Parallel'):state['Catch']=[{'ErrorEquals':['States.ALL'],'ResultPath':'$.failure','Next':'Failed'}]
 definition={'Comment':'On-demand AML full-data workflow; no retries or recurring schedule. Published pointer changes only after all gates.','StartAt':'Prepare','TimeoutSeconds':16200,'States':states}
 r['Workflow']={'Type':'AWS::StepFunctions::StateMachine','Properties':{'StateMachineName':'is459-aml-full-pipeline','StateMachineType':'STANDARD','RoleArn':attr('WorkflowRole','Arn'),'DefinitionString':{'Fn::Sub':[json.dumps(definition),{k:ref(k) for k in ['PrepareJob','RiskJob','DetectJob','EvaluateJob','ControlJob']}]}}}
 r['DashboardWorkgroup']={'Type':'AWS::Athena::WorkGroup','Properties':{'Name':'is459-aml-dashboard','State':'ENABLED','WorkGroupConfiguration':{'EnforceWorkGroupConfiguration':True,'PublishCloudWatchMetricsEnabled':False,'BytesScannedCutoffPerQuery':536870912,'EngineVersion':{'SelectedEngineVersion':'Athena engine version 3'},'ResultConfiguration':{'OutputLocation':root+'/query-results/dashboard/','ExpectedBucketOwner':ACCOUNT,'EncryptionConfiguration':{'EncryptionOption':'SSE_S3'}}}}}
 return {'AWSTemplateFormatVersion':'2010-09-09','Description':'IS459 isolated full-data batch definitions. No jobs run and no EC2 is launched by stack creation.',
  'Parameters':{'CodeVersion':{'Type':'String','Default':'full-v1','AllowedPattern':'full-v[1-9][0-9]*'},'RunId':{'Type':'String','Default':'full-20261028-v1','AllowedPattern':'[a-z][a-z0-9-]{1,60}'},'ReleaseId':{'Type':'String','Default':'full-20261028-v1','AllowedPattern':'[a-z][a-z0-9-]{1,60}'}},'Resources':r,'Outputs':{'WorkflowArn':{'Value':ref('Workflow')},'ComputeMaximumEstimateUSD':{'Value':'14.19 at US$0.44/DPU-hour if every job reaches its timeout; S3/requests/logging/dashboard separate. Not a hard billing cap.'}}}

if __name__=='__main__':
 out=Path(__file__).with_name('full-pipeline-stack.json');out.write_text(json.dumps(build(),indent=2)+'\n');print(out)
