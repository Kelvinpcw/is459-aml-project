"""Equivalent fan verification must use equi-joins, including window boundaries."""
import ast,datetime,os,random,sys,time,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'jobs')]
from evaluate_distributed import complete_fan_pairs,independent_frame
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
 def test_wide_checkpoint_baseline_has_disjoint_expression_ids_and_exact_ranks(self):
  import tempfile
  from decimal import Decimal
  from pyspark.sql import Window
  rows=[('a','USD',Decimal('0.47209301')),('b','USD',Decimal('10000000.47209301')),('c','USD',Decimal('10000000.47209302')),('d','SGD',Decimal('9.00000001'))]
  frame=self.spark.createDataFrame(rows,T.StructType([T.StructField('source_id',T.StringType()),T.StructField('payment_currency',T.StringType()),T.StructField('amount_paid',T.DecimalType(38,8))]))
  for n in range(30):frame=frame.withColumn('extra_'+str(n),F.lit('preserved'))
  with tempfile.TemporaryDirectory() as directory:
   frame.write.parquet(directory+'/facts');eligible=self.spark.read.parquet(directory+'/facts').localCheckpoint(eager=True)
   alerts=eligible.filter("source_id IN ('a','b','d')").select('source_id').localCheckpoint(eager=True)
   budgets=eligible.join(independent_frame(alerts),'source_id').groupBy('payment_currency').count().withColumnRenamed('count','budget')
   population=eligible.groupBy('payment_currency').count().withColumnRenamed('count','population')
   audit=population.join(independent_frame(budgets),'payment_currency','left').na.fill(0)
   ranked=eligible.withColumn('rank',F.row_number().over(Window.partitionBy('payment_currency').orderBy(F.col('amount_paid').desc(),'source_id'))).localCheckpoint(eager=True)
   right=independent_frame(audit.select('payment_currency','budget'))
   self.assertEqual(right.schema,audit.select('payment_currency','budget').schema)
   def ids(df):
    seq=df._jdf.queryExecution().analyzed().output();return {seq.apply(i).exprId().id() for i in range(seq.size())}
   self.assertFalse(ids(ranked)&ids(right))
   baseline=ranked.join(right,'payment_currency').filter(F.col('rank')<=F.col('budget'))
   self.assertEqual({r['source_id'] for r in baseline.select('source_id').collect()},{'b','c','d'})
   self.assertEqual({r['source_id']:r['amount_paid'] for r in baseline.select('source_id','amount_paid').collect()}['c'],Decimal('10000000.47209302'))
 def test_every_evaluator_join_refreshes_its_right_relation(self):
  source=(ROOT/'jobs/evaluate_distributed.py').read_text();fn=next(n for n in ast.parse(source).body if getattr(n,'name',None)=='evaluate');count=0
  for node in ast.walk(fn):
   if isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute) and node.func.attr=='join':
    count+=1;self.assertIsInstance(node.args[0],ast.Call);self.assertEqual(node.args[0].func.id,'independent_frame')
  self.assertGreater(count,15)

 def test_legacy_plan_exposes_the_problem_without_running_large_data(self):
  fan=self.spark.createDataFrame([('H','fan_in')],['hub','pattern_type']).alias('f')
  edges=self.spark.createDataFrame([('A','H')],['src','dst']).alias('e')
  predicate=((F.col('f.pattern_type')=='fan_in')&(F.col('f.hub')==F.col('e.dst')))|((F.col('f.pattern_type')=='fan_out')&(F.col('f.hub')==F.col('e.src')))
  self.assertIn('CartesianProduct',fan.join(edges,predicate)._jdf.queryExecution().sparkPlan().toString())
 def test_only_fan_reconstruction_call_changes_in_scoring_function(self):
  before=(ROOT/'releases/full-v3/evaluate_distributed.py').read_text();after=(ROOT/'jobs/evaluate_distributed.py').read_text()
  a=before.index("    f,e=fan.alias('f'),ed.alias('e')");b=before.index('    actual_fan=',a)
  normalized=before[:a]+'    complete_fan=complete_fan_pairs(fan,ed)\n'+before[b:]
  def function(source,name):
   node=next(n for n in ast.parse(source).body if getattr(n,'name',None)==name)
   class StripAliases(ast.NodeTransformer):
    def visit_Call(self,n):
     self.generic_visit(n)
     return n.args[0] if isinstance(n.func,ast.Name) and n.func.id=='independent_frame' else n
   return ast.dump(StripAliases().visit(node))
  for name in ('evaluate','metrics','validate_calibration','freeze_calibration'):self.assertEqual(function(normalized,name),function(after,name))

if __name__=='__main__':unittest.main()
