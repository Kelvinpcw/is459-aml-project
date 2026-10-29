"""Offline tests: explicit-profile guard and a version-only local tool check."""
import contextlib,importlib.util,io,json,os,subprocess,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('project_doctor',ROOT/'Implementation/scripts/project_doctor.py')
doctor=importlib.util.module_from_spec(spec);spec.loader.exec_module(doctor)


class LocalDoctorTests(unittest.TestCase):
    def test_all_probes_are_version_only_without_shell_or_login(self):
        commands=[]
        def run(argv,**kw):
            commands.append((argv,kw));return subprocess.CompletedProcess(argv,0,'tool 1.0\n','')
        with patch.object(doctor.shutil,'which',side_effect=lambda name:'/tools/'+name),patch.object(doctor.subprocess,'run',side_effect=run):
            for task in doctor.TASKS:self.assertTrue(doctor.inspect(task)['required_tools_found'])
        self.assertTrue(commands)
        self.assertTrue(all(cmd[1:] in (['--version'],['-version']) for cmd,_ in commands))
        self.assertTrue(all(not kw.get('shell',False) and kw['timeout']==5 for _,kw in commands))

    def test_docs_does_not_probe_aws_and_pipeline_does_not_require_it(self):
        with patch.object(doctor,'probe',side_effect=lambda name,required:{'tool':name,'required':required,'status':'missing' if name=='aws' else 'found','version':''}) as probe:
            self.assertTrue(doctor.inspect('docs')['required_tools_found'])
            self.assertNotIn('aws',[call.args[0] for call in probe.call_args_list])
            self.assertTrue(doctor.inspect('pipeline')['required_tools_found'])
            self.assertFalse(doctor.inspect('dashboard')['required_tools_found'])

    def test_missing_required_tool_exits_nonzero_but_optional_does_not(self):
        with patch.object(doctor.shutil,'which',return_value=None),contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(doctor.main(['--task','docs','--json']),1)
        with patch.object(doctor,'inspect',return_value={'required_tools_found':True}),contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(doctor.main(['--json']),0)

    def test_failed_and_slow_local_commands_are_reported(self):
        with patch.object(doctor.shutil,'which',return_value='/tools/java'),patch.object(doctor.subprocess,'run',return_value=subprocess.CompletedProcess([],1,'','missing runtime')):
            self.assertEqual(doctor.probe('java',True)['status'],'unavailable')
        with patch.object(doctor.shutil,'which',return_value='/tools/aws'),patch.object(doctor.subprocess,'run',side_effect=subprocess.TimeoutExpired('aws',5)):
            self.assertEqual(doctor.probe('aws',True)['status'],'timeout')


class ExplicitProfileGuardTests(unittest.TestCase):
    def run_guard(self,args,region='us-east-1',account='160885259244',failed=False):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);log=root/'calls.jsonl';fake=root/'aws'
            fake.write_text('#!'+sys.executable+'\n'+'''import json,os,sys
with open(os.environ['IS459_TEST_CALLS'],'a') as f:f.write(json.dumps(sys.argv[1:])+'\\n')
if sys.argv[1:3]==['configure','get']:print(os.environ['IS459_TEST_REGION'])
elif sys.argv[1:3]==['sts','get-caller-identity']:
 if os.environ['IS459_TEST_AUTH_FAIL']=='1':sys.exit(1)
 print(os.environ['IS459_TEST_ACCOUNT'])
else:sys.exit(90)
''');fake.chmod(0o755)
            env={**os.environ,'PATH':str(root)+os.pathsep+os.environ.get('PATH',''),'IS459_TEST_CALLS':str(log),'IS459_TEST_REGION':region,'IS459_TEST_ACCOUNT':account,'IS459_TEST_AUTH_FAIL':'1' if failed else '0'}
            result=subprocess.run(['bash',str(ROOT/'Implementation/scripts/check_aws_profile.sh'),*args],capture_output=True,text=True,env=env,check=False)
            return result,[json.loads(line) for line in log.read_text().splitlines()] if log.exists() else []

    def test_no_profile_or_empty_or_extra_profile_makes_no_aws_call(self):
        for args in ([],[''],['one','two']):
            result,calls=self.run_guard(args);self.assertEqual(result.returncode,2);self.assertEqual(calls,[])

    def test_configured_region_is_required_before_any_identity_request(self):
        for region in ('','eu-west-1'):
            result,calls=self.run_guard(['member-project'],region=region)
            self.assertNotEqual(result.returncode,0);self.assertEqual(len(calls),1);self.assertEqual(calls[0],['configure','get','region','--profile','member-project'])

    def test_valid_explicit_identity_passes_with_region_and_profile_on_sts(self):
        result,calls=self.run_guard(['member-project']);self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(calls[1],['sts','get-caller-identity','--profile','member-project','--region','us-east-1','--query','Account','--output','text'])

    def test_wrong_account_and_failed_login_never_fall_back(self):
        for kwargs in ({'account':'111111111111'},{'failed':True}):
            result,calls=self.run_guard(['member-project'],**kwargs);self.assertNotEqual(result.returncode,0)
            self.assertEqual(len(calls),2);self.assertNotIn('default',json.dumps(calls));self.assertNotIn('OK:',result.stdout)


if __name__=='__main__':unittest.main()
