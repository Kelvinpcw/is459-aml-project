"""Fresh evaluation namespaces and partition-bounded complete evidence lookup."""
import ast,copy,sys,unittest
from pathlib import Path
from unittest.mock import Mock,patch
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'jobs'),str(ROOT/'scripts')]
from pipeline.release import BUCKET
from control import paths,report_keys
from evaluate_distributed import evaluation_suffix
from export_case import lookup_case

CASE='a'*64

class CompletionResumeTests(unittest.TestCase):
    def config(self):return {'dataset_version':'fixture','run_id':'run','analysis_id':'detect','window_start':'2022-09-01T00:00:00','window_end':'2022-09-29T00:00:00','snapshot_cutoff':'2022-09-29T00:00:00'}
    def release(self):
        return {'dataset_version':'fixture','run_id':'run','catalog':{'database':'aml','q2_table':'cases_run'},'q2':{'analysis_id':'detect','snapshots':[
            {'window_start':'2022-09-01T00:00:00','window_end':'2022-09-08T00:00:00'},
            {'window_start':'2022-09-02T00:00:00','window_end':'2022-09-09T00:00:00'}]}}
    def test_new_attempt_changes_only_output_namespace(self):
        cfg=self.config();before=copy.deepcopy(cfg);base=evaluation_suffix(cfg,'eval');fresh=evaluation_suffix(cfg,'eval','resume1')
        self.assertEqual(fresh,base+'attempt=resume1/');self.assertEqual(cfg,before)
        for bad in ('../old','a/b','',):
            if bad:
                with self.assertRaises(ValueError):evaluation_suffix(cfg,'eval',bad)
        with self.assertRaises(ValueError):evaluation_suffix({**cfg,'analysis_id':'../foreign'},'eval','resume1')
    def test_publication_selects_only_exact_nested_report_in_same_evaluation(self):
        original=paths('run');key=original['evaluation'].rsplit('/',1)[0]+'/attempt=resume1/report.json'
        actual=report_keys('run',{'evaluation':'s3://'+BUCKET+'/'+key})
        self.assertEqual(actual['evaluation'],key);self.assertEqual(actual['q1'],original['q1'])
        for uri in ('s3://'+BUCKET+'/'+original['q2'],'s3://'+BUCKET+'/'+key.replace('resume1','../old'),'s3://other/'+key,'s3://'+BUCKET+'/'+key.replace('resume1','resume1/extra')):
            with self.assertRaises(ValueError):report_keys('run',{'evaluation':uri})
    def test_lookup_uses_locator_columns_and_one_snapshot_partition(self):
        row={'case_id':CASE,'bundle_uri':'fixture','bundle_member':CASE+'.json','bundle_sha256':'b'*64}
        with patch('export_case.run_query',side_effect=[[],[row]]) as query:
            self.assertEqual(lookup_case(Mock(),self.release(),CASE),row)
        self.assertEqual(query.call_count,2)
        for call in query.call_args_list:
            sql=call.args[1]
            self.assertNotIn('SELECT *',sql);self.assertIn('SELECT case_id,bundle_uri,bundle_member,bundle_sha256',sql)
            self.assertIn('window_date=DATE',sql);self.assertIn('window_end=TIMESTAMP',sql)
            self.assertIn("run_id='run'",sql);self.assertEqual(call.kwargs,{'max_rows':1})
        self.assertIn("window_date=DATE '2022-09-02'",query.call_args_list[0].args[1])
        self.assertIn("window_date=DATE '2022-09-01'",query.call_args_list[1].args[1])
    def test_cutoff_is_from_published_schedule_and_lookup_never_widens(self):
        with patch('export_case.run_query',return_value=[]) as query:
            with self.assertRaises(ValueError):lookup_case(Mock(),self.release(),CASE,'2022-09-30T00:00:00')
            query.assert_not_called()
            with self.assertRaises(ValueError):lookup_case(Mock(),self.release(),CASE,'2022-09-08T00:00:00')
            self.assertEqual(query.call_count,1)
            self.assertIn("window_date=DATE '2022-09-01'",query.call_args.args[1])
    def test_evaluation_and_calibration_logic_are_frozen(self):
        def functions(path):return {n.name:ast.dump(n) for n in ast.parse(path.read_text()).body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))}
        old=functions(ROOT/'releases/full-v2/evaluate_distributed.py');new=functions(ROOT/'jobs/evaluate_distributed.py')
        for name in ('metrics','validate_calibration','freeze_calibration'):self.assertEqual(old[name],new[name],name)

if __name__=='__main__':unittest.main()
