"""Read a compact project-only status/cost snapshot; cancel if reserve nears $30."""
import argparse,datetime,json,subprocess
from pathlib import Path
import boto3
from build_stack import ACCOUNT,REGION,BUCKET
ROOT=Path(__file__).resolve().parents[2]
TERMINAL={'SUCCEEDED','FAILED','STOPPED','TIMEOUT','ERROR','EXPIRED'}


def main():
 p=argparse.ArgumentParser();p.add_argument('--profile',required=True);p.add_argument('--enforce-budget',action='store_true');args=p.parse_args()
 s=boto3.Session(profile_name=args.profile,region_name=REGION)
 if s.client('sts').get_caller_identity()['Account']!=ACCOUNT:raise ValueError('Wrong project account')
 sf=s.client('stepfunctions');glue=s.client('glue');now=datetime.datetime.now(datetime.timezone.utc)
 marker=ROOT/'Implementation/aws/reviews/full-recovery1-start.json'
 if not marker.exists():marker=ROOT/'Implementation/aws/reviews/full-workflow-start.json'
 start=json.loads(marker.read_text())
 execution=sf.describe_execution(executionArn=start['executionArn']);jobs={};compute=0;active=[]
 for stage in ('prepare','risk','detect','evaluate','control'):
  name='is459-aml-full-'+stage;rows=glue.get_job_runs(JobName=name)['JobRuns'];jobs[stage]=[]
  for row in rows:
   running=row['JobRunState'] not in TERMINAL
   seconds=max(row.get('ExecutionTime',0),(now-row['StartedOn']).total_seconds() if running else 0,60)
   workers=row.get('NumberOfWorkers',2);cost=seconds*workers/3600*.44;compute+=cost
   item={'job_name':name,'run_id':row['Id'],'status':row['JobRunState'],'execution_seconds':row.get('ExecutionTime',0),'workers':workers,
     'estimated_compute_usd_including_minimum':round(cost,6),'compute_still_running':running,'started_at':row['StartedOn'].isoformat(),'ended_at':row.get('CompletedOn').isoformat() if row.get('CompletedOn') else None,'error':row.get('ErrorMessage')}
   jobs[stage].append(item)
   if running:active.append(item)
 reserved_output=10 if jobs['detect'] else 0
 estimate=.280623+compute+reserved_output+1
 result={'observed_at_singapore':now.astimezone(datetime.timezone(datetime.timedelta(hours=8))).isoformat(),'execution_arn':start['executionArn'],'execution_status':execution['status'],
   'jobs':jobs,'full_compute_estimate_usd':round(compute,6),'prior_compute_estimate_usd':.280623,'reserved_output_estimate_usd':reserved_output,'other_overhead_reserve_usd':1,
   'guard_total_estimate_usd':round(estimate,6),'total_budget_usd':30,'active_paid_resources':active,'published_release_changes_only_after_success':True,
   'cost_note':'Conservative active elapsed-time and one-minute minimum estimates; output reserve is a bound, not a measured invoice. Other reserve is not a billing cap.'}
 if estimate>=28 and active and args.enforce_budget:
  subprocess.run(['bash','Implementation/scripts/check_aws_profile.sh',args.profile],cwd=ROOT,check=True)
  if execution['status']=='RUNNING':sf.stop_execution(executionArn=start['executionArn'],cause='Conservative project cost plus reserves approached US$30 limit')
  for item in active:glue.batch_stop_job_run(JobName=item['job_name'],JobRunIds=[item['run_id']])
  result['budget_stop_requested']=True
 path=ROOT/'Implementation/aws/reviews/full-monitor-latest.json';path.write_text(json.dumps(result,indent=2)+'\n')
 ledger_path=ROOT/'Implementation/data/aws-operations-20261028/resource-ledger.json'
 if not ledger_path.exists():
  ledger_path.parent.mkdir(parents=True,exist_ok=True);ledger_path.write_bytes((ROOT/'Implementation/aws/resource-ledger.json').read_bytes());ledger=json.loads(ledger_path.read_text());ledger['active_paid_resources']=active
 ledger['full_completion'].update(status=execution['status'],full_processing_started=True,execution_arn=start['executionArn'],observed_at_singapore=result['observed_at_singapore'],estimated_compute_usd=round(compute,6))
 for group in jobs.values():
  for item in group:
   record=next((r for r in ledger['paid_resources_started_by_this_project'] if r['run_id']==item['run_id']),None)
   if record is None:
    record={'service':'glue-job-run',**item};ledger['paid_resources_started_by_this_project'].append(record)
   else:record.update(item)
 ledger_path.write_text(json.dumps(ledger,indent=2)+'\n')
 print(json.dumps({'execution':execution['status'],'jobs':{k:[{'state':r['status'],'seconds':r['execution_seconds'],'error':r['error']} for r in v] for k,v in jobs.items()},
 'compute_estimate_usd':round(compute,4),'guard_total_with_reserves_usd':round(estimate,4),'budget_stop_requested':result.get('budget_stop_requested',False)},indent=2))

if __name__=='__main__':main()
