from pathlib import Path
import importlib.util,json,unittest,sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'deployment'))
from build_stack import build
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'jobs'))
from q2_snapshots import schedule

class DeploymentTests(unittest.TestCase):
 def test_fresh_jobs_have_no_retry_and_bounded_worst_case_compute(self):
  stack=build();jobs=[r['Properties'] for r in stack['Resources'].values() if r['Type']=='AWS::Glue::Job']
  cost=0
  for job in jobs:
   self.assertEqual(job['MaxRetries'],0);self.assertEqual(job['ExecutionProperty']['MaxConcurrentRuns'],1)
   self.assertFalse(job['JobRunQueuingEnabled'])
   cost+=job['NumberOfWorkers']*job['Timeout']/60*.44*(3 if job['Name'].endswith('control') else 1)
  self.assertAlmostEqual(cost,14.19)
  self.assertLess(cost,30*.5)
  self.assertFalse(any(r['Type']=='AWS::Events::Rule' for r in stack['Resources'].values()))
 def test_q2_role_has_no_label_reference_or_q1_read_permission(self):
  stack=build();props=stack['Resources']['DetectRole']['Properties']
  policy=props['Policies'][0]['PolicyDocument'];allow=[s for s in policy['Statement'] if s['Effect']=='Allow']
  text=json.dumps(allow)
  self.assertNotIn('references/',text);self.assertNotIn('gold/risk/',text)
  deny=[s for s in policy['Statement'] if s['Effect']=='Deny'][0]
  self.assertTrue(any('/references/' in r for r in deny['Resource']))
  self.assertNotEqual(stack['Resources']['DetectJob']['Properties']['Role'],stack['Resources']['RiskJob']['Properties']['Role'])
 def test_recovery_reuses_preparation_and_every_approved_role(self):
  from build_recovery import build as recovery,dashboard
  original=build();stack=recovery()
  for key,value in original['Resources'].items():
   if value['Type']=='AWS::IAM::Role':self.assertEqual(value,stack['Resources'][key])
  definition=json.loads(stack['Resources']['RecoveryWorkflow']['Properties']['DefinitionString']['Fn::Sub'][0])
  self.assertNotIn('Prepare',definition['States']);self.assertNotIn('MakeManifest',definition['States'])
  self.assertEqual(definition['StartAt'],'Branches')
  self.assertIn('attempt=recovery1',stack['Resources']['EvaluateJob']['Properties']['DefaultArguments']['--detector-report']['Fn::Sub'])
  from build_dashboard_stack import build as base_dashboard
  self.assertEqual(base_dashboard()['Resources']['Role'],dashboard()['Resources']['Role'])

 def test_evaluation_resume_has_only_two_tasks_and_unchanged_grants(self):
  from build_evaluation_resume import build as resume,MAXIMUM_COMPUTE_USD
  from build_recovery import build as recovery
  old=recovery();stack=resume()
  for key,value in old['Resources'].items():
   if value['Type']=='AWS::IAM::Role' or key in ('PrepareJob','RiskJob','DetectJob','FullDatabase','RecoveryWorkflow','Workflow'):
    self.assertEqual(value,stack['Resources'][key])
  definition=json.loads(stack['Resources']['EvaluationResumeWorkflow']['Properties']['DefinitionString']['Fn::Sub'][0])
  self.assertEqual(set(definition['States']),{'Evaluate','Publish','Failed'})
  self.assertEqual(definition['StartAt'],'Evaluate');self.assertEqual(definition['TimeoutSeconds'],4200)
  self.assertTrue(all('Retry' not in s for s in definition['States'].values()))
  self.assertEqual(stack['Resources']['EvaluateJob']['Properties']['DefaultArguments']['--attempt-id'],'evaluation-resume1')
  self.assertIn('attempt=evaluation-resume1/report.json',stack['Resources']['ControlJob']['Properties']['DefaultArguments']['--evaluation-report']['Fn::Sub'])
  self.assertAlmostEqual(MAXIMUM_COMPUTE_USD,1.7966666667)

 def test_dashboard_validation_self_terminates_without_new_grants(self):
  from build_dashboard_validation import build as validate
  from build_recovery import dashboard
  original=dashboard();stack=validate();instance=stack['Resources']['Instance']['Properties']
  self.assertEqual(original['Resources']['Role'],stack['Resources']['Role'])
  self.assertEqual(instance['InstanceInitiatedShutdownBehavior'],'terminate')
  self.assertIn('shutdown -h +60',instance['UserData']['Fn::Base64'])
  self.assertTrue(instance['BlockDeviceMappings'][0]['Ebs']['DeleteOnTermination'])
  self.assertEqual(stack['Resources']['Group']['Properties']['SecurityGroupIngress'],[])

 def test_schedule_overlaps_and_preserves_full_daily_history(self):
  windows=schedule('2022-09-02T00:00:00','2022-09-29T00:00:00')
  self.assertEqual(len(windows),28)
  self.assertEqual((windows[1][0]-windows[0][0]).days,1)
  self.assertEqual((windows[0][1]-windows[0][0]).days,7)
  self.assertLess(windows[1][0],windows[0][1])
  with self.assertRaises(ValueError):schedule('2022-09-02T00:01:00','2022-09-29T00:00:00')

if __name__=='__main__':unittest.main()
