"""Same evaluation rules; replace Cartesian verification with keyed joins."""
import copy,json
from pathlib import Path
from build_stack import BUCKET
ATTEMPT='evaluation-keyed1'


def build():
    path=Path(__file__).with_name('evaluation-resume1-stack.json');prior=json.loads(path.read_text());stack=copy.deepcopy(prior)
    scripts='s3://'+BUCKET+'/scripts/${CodeVersion}/'+ATTEMPT+'/'
    for key,script in [('EvaluateJob','evaluate_distributed.py'),('ControlJob','control.py')]:
        p=stack['Resources'][key]['Properties'];p['Command']['ScriptLocation']={'Fn::Sub':scripts+script};p['DefaultArguments']['--extra-py-files']={'Fn::Sub':scripts+'jobs.zip'}
    stack['Resources']['EvaluateJob']['Properties']['DefaultArguments']['--attempt-id']=ATTEMPT
    report='s3://'+BUCKET+'/quality/evaluation/dataset_version=ibm-hi-medium-b1b99c68b765580f/run_id=${RunId}/analysis_id=q2-full-v2/evaluation_id=eval-full-v2/attempt='+ATTEMPT+'/report.json'
    stack['Resources']['ControlJob']['Properties']['DefaultArguments']['--evaluation-report']={'Fn::Sub':report}
    workflow=copy.deepcopy(stack['Resources']['EvaluationResumeWorkflow']);workflow['Properties']['StateMachineName']='is459-aml-'+ATTEMPT
    stack['Resources']['KeyedEvaluationWorkflow']=workflow;stack['Outputs']['KeyedEvaluationWorkflowArn']={'Value':{'Ref':'KeyedEvaluationWorkflow'}}
    for key,r in prior['Resources'].items():
        if r['Type']=='AWS::IAM::Role' or key in ('PrepareJob','RiskJob','DetectJob','FullDatabase','Workflow','RecoveryWorkflow','EvaluationResumeWorkflow'):
            if r!=stack['Resources'][key]:raise ValueError('Changed approved grant or completed-stage definition')
    return stack

if __name__=='__main__':
    p=Path(__file__).with_name('evaluation-keyed1-stack.json');p.write_text(json.dumps(build(),indent=2)+'\n');print(p)
