"""No real AWS: explicit attempt routing and request-marker duplicate prevention."""
import contextlib,hashlib,io,json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import Mock,patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'deployment'))
import resume_evaluation as driver
from build_keyed_evaluation import build as keyed
from build_evaluation_resume import build as previous
from build_lineage_evaluation import build as lineage

class ResumeDriverTests(unittest.TestCase):
 def test_new_attempt_uses_own_approval_marker_and_prevents_second_start(self):
  for attempt in ('evaluation-keyed1','evaluation-lineage1'):
   with self.subTest(attempt=attempt),tempfile.TemporaryDirectory() as d:
    root=Path(d);reviews=root/'Implementation/aws/reviews';reviews.mkdir(parents=True);deployment=root/'Implementation/deployment';deployment.mkdir()
    templates={'evaluation-keyed1':keyed(),'evaluation-resume1':previous(),'evaluation-lineage1':lineage()}
    for name,value in templates.items():(deployment/(name+'-stack.json')).write_text(json.dumps(value,indent=2)+'\n')
    raw=(deployment/(attempt+'-stack.json')).read_bytes()
    (reviews/(attempt+'-deployment-verification.json')).write_text(json.dumps({'status':'VERIFIED_BEFORE_PROCESSING','workflow_arn':'scoped-workflow'}))
    (reviews/(attempt+'-authorization.json')).write_text(json.dumps({'approved':True,'template_sha256':hashlib.sha256(raw).hexdigest()}))
    (reviews/'full-monitor-latest.json').write_text(json.dumps({'active_paid_resources':[],'guard_total_estimate_usd':16}))
    sts=Mock();sts.get_caller_identity.return_value={'Account':'160885259244'}
    s3=Mock();s3.get_object.side_effect=lambda **kw:{'ETag':'expected','Body':io.BytesIO(b'{"release_id":"pilot-20220901-m00-v1"}')}
    sf=Mock();sf.start_execution.return_value={'executionArn':'new-scoped'}
    clients={'sts':sts,'s3':s3,'stepfunctions':sf,'cloudformation':Mock(),'glue':Mock()};session=Mock();session.client.side_effect=clients.__getitem__
    def save(name,value):(reviews/name).write_text(json.dumps(value))
    with patch.object(driver,'ROOT',root),patch.object(driver,'REV',reviews),patch.object(driver,'save',side_effect=save),patch.object(driver.subprocess,'run'),patch('boto3.Session',return_value=session),patch.object(sys,'argv',['resume','--profile','synthetic','--attempt',attempt,'--phase','start']),contextlib.redirect_stdout(io.StringIO()):
     driver.main()
     with self.assertRaisesRegex(ValueError,'already requested'):driver.main()
    sf.start_execution.assert_called_once();self.assertEqual(sf.start_execution.call_args.kwargs['name'],'full-20261028-'+attempt)
    self.assertTrue((reviews/(attempt+'-request.json')).exists());self.assertTrue((reviews/(attempt+'-start.json')).exists())
    self.assertFalse((reviews/'evaluation-resume1-start.json').exists())
    request=json.loads((reviews/(attempt+'-request.json')).read_text());self.assertAlmostEqual(request['maximum_new_compute_estimate_usd'],driver.ATTEMPTS[attempt][3])

if __name__=='__main__':unittest.main()
