"""Prepare evaluator→publication only; no deployment or execution on import."""
import copy,json
from pathlib import Path
from build_recovery import build as recovery_stack
from build_stack import BUCKET
ATTEMPT='evaluation-resume1'
MAXIMUM_COMPUTE_USD=5*45/60*.44+2*10/60*.44


def build():
    stack=recovery_stack();prior=copy.deepcopy(stack)
    root='s3://'+BUCKET+'/'
    scripts=root+'scripts/${CodeVersion}/'+ATTEMPT+'/'
    quality=root+'quality/evaluation/dataset_version=ibm-hi-medium-b1b99c68b765580f/run_id=${RunId}/analysis_id=q2-full-v2/evaluation_id=eval-full-v2/attempt='+ATTEMPT+'/report.json'
    for key,script in [('EvaluateJob','evaluate_distributed.py'),('ControlJob','control.py')]:
        props=stack['Resources'][key]['Properties']
        props['Command']['ScriptLocation']={'Fn::Sub':scripts+script}
        props['DefaultArguments']['--extra-py-files']={'Fn::Sub':scripts+'jobs.zip'}
    stack['Resources']['EvaluateJob']['Properties']['DefaultArguments']['--attempt-id']=ATTEMPT
    stack['Resources']['ControlJob']['Properties']['DefaultArguments']['--evaluation-report']={'Fn::Sub':quality}
    workflow=copy.deepcopy(stack['Resources']['RecoveryWorkflow']);props=workflow['Properties']
    props['StateMachineName']='is459-aml-'+ATTEMPT
    definition=json.loads(props['DefinitionString']['Fn::Sub'][0])
    definition['StartAt']='Evaluate';definition['TimeoutSeconds']=4200
    definition['Comment']='One evaluator and one conditional publisher; reuse completed preparation/Q1/Q2/Catalog. No retries or schedules.'
    definition['States']={k:v for k,v in definition['States'].items() if k in ('Evaluate','Publish','Failed')}
    props['DefinitionString']['Fn::Sub']=[json.dumps(definition),{k:v for k,v in props['DefinitionString']['Fn::Sub'][1].items() if k in ('EvaluateJob','ControlJob')}]
    stack['Resources']['EvaluationResumeWorkflow']=workflow
    stack['Outputs']['EvaluationResumeWorkflowArn']={'Value':{'Ref':'EvaluationResumeWorkflow'}}
    stack['Outputs']['EvaluationResumeMaximumComputeEstimateUSD']={'Value':f'{MAXIMUM_COMPUTE_USD:.6f} at the reviewed0.44/DPU-hour, before other overhead; estimate only.'}
    for key,resource in prior['Resources'].items():
        if resource['Type']=='AWS::IAM::Role' and stack['Resources'][key]!=resource:raise ValueError('Evaluation resume must not change IAM grants')
    for key in ('PrepareJob','RiskJob','DetectJob','FullDatabase','RecoveryWorkflow','Workflow'):
        if stack['Resources'][key]!=prior['Resources'][key]:raise ValueError('Do not change completed stage definitions: '+key)
    return stack

if __name__=='__main__':
    path=Path(__file__).with_name('evaluation-resume1-stack.json');path.write_text(json.dumps(build(),indent=2)+'\n');print(path)
