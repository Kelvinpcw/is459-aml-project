import hashlib,json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'deployment'))
import build_run30,run30,upload_input

class WholeRunTests(unittest.TestCase):
    def test_maintained_resource_set_and_fresh_input_scope(self):
        root=Path(__file__).resolve().parents[1]
        old=json.loads((root/'deployment/full-maintained-stack.json').read_text())
        new=build_run30.build()
        self.assertEqual(set(old['Resources']),set(new['Resources']))
        self.assertEqual(new['Resources']['PrepareJob']['Properties']['DefaultArguments']['--input-root'],'s3://is459-aml-g2team7-160885259244-us-east-1/raw/full-20261030-v1')
        prep=json.dumps(new['Resources']['PrepareRole'])
        self.assertNotIn('raw/full-v1',prep);self.assertIn('raw/full-20261030-v1',prep)
        self.assertEqual(new['Resources']['FullDatabase'],old['Resources']['FullDatabase'])
        self.assertEqual(new['Resources']['DashboardWorkgroup'],old['Resources']['DashboardWorkgroup'])

    def test_revoked_or_stale_plan_fails_before_cloud(self):
        raw=(run30.ROOT/'Implementation/deployment/run30-stack.json').read_bytes()
        valid={'approved':True,'budget_usd':90,'run_id':build_run30.RUN_ID,'code_version':build_run30.CODE_VERSION,'template_sha256':hashlib.sha256(raw).hexdigest()}
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'plan.json'
            for diff in ({'approved':False},{'run_id':'full-20261029-v1'},{'budget_usd':91},{'template_sha256':'0'*64}):
                p.write_text(json.dumps({**valid,**diff}))
                with patch.object(sys,'argv',['run30.py','--profile','fixture','--plan',str(p),'--phase','start']),patch.object(run30,'identity') as identity:
                    with self.assertRaises(ValueError):run30.main()
                    identity.assert_not_called()

    def test_valid_new_plan_reaches_identity_with_generated_new_template(self):
        raw=(run30.ROOT/'Implementation/deployment/run30-stack.json').read_bytes()
        valid={'approved':True,'budget_usd':90,'run_id':build_run30.RUN_ID,'code_version':build_run30.CODE_VERSION,'template_sha256':hashlib.sha256(raw).hexdigest()}
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'plan.json';p.write_text(json.dumps(valid))
            with patch.object(sys,'argv',['run30.py','--profile','fixture','--plan',str(p),'--phase','upload']),patch.object(run30,'identity',side_effect=RuntimeError('fixture identity reached')) as identity:
                with self.assertRaisesRegex(RuntimeError,'fixture identity reached'):run30.main()
                identity.assert_called_once_with('fixture')

    def test_label_isolation_and_frozen_thresholds(self):
        from build_rerun import build
        old=build();new=build_run30.build();a=old['Resources']['DetectJob']['Properties']['DefaultArguments'];b=new['Resources']['DetectJob']['Properties']['DefaultArguments']
        for key in ['--first-snapshot-end','--last-snapshot-end','--max-cycle-degree','--max-cycle-path-rows','--max-output-cost-usd']:self.assertEqual(a[key],b[key])
        denied=json.dumps(new['Resources']['DetectRole'])
        for prefix in ['raw/','references/','gold/risk/','evaluation/']:self.assertIn(prefix,denied)
        definition=json.loads(new['Resources']['Workflow']['Properties']['DefinitionString']['Fn::Sub'][0])
        self.assertEqual(definition['StartAt'],'Prepare');self.assertNotIn('Retry',json.dumps(definition))
        self.assertEqual(definition['States']['Publish']['Parameters']['Arguments']['--expected-pointer-etag.$'],'$.expected_pointer_etag')

    def test_dashboard_bound_and_source_upload_prefix_guard(self):
        r=build_run30.dashboard()['Resources'];instance=r['Instance']['Properties']
        self.assertEqual(instance['InstanceInitiatedShutdownBehavior'],'terminate')
        self.assertIn('shutdown -h +60',instance['UserData']['Fn::Base64']['Fn::Sub'])
        self.assertEqual(r['Group']['Properties']['SecurityGroupIngress'],[])
        with patch.object(sys,'argv',['upload_input.py','--profile','fixture','--prefix','gold/']),patch.object(upload_input.subprocess,'run') as cloud:
            with self.assertRaises(ValueError):upload_input.main()
            cloud.assert_not_called()

if __name__=='__main__':unittest.main()
