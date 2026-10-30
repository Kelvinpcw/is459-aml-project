"""Delete only an approved pre-run inventory after a verified replacement release."""
import argparse,hashlib,json,sys
from pathlib import Path
from urllib.parse import urlparse
from build_stack import BUCKET
from run30 import identity
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from pipeline.release import load_current,verify_ref
ALLOWED=('curated/','evaluation/','gold/','manifests/','quality/','quarantine/','references/labels/','query-results/','temporary/','published/releases/')


def candidates(objects,run):
    result=[];seen=set()
    for row in objects:
        key=row['Key']
        if key in seen or not key.startswith(ALLOWED) or any(x in key.split('/') for x in ('.','..')):
            raise ValueError('Unapproved, duplicate or unsafe cleanup key')
        if 'run_id='+run+'/' in key or key.startswith('published/releases/'+run+'/'):
            raise ValueError('Current run must never be a cleanup candidate')
        if not row.get('ETag') or row['ETag'].strip('"')=='*':raise ValueError('Require exact object ETag')
        seen.add(key);result.append({'Key':key,'ETag':row['ETag'].strip('"')})
    return result


def main():
    p=argparse.ArgumentParser();p.add_argument('--profile',required=True);p.add_argument('--plan',type=Path,required=True);p.add_argument('--inventory',type=Path,required=True);p.add_argument('--execute',action='store_true');a=p.parse_args()
    plan=json.loads(a.plan.read_text());folder=a.plan.parent;raw=a.inventory.read_bytes()
    if plan.get('approved') is not True or not plan.get('cleanup_old_outputs_after_new_release_validated'):raise ValueError('Missing scoped cleanup approval')
    if hashlib.sha256(raw).hexdigest()!=plan.get('old_inventory_sha256'):raise ValueError('Inventory changed since approval')
    objects=json.loads(raw);items=candidates(objects,plan['run_id'])
    dashboard=json.loads((folder/'dashboard-verified.json').read_text())
    if dashboard.get('status')!='PASSED' or dashboard.get('release_id')!=plan['run_id']:raise ValueError('Verify EC2 dashboard before removing prior outputs')
    session=identity(a.profile);s3=session.client('s3');glue=session.client('glue')
    release=load_current(s3)
    if release['release_id']!=plan['run_id']:raise ValueError('Replacement release not current')
    for ref in release['reports'].values():
        if verify_ref(s3,ref)['status']!='PASSED':raise ValueError('Replacement stage incomplete')
    pointer=s3.get_object(Bucket=BUCKET,Key='published/current.json')['ETag']
    if s3.get_bucket_versioning(Bucket=BUCKET).get('Status'):raise ValueError('Versioned bucket needs separate version cleanup review')
    print('Exact old-output candidates:',len(items),'execute:',a.execute,flush=True)
    if not a.execute:return
    evidence=[]
    for offset in range(0,len(items),1000):
        if s3.head_object(Bucket=BUCKET,Key='published/current.json')['ETag']!=pointer:raise ValueError('Publication changed during cleanup')
        response=s3.delete_objects(Bucket=BUCKET,Delete={'Objects':items[offset:offset+1000],'Quiet':False})
        evidence.append(response)
        (folder/'output-deletion-progress.json').write_text(json.dumps(evidence,default=str,indent=2)+'\n')
        if response.get('Errors'):raise ValueError('Conditional deletion conflict; inspect private record')
        print('Deleted old-output batch',offset//1000+1,flush=True)
    # Verify absence by fresh LIST, without expensive per-object HEAD requests.
    remaining=set()
    for prefix in ALLOWED:
        for page in s3.get_paginator('list_objects_v2').paginate(Bucket=BUCKET,Prefix=prefix):
            remaining.update(row['Key'] for row in page.get('Contents',[]))
    overlap=remaining.intersection(x['Key'] for x in items)
    if overlap:raise ValueError('Old objects remain; inspect without broadening deletion')
    if load_current(s3)['release_id']!=plan['run_id']:raise ValueError('Publication changed after cleanup')
    result={'status':'PASSED','old_objects_deleted':len(items),'current_release_verified':True,'remaining_generated_object_count':len(remaining),'source_or_software_deleted':False}
    (folder/'output-deletion-verified.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))

if __name__=='__main__':main()
