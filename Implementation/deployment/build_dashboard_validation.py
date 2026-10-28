"""Temporary private validation server with a one-hour terminate safety timer."""
import copy,json
from pathlib import Path
from build_recovery import dashboard


def build():
    original=dashboard();stack=copy.deepcopy(original)
    instance=stack['Resources']['Instance']['Properties']
    instance['InstanceInitiatedShutdownBehavior']='terminate'
    userdata=instance['UserData']['Fn::Base64']
    userdata=userdata.replace('/published/software/full-v2/dashboard.zip','/published/software/dashboard-v1/dashboard.zip')
    instance['UserData']['Fn::Base64']=userdata.replace('set -euo pipefail\n','set -euo pipefail\n# One-time safety timer; normal cleanup deletes the stack sooner.\nshutdown -h +60\n',1)
    assert stack['Resources']['Role']==original['Resources']['Role']
    return stack

if __name__=='__main__':
    p=Path(__file__).with_name('dashboard-validation-stack.json');p.write_text(json.dumps(build(),indent=2)+'\n');print(p)
