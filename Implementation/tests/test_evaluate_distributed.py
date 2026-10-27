from pathlib import Path
from dataclasses import asdict
from datetime import date
import sys,unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'jobs'))
sys.path.insert(0,str(Path(__file__).resolve().parent))
from test_q2_distributed import DistributedTests
from test_q2_detect import CONFIG,transaction,manifest
from q2_distributed import DistributedConfig,detect
from evaluate_distributed import evaluate,validate_calibration
from pyspark.sql import functions as F,types as T

class WiderEvaluationTests(DistributedTests):
 # Deliberately do not inherit the detector test methods.
 test_distributed_relations_match_independent_driver_oracle_across_minute_boundary=None
 test_explicit_cycle_degree_exclusions_preserve_complete_fan_evidence=None
 def test_full_eligible_population_reference_recovery_and_exact_baseline(self):
  rows=[transaction(str(i),'H',f'P{i}',minute=i) for i in range(5)]+[transaction('self','H','H')]
  facts=self.frame(rows).withColumn('event_date',F.to_date('event_time'))
  config=DistributedConfig(**{k:getattr(CONFIG,k) for k in ('dataset_version','run_id','analysis_id','window_start','window_end','snapshot_cutoff')})
  handoff=manifest(rows);handoff['fact_columns']=facts.columns
  index,pairs,evidence,stats=detect(facts,handoff,config)
  labels=facts.select('source_id','dataset_version','run_id','event_date').withColumn('is_laundering',F.when(F.col('source_id')=='self',0).otherwise(1))
  prep={'accepted_rows':6,'accepted_by_format':[{'payment_format':'Bitcoin','transactions':6,'labelled_laundering':5}]}
  report={'status':'PASSED','rule_version':'structural-v2','detector_received_labels':False,'config':asdict(config),'statistics':stats}
  annotations=[{'attempt_id':'fixture:1','annotation_type':'FAN-OUT','transactions':[{k:r[k] for k in ['event_time','sender_bank','sender_account','receiver_bank','receiver_account','amount_paid','amount_received','payment_currency','receiving_currency','payment_format']} for r in rows[:5]]}]
  result=evaluate(facts,labels,index,pairs,evidence,prep,report,annotations)
  self.assertEqual(result['detector_transaction_metrics']['population'],6)
  self.assertEqual(result['detector_transaction_metrics']['recall'],1)
  self.assertEqual(result['annotation_metrics']['eligible_attempts'],1)
  self.assertEqual(result['annotation_metrics']['attempt_recovery'],1)
  self.assertEqual(result['amount_baseline_transaction_metrics']['unique_alerted_transactions'],5)
  report['snapshots']=[{'window_start':config.window_start,'window_end':'2022-09-01T00:30:00','snapshot_cutoff':'2022-09-01T00:30:00'},asdict(config)]
  early=evaluate(facts,labels,index,pairs,evidence,prep,report,annotations,scoring_window=('2022-09-01T00:00:00','2022-09-01T00:30:00'))
  self.assertEqual(early['detector_transaction_metrics']['unique_alerted_transactions'],0)
  self.assertEqual(early['annotation_metrics']['attempt_recovery'],0)
 def test_holdout_requires_pinned_early_calibration_and_same_rules(self):
  config={'min_counterparties':5,'max_cycle_degree':64}
  with self.assertRaises(ValueError):validate_calibration({},config)
  policy={'schema_version':1,'frozen':True,'rule_version':'structural-v2','min_counterparties':5,'max_cycle_degree':64,
   'development_analyses':[{'window_end':'2022-09-09T00:00:00'}],'amount_alert_fraction_by_currency':{'Bitcoin':'0.1'},'improvement_target':'Compare typed recovery and transaction precision against the frozen amount baseline; report the target as unmet if no improvement.'}
  validate_calibration(policy,config)
  policy['development_analyses'][0]['window_end']='2022-09-10T00:00:00'
  with self.assertRaises(ValueError):validate_calibration(policy,config)

if __name__=='__main__':unittest.main()
