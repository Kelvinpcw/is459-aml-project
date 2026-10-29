"""Fresh isolated full rerun: reuse storage/Catalog/workgroup, never old jobs."""
import copy,json,re
from build_stack import build as original_stack
from build_dashboard_stack import build as original_dashboard

PREFIX='is459-aml-rerun29'
RUN_ID='full-20261029-v1'
CODE_VERSION='full-v6'
BUDGET_USD=90


def _replace(value):
    if isinstance(value,list):return [_replace(v) for v in value]
    if isinstance(value,dict):return {k:_replace(v) for k,v in value.items()}
    if isinstance(value,str):
        return value.replace('is459-aml-full-',PREFIX+'-').replace('/is459/aml/full/','/is459/aml/rerun29/').replace('temporary/full/','temporary/rerun29/')
    return value


def build():
    stack=_replace(copy.deepcopy(original_stack()))
    # Existing shared metadata is observed/reused, not re-created or modified.
    for key in ('FullDatabase','DashboardWorkgroup'):stack['Resources'].pop(key)
    stack['Parameters']['RunId']['Default']=RUN_ID
    stack['Parameters']['ReleaseId']['Default']=RUN_ID
    stack['Parameters']['CodeVersion']['Default']=CODE_VERSION
    for resource in stack['Resources'].values():
        if resource['Type']=='AWS::Glue::Job':resource['Properties']['Tags']['BudgetUSD']=str(BUDGET_USD)
    stack['Resources']['EvaluateJob']['Properties']['NumberOfWorkers']=10
    stack['Resources']['Workflow']['Properties']['StateMachineName']=PREFIX+'-pipeline'
    stack['Description']='Fresh on-demand AML rerun. Isolated jobs/roles/temp paths; existing Catalog/workgroup reused. No processing starts on creation.'
    # Three control invocations occur on the longest path. Timeouts remain finite.
    maximum=(5*45+5*45+10*120+10*45+3*2*10)/60*.44
    stack['Outputs']['ComputeMaximumEstimateUSD']['Value']=str(round(maximum,6))+' compute estimate at reviewed pricing; startup/storage/requests/dashboard separate; not a billing cap.'
    return stack


def dashboard():
    stack=copy.deepcopy(original_dashboard())
    stack['Parameters']['CodeVersion']['Default']=CODE_VERSION
    stack['Resources']['Role']['Properties']['RoleName']=PREFIX+'-dashboard'
    instance=stack['Resources']['Instance']['Properties']
    instance['InstanceInitiatedShutdownBehavior']='terminate'
    user=instance['UserData']['Fn::Base64']['Fn::Sub']
    instance['UserData']['Fn::Base64']['Fn::Sub']=user.replace('set -euo pipefail\n','set -euo pipefail\nshutdown -h +60\n',1)
    for tag in instance['Tags']:
        if tag['Key']=='Name':tag['Value']=PREFIX+'-dashboard'
    return stack


if __name__=='__main__':
    from pathlib import Path
    for name,body in [('rerun29-stack.json',build()),('rerun29-dashboard-stack.json',dashboard())]:
        Path(__file__).with_name(name).write_text(json.dumps(body,indent=2)+'\n')
