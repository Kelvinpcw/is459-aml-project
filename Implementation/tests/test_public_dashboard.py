import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'deployment'))
from build_public_dashboard import build
class PublicDashboardTests(unittest.TestCase):
    def test_public_proxy_only_keeps_instance_and_source_boundaries(self):
        r=build()['Resources'];p=r['Instance']['Properties'];ingress=r['Group']['Properties']['SecurityGroupIngress']
        self.assertEqual([(x['FromPort'],x['ToPort']) for x in ingress],[(80,80)])
        user=p['UserData']['Fn::Base64']['Fn::Sub']
        self.assertIn('--server.address=127.0.0.1',user)
        self.assertIn('proxy_set_header Upgrade $http_upgrade',user)
        self.assertIn('proxy_pass http://127.0.0.1:8501',user)
        self.assertNotIn('shutdown -h +60',user);self.assertEqual(p['InstanceInitiatedShutdownBehavior'],'stop')
        self.assertTrue(p['BlockDeviceMappings'][0]['Ebs']['DeleteOnTermination'])
        deny=next(x for x in r['Role']['Properties']['Policies'][0]['PolicyDocument']['Statement'] if x['Effect']=='Deny')
        for name in ['raw/','curated/','references/']:self.assertTrue(any(name in x for x in deny['Resource']))
    def test_no_processing_or_storage_resources(self):
        t=build();self.assertEqual({x['Type'] for x in t['Resources'].values()},{'AWS::IAM::Role','AWS::IAM::InstanceProfile','AWS::EC2::SecurityGroup','AWS::EC2::Instance'})
if __name__=='__main__':unittest.main()
