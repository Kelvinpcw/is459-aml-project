import json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import Mock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'deployment'))
from deploy import execution_arns,stop_owned_processing,EXECUTION_MARKERS

class ShutdownTests(unittest.TestCase):
 def test_old_terminal_executions_do_not_hide_active_evaluator_resume(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);arns=[]
   for marker,name in zip(EXECUTION_MARKERS,('full-pipeline','full-recovery1','evaluation-resume1')):
    arn='arn:aws:states:us-east-1:160885259244:execution:is459-aml-'+name+':fixture';arns.append(arn)
    (root/marker).write_text(json.dumps({'executionArn':arn}))
   sf=Mock();sf.describe_execution.side_effect=lambda **kw:{'status':dict(zip(arns,('FAILED','ABORTED','RUNNING')))[kw['executionArn']]}
   glue=Mock();glue.get_job_runs.side_effect=lambda **kw:{'JobRuns':[{'Id':'owned-eval','JobRunState':'RUNNING'}] if kw['JobName']=='is459-aml-full-evaluate' else []}
   result=stop_owned_processing(sf,glue,root)
   sf.stop_execution.assert_called_once_with(executionArn=arns[-1],cause='User project cleanup or budget control')
   glue.batch_stop_job_run.assert_called_once_with(JobName='is459-aml-full-evaluate',JobRunIds=['owned-eval'])
   self.assertEqual(execution_arns(root),arns);self.assertTrue(result['terminal_verification_still_required'])
 def test_marker_cannot_target_another_account_or_unrelated_workflow(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d)
   for arn in ('arn:aws:states:us-east-1:372014757586:execution:is459-aml-other:run','arn:aws:states:us-east-1:160885259244:execution:unrelated:run'):
    (root/EXECUTION_MARKERS[0]).write_text(json.dumps({'executionArn':arn}))
    with self.assertRaises(ValueError):execution_arns(root)

if __name__=='__main__':unittest.main()
