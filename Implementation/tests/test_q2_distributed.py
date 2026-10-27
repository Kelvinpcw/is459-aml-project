from dataclasses import replace
from pathlib import Path
import sys,unittest,os,time
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'jobs'))
sys.path.insert(0,str(Path(__file__).resolve().parent))
from q2_distributed import DistributedConfig,detect,export_partition,export_rows
from q2_snapshots import output_cost_estimate
from unittest.mock import patch,Mock
from botocore.exceptions import ClientError
import io,json,hashlib,itertools
from test_q2_detect import transaction,manifest,CONFIG
from q2_detect import build_cases
from pyspark.sql import SparkSession
from pyspark.sql.types import StructType,StructField,StringType,TimestampType,BooleanType,DecimalType

class DistributedTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.original_tz=os.environ.get('TZ');os.environ['TZ']='UTC';time.tzset()
  cls.spark=SparkSession.builder.master('local[2]').appName('distributed-q2-tests').config('spark.sql.shuffle.partitions','2').config('spark.sql.session.timeZone','UTC').getOrCreate()
  cls.spark.sparkContext.setLogLevel('ERROR')
 @classmethod
 def tearDownClass(cls):
  cls.spark.stop()
  if cls.original_tz is None:os.environ.pop('TZ',None)
  else:os.environ['TZ']=cls.original_tz
  time.tzset()
 def frame(self,rows):
  schema=StructType([StructField(k,TimestampType() if k=='event_time' else DecimalType(38,8) if k in ('amount_paid','amount_received') else BooleanType() if k.endswith('_unknown') else StringType(),True) for k in rows[0]])
  return self.spark.createDataFrame(rows,schema)
 def test_distributed_relations_match_independent_driver_oracle_across_minute_boundary(self):
  rows=[transaction(str(i),'H',f'P{i}',minute=i) for i in range(5)]
  rows += [transaction('duplicate','H','P0',minute=4),transaction('self','H','H')]
  rows += [transaction('cycle-a','A','B',minute=0),transaction('cycle-b','B','C',minute=1),transaction('cycle-c','C','A',minute=2)]
  rows += [transaction('dense'+str(i),a,b) for i,(a,b) in enumerate(itertools.permutations(['D0','D1','D2','D3'],2))]
  cfg=DistributedConfig(**{k:getattr(CONFIG,k) for k in ('dataset_version','run_id','analysis_id','window_start','window_end','snapshot_cutoff')})
  expected,_=build_cases(rows,CONFIG)
  index,pairs,evidence,stats=detect(self.frame(rows),manifest(rows),cfg)
  got=sorted((r['pattern_type'],r['participant_count'],r['unique_edge_count'],r['evidence_transaction_count']) for r in index.collect())
  want=sorted((r['pattern_type'],r['participant_count'],r['unique_edge_count'],r['evidence_transaction_count']) for r in expected)
  self.assertEqual(got,want)
  self.assertEqual(stats['self_transaction_rows'],1)
  self.assertEqual({r['source_id'] for r in evidence.select('source_id').collect()},set(t['source_id'] for c in expected for t in c['transactions']))
  estimate=output_cost_estimate(index,evidence)
  metadata=[c for c in index.columns if c not in evidence.columns or c=='case_id']
  import tempfile
  with tempfile.TemporaryDirectory() as directory:index.write.mode('errorifexists').parquet(directory+'/index')
  output=export_rows(index,evidence).orderBy('case_id','event_time','source_id').collect()
  objects={}
  def put(**kw):
   if kw['Key'] in objects:raise ClientError({'Error':{'Code':'PreconditionFailed'}},'PutObject')
   objects[kw['Key']]=kw['Body']
  s3=Mock();s3.put_object.side_effect=put;s3.get_object.side_effect=lambda **kw:{'Body':io.BytesIO(objects[kw['Key']])}
  session=Mock();session.client.return_value=s3
  with patch('boto3.Session',return_value=session):
   first=list(export_partition(iter(output),'fixture','gold/cases/'))
   again=list(export_partition(iter(output),'fixture','gold/cases/'))
  self.assertEqual(first,again)
  headers=[json.loads(body) for key,body in objects.items() if '/bundles/' in key]
  self.assertEqual(len(headers),len(expected))
  for case in headers:
   self.assertEqual(sum(p['rows'] for p in case['evidence_parts']),case['evidence_transaction_count'])
   for part in case['evidence_parts']:
    raw=objects[part['uri'].split('s3://fixture/',1)[1]]
    self.assertEqual(hashlib.sha256(raw).hexdigest(),part['sha256'])
    self.assertIn(b'0.47209301',raw)
  self.assertGreaterEqual(estimate['estimated_30day_storage_bytes_upper_bound'],sum(map(len,objects.values())))

  # Schema-v3 packs all cases into bounded ZIPs without altering source evidence.
  from q2_bundle_shards import export_shards
  from dashboard.data import get_case,read_evidence_part,full_evidence_archive
  objects.clear();root='gold/cases/bundles-test/'
  with patch('boto3.Session',return_value=session):
   refs=list(export_shards(iter(output),'is459-aml-g2team7-160885259244-us-east-1',root,'2022-09-02',0,shard_bytes=16000))
   original=dict(objects)
   self.assertEqual(refs,list(export_shards(iter(output),'is459-aml-g2team7-160885259244-us-east-1',root,'2022-09-02',0,shard_bytes=16000)))
   self.assertEqual(original,objects)
  release={'dataset_version':cfg.dataset_version,'run_id':cfg.run_id,'q2':{'analysis_id':cfg.analysis_id,'bundles':'s3://is459-aml-g2team7-160885259244-us-east-1/'+root+'bundles/'}}
  seen={};self.assertEqual(len(refs),len(expected));self.assertGreater(len(objects),1)
  for case_id,uri,member,digest in refs:
   row=dict(case_id=case_id,bundle_uri=uri,bundle_member=member,bundle_sha256=digest)
   loaded,raw=get_case(s3,release,row);cache={};records=[]
   for ref in loaded['evidence_parts']:records.extend(json.loads(line) for line in read_evidence_part(s3,ref,cache).splitlines())
   self.assertEqual(len(records),loaded['evidence_transaction_count']);seen[case_id]={r['source_id'] for r in records}
   self.assertTrue(full_evidence_archive(s3,loaded))
   with self.assertRaises(ValueError):get_case(s3,release,{**row,'bundle_sha256':'0'*64})
   with self.assertRaises(ValueError):get_case(s3,release,{**row,'bundle_member':'../'+member})
  self.assertEqual(set().union(*seen.values()),set(t['source_id'] for c in expected for t in c['transactions']))

 def test_explicit_cycle_degree_exclusions_preserve_complete_fan_evidence(self):
  rows=[transaction(str(i),'H',f'P{i}') for i in range(5)]+[transaction('back','P0','H')]
  cfg=DistributedConfig(**{k:getattr(CONFIG,k) for k in ('dataset_version','run_id','analysis_id','window_start','window_end','snapshot_cutoff')},max_cycle_degree=2)
  index,pairs,evidence,stats=detect(self.frame(rows),manifest(rows),cfg)
  self.assertEqual([r['pattern_type'] for r in index.collect()],['fan_out'])
  self.assertEqual(evidence.count(),5);self.assertEqual(stats['cycle_excluded_nodes_above_degree'],1)
  self.assertIn('not all original graph cycles',stats['cycle_coverage'])

if __name__=='__main__':unittest.main()
