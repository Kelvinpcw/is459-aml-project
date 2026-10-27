"""Private on-demand dashboard: no inbound ports, SSM tunnel, delete root disk."""
import json
from pathlib import Path
from build_stack import ACCOUNT,REGION,BUCKET,allow,trust,ref,attr,sub


def build():
 arn='arn:aws:s3:::'+BUCKET
 policy={'Version':'2012-10-17','Statement':[
  allow('s3:GetBucketLocation',arn),
  {'Effect':'Allow','Action':'s3:ListBucket','Resource':arn,'Condition':{'StringLike':{'s3:prefix':['published/*','gold/risk/*','gold/cases/*','evaluation/*','query-results/dashboard/*',sub('scripts/${CodeVersion}/dashboard.zip')]}}},
  allow('s3:GetObject',[sub(arn+'/'+key) for key in ['published/*','gold/risk/*','gold/cases/*','evaluation/*/metrics.json','query-results/dashboard/*','scripts/${CodeVersion}/dashboard.zip']]),
  allow(['s3:PutObject','s3:AbortMultipartUpload'],arn+'/query-results/dashboard/*'),
  allow(['athena:StartQueryExecution','athena:GetQueryExecution','athena:GetQueryResults','athena:StopQueryExecution'],'arn:aws:athena:'+REGION+':'+ACCOUNT+':workgroup/is459-aml-dashboard'),
  allow(['glue:GetDatabase','glue:GetTable','glue:GetPartitions','glue:BatchGetPartition'],['arn:aws:glue:'+REGION+':'+ACCOUNT+':catalog']+['arn:aws:glue:'+REGION+':'+ACCOUNT+':'+resource for resource in ['database/is459_aml_dev','database/is459_aml_full','table/is459_aml_dev/q1_*','table/is459_aml_dev/q2_*','table/is459_aml_full/q1_*','table/is459_aml_full/q2_*']]),
  {'Effect':'Deny','Action':'s3:GetObject*','Resource':[arn+'/raw/*',arn+'/curated/*',arn+'/references/*']} ]}
 userdata='''#!/bin/bash
set -euo pipefail
dnf install -y python3.11 python3.11-pip
mkdir -p /opt/is459-aml /root/.aws
printf '[profile project-instance]\nregion=us-east-1\n' > /root/.aws/config
aws s3 cp s3://'''+BUCKET+'''/scripts/${CodeVersion}/dashboard.zip /opt/is459-dashboard.zip --profile project-instance --region us-east-1
python3.11 -m zipfile -e /opt/is459-dashboard.zip /opt/is459-aml
python3.11 -m venv /opt/is459-aml/venv
/opt/is459-aml/venv/bin/pip install --no-cache-dir -r /opt/is459-aml/requirements-dashboard.txt
chown -R ec2-user:ec2-user /opt/is459-aml
cat > /etc/systemd/system/is459-dashboard.service <<'SERVICE'
[Unit]
Description=IS459 read-only AML dashboard
After=network-online.target
[Service]
User=ec2-user
WorkingDirectory=/opt/is459-aml
Environment=AML_USE_INSTANCE_ROLE=1
Environment=AML_ATHENA_WORKGROUP=is459-aml-dashboard
Environment=AWS_DEFAULT_REGION=us-east-1
ExecStart=/opt/is459-aml/venv/bin/python -m streamlit run Implementation/dashboard/app.py --server.address=127.0.0.1 --server.port=8501
Restart=on-failure
RestartSec=10
NoNewPrivileges=true
PrivateTmp=true
[Install]
WantedBy=multi-user.target
SERVICE
systemctl daemon-reload
systemctl enable --now is459-dashboard
'''
 resources={
 'Role':{'Type':'AWS::IAM::Role','Properties':{'RoleName':'is459-aml-dashboard','AssumeRolePolicyDocument':trust('ec2.amazonaws.com'),'ManagedPolicyArns':['arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore'],'Policies':[{'PolicyName':'read-published-analysis-only','PolicyDocument':policy}]}},
 'Profile':{'Type':'AWS::IAM::InstanceProfile','Properties':{'Roles':[ref('Role')]}},
 'Group':{'Type':'AWS::EC2::SecurityGroup','Properties':{'GroupDescription':'IS459 SSM-only dashboard; no inbound access','VpcId':ref('VpcId'),'SecurityGroupIngress':[],
  'SecurityGroupEgress':[{'IpProtocol':'tcp','FromPort':p,'ToPort':p,'CidrIp':'0.0.0.0/0','Description':'Package registry and AWS HTTPS' if p==443 else 'Official package repository redirects'} for p in (443,80)],'Tags':[{'Key':'Project','Value':'is459-aml'}]}},
 'Instance':{'Type':'AWS::EC2::Instance','Properties':{'ImageId':ref('AmiId'),'InstanceType':'t3.small','IamInstanceProfile':ref('Profile'),
   'MetadataOptions':{'HttpTokens':'required','HttpPutResponseHopLimit':1},'NetworkInterfaces':[{'DeviceIndex':'0','AssociatePublicIpAddress':True,'SubnetId':ref('SubnetId'),'GroupSet':[ref('Group')]}],
   'BlockDeviceMappings':[{'DeviceName':'/dev/xvda','Ebs':{'VolumeSize':8,'VolumeType':'gp3','Encrypted':True,'DeleteOnTermination':True}}],
   'CreditSpecification':{'CPUCredits':'standard'},'UserData':{'Fn::Base64':sub(userdata)},'Tags':[{'Key':'Name','Value':'is459-aml-dashboard'},{'Key':'Project','Value':'is459-aml'}]}}}
 return {'AWSTemplateFormatVersion':'2010-09-09','Description':'Temporary SSM-only AML dashboard. Delete this stack after validation to remove instance, disk and public IPv4 charges.',
  'Parameters':{'CodeVersion':{'Type':'String','Default':'full-v1','AllowedPattern':'full-v[1-9][0-9]*'},'VpcId':{'Type':'AWS::EC2::VPC::Id'},'SubnetId':{'Type':'AWS::EC2::Subnet::Id'},'AmiId':{'Type':'AWS::SSM::Parameter::Value<AWS::EC2::Image::Id>','Default':'/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64'}},
  'Resources':resources,'Outputs':{'InstanceId':{'Value':ref('Instance')},'Access':{'Value':'Use AWS-StartPortForwardingSession through SSM, local port 8502 to instance port 8501. No inbound ports are open.'}}}

if __name__=='__main__':
 out=Path(__file__).with_name('dashboard-stack.json');out.write_text(json.dumps(build(),indent=2)+'\n');print(out)
