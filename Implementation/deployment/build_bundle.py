"""Freeze and package a new version; never edit an existing release in place."""
import hashlib,json,zipfile,io
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]


def digest(body):return hashlib.sha256(body).hexdigest()
def archive(files):
    buffer=io.BytesIO()
    with zipfile.ZipFile(buffer,'w',compression=zipfile.ZIP_DEFLATED) as z:
        for name,body in sorted(files.items()):
            info=zipfile.ZipInfo(name,date_time=(1980,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED
            z.writestr(info,body)
    return buffer.getvalue()


def build(version='full-v1'):
    import re
    if not re.fullmatch(r'full-v[1-9][0-9]*',version):raise ValueError('Use an explicit new full release version')
    sources={name:(ROOT/'Implementation/jobs'/name).read_bytes() for name in ['q1_risk.py','q2_detect.py','q2_distributed.py','q2_bundle_shards.py','q2_snapshots.py','evaluate_q2.py','evaluate_distributed.py','control.py']}
    sources['prepare.py']=(ROOT/'Implementation/releases/preparation-v2/prepare-v2.py').read_bytes()
    sources['make_q2_input_manifest.py']=(ROOT/'Implementation/scripts/make_q2_input_manifest.py').read_bytes()
    for name in ['__init__.py','release.py']:sources['pipeline/'+name]=(ROOT/'Implementation/pipeline'/name).read_bytes()
    payload={**{k:v for k,v in sources.items() if '/' not in k},'jobs.zip':archive(sources)}
    dashboard={'.streamlit/config.toml':(ROOT/'.streamlit/config.toml').read_bytes(),'requirements-dashboard.txt':(ROOT/'Implementation/dashboard/requirements.txt').read_bytes()}
    for folder in ['dashboard','pipeline']:
        for path in (ROOT/'Implementation'/folder).glob('*.py'):dashboard['Implementation/'+folder+'/'+path.name]=path.read_bytes()
    payload['dashboard.zip']=archive(dashboard)
    target=ROOT/'Implementation/releases'/version
    target.mkdir(exist_ok=False)
    files={}
    for name,body in payload.items():
        (target/name).write_bytes(body);files[name]={'sha256':digest(body),'bytes':len(body),'s3_key':'scripts/'+version+'/'+name}
    manifest={'schema_version':1,'version':version,'files':files,'source_tree_sha256':digest(json.dumps({k:digest(v) for k,v in sorted(sources.items())},sort_keys=True).encode()),'immutable':True}
    (target/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    return manifest

if __name__=='__main__':print(json.dumps(build(),indent=2))
