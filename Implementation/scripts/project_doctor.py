"""Local tool inventory only: no auth, cloud APIs, installation or config reads."""
from __future__ import annotations
import argparse,json,shutil,subprocess,sys

# Fixed, version-only commands. Never expand user input into a shell command.
TOOLS={
    'git':('git','--version'),
    'gh':('gh','--version'),
    'python3.11':('python3.11','--version'),
    'node':('node','--version'),
    'java':('java','-version'),
    'aws':('aws','--version'),
}
TASKS={
    'docs':(('git',),('gh',)),
    'prototype':(('git','node'),('gh',)),
    'dashboard':(('git','python3.11','aws'),('gh',)),
    'pipeline':(('git','python3.11','java'),('gh','aws')),
}


def probe(name,required):
    command=TOOLS[name]
    found=shutil.which(command[0])
    if not found and name=='python3.11' and sys.version_info[:2]==(3,11):found=sys.executable
    row={'tool':name,'required':required,'status':'missing','version':''}
    if not found:return row
    try:
        result=subprocess.run([found,*command[1:]],capture_output=True,text=True,timeout=5,check=False)
    except subprocess.TimeoutExpired:
        return {**row,'status':'timeout'}
    except OSError:
        return {**row,'status':'unavailable'}
    if result.returncode:return {**row,'status':'unavailable'}
    lines=(result.stdout+'\n'+result.stderr).strip().splitlines()
    return {**row,'status':'found','version':lines[0][:200] if lines else 'version not reported'}


def inspect(task):
    required,optional=TASKS[task]
    rows=[probe(name,True) for name in required]+[probe(name,False) for name in optional]
    return {'task':task,'required_tools_found':all(r['status']=='found' for r in rows if r['required']),
            'tools':rows,'aws_api_calls':False,'configuration_changed':False,
            'note':'Tool versions only. Compare with SETUP.md; Python packages, credentials, access and cloud completion are not checked.'}


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--task',choices=TASKS,default='docs')
    parser.add_argument('--json',action='store_true',help='Print the same local inventory as JSON')
    args=parser.parse_args(argv);report=inspect(args.task)
    if args.json:print(json.dumps(report,indent=2))
    else:
        print('Local tool check — '+args.task+' (no login or cloud calls)')
        for row in report['tools']:
            print(f"{row['tool']}: {row['status']} · {'required' if row['required'] else 'optional'}"+((' · '+row['version']) if row['version'] else ''))
        print(report['note'])
        print('Next: TEAM_START_HERE.md and Implementation/SETUP.md. Ask before installing or configuring anything.')
    return 0 if report['required_tools_found'] else 1


if __name__=='__main__':raise SystemExit(main())
