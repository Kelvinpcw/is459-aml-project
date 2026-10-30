"""Temporary public read-only dashboard; raw data stays private."""
import copy,json
from pathlib import Path
from build_run30 import dashboard as private_dashboard
STACK_NAME='is459-aml-public30-dashboard'

PROXY=r'''
dnf install -y nginx
cat > /etc/nginx/nginx.conf <<'NGINX'
user nginx;
worker_processes auto;
pid /run/nginx.pid;
error_log /var/log/nginx/error.log;
events { worker_connections 1024; }
http {
  include /etc/nginx/mime.types;
  default_type application/octet-stream;
  map $http_upgrade $connection_upgrade { default upgrade; '' close; }
  limit_conn_zone $binary_remote_addr zone=per_ip:10m;
  limit_req_zone $binary_remote_addr zone=page_requests:10m rate=10r/s;
  server {
    listen 80 default_server;
    server_name _;
    server_tokens off;
    limit_conn per_ip 10;
    location / {
      limit_req zone=page_requests burst=80 nodelay;
      proxy_pass http://127.0.0.1:8501;
      proxy_http_version 1.1;
      proxy_set_header Host $host;
      proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
      proxy_set_header X-Forwarded-Proto $scheme;
      proxy_set_header Upgrade $http_upgrade;
      proxy_set_header Connection $connection_upgrade;
      proxy_read_timeout 180s;
      proxy_buffering off;
    }
  }
}
NGINX
nginx -t
systemctl enable --now nginx
'''

def build():
    t=copy.deepcopy(private_dashboard());r=t['Resources']
    t['Description']='User-authorised temporary public read-only synthetic AML dashboard. HTTP proxy only; manual shutdown; source bucket remains private.'
    r['Role']['Properties']['RoleName']=STACK_NAME
    r['Group']['Properties']['GroupDescription']='Public HTTP dashboard only; no SSH or direct Streamlit ingress'
    r['Group']['Properties']['SecurityGroupIngress']=[{'IpProtocol':'tcp','FromPort':80,'ToPort':80,'CidrIp':'0.0.0.0/0','Description':'User-authorised public read-only dashboard'}]
    instance=r['Instance']['Properties']
    for tag in instance['Tags']:
        if tag['Key']=='Name':tag['Value']=STACK_NAME
    instance['UserData']['Fn::Base64']['Fn::Sub']=instance['UserData']['Fn::Base64']['Fn::Sub'].replace('shutdown -h +60\n','')+PROXY
    instance['InstanceInitiatedShutdownBehavior']='stop'
    t['Outputs']['Access']['Value']='Open the instance public IPv4 address over HTTP. Synthetic published results are publicly visible for the bounded session; raw data and AWS credentials are never served.'
    t['Outputs']['PublicUrl']={'Value':{'Fn::Sub':'http://${Instance.PublicIp}/'}}
    return t

if __name__=='__main__':
    Path(__file__).with_name('public-dashboard-stack.json').write_text(json.dumps(build(),indent=2)+'\n')
