"""Fresh full run on the maintained five-job stack; no automatic execution."""
import copy,json
from pathlib import Path
from build_stack import build as base
from build_rerun import dashboard as old_dashboard
PREFIX='is459-aml-full'
STACK_NAME='is459-aml-full-v1'
RUN_ID='full-20261030-v1'
CODE_VERSION='full-v6'
BUDGET_USD=90
INPUT_PREFIX='raw/full-20261030-v1'

def build():
    t=base()
    t['Parameters']['RunId']['Default']=RUN_ID
    t['Parameters']['ReleaseId']['Default']=RUN_ID
    t['Parameters']['CodeVersion']['Default']=CODE_VERSION
    for r in t['Resources'].values():
        if r['Type']=='AWS::Glue::Job':r['Properties']['Tags']['BudgetUSD']=str(BUDGET_USD)
    r=t['Resources']
    r['EvaluateJob']['Properties']['NumberOfWorkers']=10
    r['PrepareJob']['Properties']['DefaultArguments']['--input-root']=r['PrepareJob']['Properties']['DefaultArguments']['--input-root'].replace('raw/full-v1',INPUT_PREFIX)
    role=r['PrepareRole']['Properties']['Policies'][0]['PolicyDocument']
    r['PrepareRole']['Properties']['Policies'][0]['PolicyDocument']=json.loads(json.dumps(role).replace('raw/full-v1',INPUT_PREFIX))
    # Run-specific temporary files prevent old checkpoints influencing the new run.
    t=json.loads(json.dumps(t).replace('temporary/full/','temporary/run30/'))
    t['Outputs']['ComputeMaximumEstimateUSD']['Value']='15.84 configured Glue compute estimate at reviewed pricing, excluding startup/storage/requests/dashboard; not a billing cap.'
    return t

def dashboard():
    t=copy.deepcopy(old_dashboard())
    t['Resources']['Role']['Properties']['RoleName']='is459-aml-run30-dashboard'
    for tag in t['Resources']['Instance']['Properties']['Tags']:
        if tag['Key']=='Name':tag['Value']='is459-aml-run30-dashboard'
    return t

if __name__=='__main__':
    for name,t in [('run30-stack.json',build()),('run30-dashboard-stack.json',dashboard())]:
        Path(__file__).with_name(name).write_text(json.dumps(t,indent=2)+'\n')
