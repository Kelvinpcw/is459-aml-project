"""Recovery definitions: reuse completed preparation and unchanged IAM grants."""
import copy,json
from pathlib import Path
from build_stack import BUCKET
ROOT=Path(__file__).resolve().parents[2]
ATTEMPT='recovery1'


def build():
    original=json.loads((ROOT/'Implementation/deployment/full-pipeline-stack.json').read_text());stack=copy.deepcopy(original)
    root='s3://'+BUCKET+'/'
    suffix='dataset_version=ibm-hi-medium-b1b99c68b765580f/run_id=${RunId}/'
    q1=root+'quality/q1/'+suffix+'analysis_id=q1-full-v1/attempt='+ATTEMPT+'/report.json'
    q2=root+'quality/q2/'+suffix+'analysis_id=q2-full-v2/attempt='+ATTEMPT+'/report.json'
    for key in ('RiskJob','DetectJob','EvaluateJob','ControlJob'):
        p=stack['Resources'][key]['Properties'];name=p['Command']['ScriptLocation']['Fn::Sub'].rsplit('/',1)[1]
        p['Command']['ScriptLocation']={'Fn::Sub':root+'scripts/${CodeVersion}/'+ATTEMPT+'/'+name}
        p['DefaultArguments']['--extra-py-files']={'Fn::Sub':root+'scripts/${CodeVersion}/'+ATTEMPT+'/jobs.zip'}
        if key in ('RiskJob','DetectJob'):p['DefaultArguments']['--attempt-id']=ATTEMPT
        if key=='EvaluateJob':p['DefaultArguments']['--detector-report']={'Fn::Sub':q2}
        if key=='ControlJob':p['DefaultArguments'].update({'--q1-report':{'Fn::Sub':q1},'--q2-report':{'Fn::Sub':q2}})
    workflow=copy.deepcopy(stack['Resources']['Workflow']);p=workflow['Properties'];p['StateMachineName']='is459-aml-full-'+ATTEMPT
    definition=json.loads(p['DefinitionString']['Fn::Sub'][0]);definition['StartAt']='Branches'
    for key in ('Prepare','MakeManifest'):definition['States'].pop(key)
    definition['Comment']='Recovery after diagnosed export join failure; preparation and manifest reused, frozen rules unchanged.'
    p['DefinitionString']['Fn::Sub'][0]=json.dumps(definition)
    p['DefinitionString']['Fn::Sub'][1].pop('PrepareJob')
    stack['Resources']['RecoveryWorkflow']=workflow;stack['Outputs']['RecoveryWorkflowArn']={'Value':{'Ref':'RecoveryWorkflow'}}
    for key,resource in original['Resources'].items():
        if resource['Type']=='AWS::IAM::Role':
            if resource!=stack['Resources'][key]:raise ValueError('Recovery must not change approved IAM grants')
    return stack


def dashboard():
    stack=json.loads((ROOT/'Implementation/deployment/dashboard-stack.json').read_text())
    original=copy.deepcopy(stack)
    user=stack['Resources']['Instance']['Properties']['UserData']['Fn::Base64']['Fn::Sub']
    user=user.replace('/scripts/${CodeVersion}/dashboard.zip','/published/software/full-v2/dashboard.zip')
    stack['Resources']['Instance']['Properties']['UserData']['Fn::Base64']=user
    assert stack['Resources']['Role']==original['Resources']['Role']
    return stack

if __name__=='__main__':
    for name,body in [('recovery1-stack.json',build()),('dashboard-recovery1-stack.json',dashboard())]:
        (Path(__file__).parent/name).write_text(json.dumps(body,indent=2)+'\n')
