import json,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'deployment'))
import build_rerun

class FreshRerunDefinitionTests(unittest.TestCase):
    def test_isolated_names_and_existing_shared_metadata_reused(self):
        t=build_rerun.build();r=t['Resources']
        self.assertNotIn('FullDatabase',r);self.assertNotIn('DashboardWorkgroup',r)
        for value in r.values():
            if value['Type']=='AWS::Glue::Job':
                p=value['Properties'];self.assertTrue(p['Name'].startswith(build_rerun.PREFIX+'-'))
                self.assertEqual(p['MaxRetries'],0);self.assertEqual(p['ExecutionProperty']['MaxConcurrentRuns'],1)
                self.assertIn('temporary/rerun29/',p['DefaultArguments']['--TempDir'])
            if value['Type']=='AWS::IAM::Role':self.assertTrue(value['Properties']['RoleName'].startswith(build_rerun.PREFIX+'-'))
        self.assertNotIn('is459-aml-full-',json.dumps(r))
        self.assertEqual(t['Parameters']['RunId']['Default'],build_rerun.RUN_ID)

    def test_frozen_detection_windows_and_label_denies_unchanged(self):
        r=build_rerun.build()['Resources'];detect=r['DetectJob']['Properties'];args=detect['DefaultArguments']
        self.assertEqual(args['--first-snapshot-end'],'2022-09-02T00:00:00');self.assertEqual(args['--last-snapshot-end'],'2022-09-29T00:00:00')
        self.assertEqual(args['--max-cycle-degree'],'64');self.assertEqual(args['--max-output-cost-usd'],'10')
        statements=r['DetectRole']['Properties']['Policies'][0]['PolicyDocument']['Statement']
        denied=next(x['Resource'] for x in statements if x['Effect']=='Deny')
        for prefix in ('raw/','references/','gold/risk/','evaluation/','quality/evaluation/'):
            self.assertTrue(any(prefix in arn for arn in denied))
        self.assertEqual(r['EvaluateJob']['Properties']['NumberOfWorkers'],10)

    def test_full_path_no_retry_and_cas_publication(self):
        definition=json.loads(build_rerun.build()['Resources']['Workflow']['Properties']['DefinitionString']['Fn::Sub'][0])
        self.assertEqual(definition['StartAt'],'Prepare');self.assertIn('MakeManifest',definition['States'])
        self.assertNotIn('Retry',json.dumps(definition))
        publish=definition['States']['Publish'];self.assertEqual(publish['Parameters']['Arguments']['--expected-pointer-etag.$'],'$.expected_pointer_etag')
        self.assertLessEqual(definition['TimeoutSeconds'],16200)

    def test_private_dashboard_guard_and_latest_package(self):
        r=build_rerun.dashboard()['Resources'];p=r['Instance']['Properties']
        self.assertEqual(p['InstanceInitiatedShutdownBehavior'],'terminate');self.assertTrue(p['BlockDeviceMappings'][0]['Ebs']['DeleteOnTermination'])
        self.assertEqual(r['Group']['Properties']['SecurityGroupIngress'],[])
        user=p['UserData']['Fn::Base64']['Fn::Sub'];self.assertIn('shutdown -h +60',user);self.assertIn('/scripts/${CodeVersion}/dashboard.zip',user)
        self.assertEqual(r['Role']['Properties']['RoleName'],build_rerun.PREFIX+'-dashboard')

    def test_invalid_private_plan_is_rejected_before_any_identity_or_cloud_call(self):
        import hashlib,tempfile
        from unittest.mock import patch
        import rerun
        raw=(rerun.ROOT/'Implementation/deployment/rerun29-stack.json').read_bytes()
        valid={'approved':True,'budget_usd':90,'run_id':build_rerun.RUN_ID,'code_version':build_rerun.CODE_VERSION,'template_sha256':hashlib.sha256(raw).hexdigest()}
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'plan.json'
            for change in ({'approved':False},{'budget_usd':91},{'budget_usd':30},{'run_id':'old-run'},{'code_version':'full-v1'},{'template_sha256':'0'*64}):
                path.write_text(json.dumps({**valid,**change}))
                with patch.object(sys,'argv',['rerun.py','--profile','fixture','--plan',str(path),'--phase','start']),patch.object(rerun,'identity') as login:
                    with self.assertRaises(ValueError):rerun.main()
                    login.assert_not_called()

    def test_nested_role_substitutions_resolve_only_this_run_and_version(self):
        import rerun
        data={'Resource':[{'Fn::Sub':'s3://bucket/scripts/${CodeVersion}/x.py'},{'Fn::Sub':'s3://bucket/run_id=${RunId}/'}]}
        actual=rerun.resolve(data,{'CodeVersion':build_rerun.CODE_VERSION,'RunId':build_rerun.RUN_ID})
        self.assertEqual(actual,{'Resource':['s3://bucket/scripts/full-v6/x.py','s3://bucket/run_id=full-20261029-v1/']})

if __name__=='__main__':unittest.main()
