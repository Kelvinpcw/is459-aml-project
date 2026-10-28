"""Equivalent fan verification must use equi-joins, including window boundaries."""
import ast,datetime,os,random,sys,time,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'jobs')]
from evaluate_distributed import complete_fan_pairs
from pyspark.sql import SparkSession,functions as F,types as T

class FanPlanTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.old_tz=os.environ.get('TZ');os.environ['TZ']='UTC';time.tzset()
  cls.spark=SparkSession.builder.master('local[2]').appName('is459-keyed-fan-check').config('spark.sql.shuffle.partitions','2').getOrCreate();cls.spark.sparkContext.setLogLevel('ERROR')
 @classmethod
 def tearDownClass(cls):
  cls.spark.stop()
  if cls.old_tz is None:os.environ.pop('TZ',None)
  else:os.environ['TZ']=cls.old_tz
  time.tzset()
 def test_keyed_join_equals_independent_oracle_and_has_no_cartesian_plan(self):
  start=datetime.datetime(2022,9,1);end=start+datetime.timedelta(days=1);cut=start+datetime.timedelta(hours=12)
  cases=[('in','H','fan_in',start,end,end),('out','H','fan_out',start,end,cut),('late','H','fan_out',end,end+datetime.timedelta(days=1),end+datetime.timedelta(days=1))]
  rng=random.Random(459);nodes=['H','A','B','C','D']
  edges=[(rng.choice(nodes),rng.choice(nodes),start+datetime.timedelta(hours=rng.choice([-1,0,1,12,13,23,24,25,48]))) for _ in range(200)]
  edges += [('A','H',start),('H','B',cut),('H','B',cut),('H','C',end),('H','H',start)]
  expected={(cid,src,dst) for cid,hub,pattern,lo,hi,at in cases for src,dst,event in edges if src!=dst and lo<=event<hi and event<=at and ((pattern=='fan_in' and hub==dst) or (pattern=='fan_out' and hub==src))}
  fans=self.spark.createDataFrame(cases,['case_id','hub','pattern_type','window_start','window_end','snapshot_cutoff'])
  facts=self.spark.createDataFrame(edges,['src','dst','event_time']).filter('src<>dst')
  actual=complete_fan_pairs(fans,facts)
  self.assertEqual({tuple(r) for r in actual.collect()},expected)
  plan=actual._jdf.queryExecution().executedPlan().toString()
  self.assertNotIn('CartesianProduct',plan);self.assertNotIn('BroadcastNestedLoopJoin',plan)
  self.assertTrue('SortMergeJoin' in plan or 'BroadcastHashJoin' in plan or 'ShuffledHashJoin' in plan)
 def test_legacy_plan_exposes_the_problem_without_running_large_data(self):
  fan=self.spark.createDataFrame([('H','fan_in')],['hub','pattern_type']).alias('f')
  edges=self.spark.createDataFrame([('A','H')],['src','dst']).alias('e')
  predicate=((F.col('f.pattern_type')=='fan_in')&(F.col('f.hub')==F.col('e.dst')))|((F.col('f.pattern_type')=='fan_out')&(F.col('f.hub')==F.col('e.src')))
  self.assertIn('CartesianProduct',fan.join(edges,predicate)._jdf.queryExecution().sparkPlan().toString())
 def test_only_fan_reconstruction_call_changes_in_scoring_function(self):
  before=(ROOT/'releases/full-v3/evaluate_distributed.py').read_text();after=(ROOT/'jobs/evaluate_distributed.py').read_text()
  a=before.index("    f,e=fan.alias('f'),ed.alias('e')");b=before.index('    actual_fan=',a)
  normalized=before[:a]+'    complete_fan=complete_fan_pairs(fan,ed)\n'+before[b:]
  def function(source,name):return ast.dump(next(n for n in ast.parse(source).body if getattr(n,'name',None)==name))
  for name in ('evaluate','metrics','validate_calibration','freeze_calibration'):self.assertEqual(function(normalized,name),function(after,name))

if __name__=='__main__':unittest.main()
