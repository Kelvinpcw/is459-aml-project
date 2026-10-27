import copy,io,json,sys,unittest
from pathlib import Path
from unittest.mock import Mock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from pipeline.release import validate_candidate,publish,encoded,BUCKET,load_current,sha,check_outputs
from dashboard.data import q1_query,case_query,get_case,evidence_csv,run_query,wilson


def fixture():
    base='s3://'+BUCKET+'/'
    suffix='dataset_version=fixture/run_id=run/'
    reports={
      'preparation':{'stage':'preparation','status':'PASSED','dataset_version':'fixture','run_id':'run',
        'label_separation_passed':True,'quarantined_rows':0,'source_reference_reconciliation_passed':True,
        'accepted_rows':10,'input_rows':10,'accepted_by_format':[{'labelled_laundering':2}],
        'source_manifest':{'selected_dates':{'2022-09-01':10},'counts':{'selected_records':10,'source_records':100,'outside_development_scope':90}},'timestamp_policy':'dataset-local'},
      'q1':{'stage':'q1','status':'PASSED','dataset_version':'fixture','run_id':'run','analysis_id':'risk',
        'totals':{'transactions':10,'labelled_laundering':2},'outputs':{'daily_counts':base+'gold/risk/'+suffix+'analysis_id=risk/daily_counts/'}},
      'q2':{'stage':'q2','status':'PASSED','config':{'dataset_version':'fixture','run_id':'run','analysis_id':'detect',
        'window_start':'2022-09-01T00:00:00','window_end':'2022-09-01T00:01:00','snapshot_cutoff':'2022-09-01T00:01:00'},
        'detector_received_labels':False,'statistics':{'case_count':1,'scoped_rows':5,'complete_for_declared_window':True,'truncated':False},
        'outputs':{'case_index':base+'gold/cases/'+suffix+'analysis_id=detect/case_index/','bundles':base+'gold/cases/'+suffix+'analysis_id=detect/bundles/'}},
      'evaluation':{'stage':'evaluation','status':'PASSED','dataset_version':'fixture','run_id':'run','full_prepared_rows_reconciled':10,
        'detector_analysis_id':'detect','case_count':1,'eligible_transactions':5,'evaluation_id':'eval','artifacts':{'metrics.json':{'uri':base+'evaluation/metrics.json','sha256':'0'*64,'bytes':0}}}}
    candidate={'schema_version':1,'release_id':'r1','release_kind':'pilot','reports':{s:{'uri':base+s+'.json','sha256':'0'*64} for s in reports},
      'catalog':{'database':'aml','q1_table':'risk_run','q2_table':'cases_run'}}
    return candidate,reports


class MemoryS3:
    def __init__(self):self.objects={};self.etags={};self.fail_pointer=False
    def put_object(self,Bucket,Key,Body,IfNoneMatch=None,IfMatch=None,**kwargs):
        if Key=='published/current.json' and self.fail_pointer:raise RuntimeError('injected publication failure')
        if IfNoneMatch=='*' and Key in self.objects:raise ValueError('PreconditionFailed')
        if IfMatch and self.etags.get(Key)!=IfMatch:raise ValueError('PreconditionFailed')
        self.objects[Key]=Body;self.etags[Key]=sha(Body)
    def get_object(self,Bucket,Key):return {'Body':io.BytesIO(self.objects[Key])}


class ReleaseTests(unittest.TestCase):
    def test_failed_mixed_truncated_wrong_population_and_full_claims_are_rejected(self):
        for stage,key,value in [('q1','status','FAILED'),('evaluation','run_id','other'),('evaluation','eligible_transactions',4)]:
            candidate,reports=fixture();reports[stage][key]=value
            with self.assertRaises(ValueError):validate_candidate(candidate,reports)
        for key,value in [('truncated',True),('complete_for_declared_window',False)]:
            c,r=fixture();r['q2']['statistics'][key]=value
            with self.assertRaises(ValueError):validate_candidate(c,r)
        c,r=fixture();c['release_kind']='full'
        with self.assertRaisesRegex(ValueError,'complete source'):validate_candidate(c,r)
    def test_pointer_cas_and_failed_publication_preserve_previous_release(self):
        c,r=fixture();first=validate_candidate(c,r);s3=MemoryS3();publish(s3,first)
        prior=s3.objects['published/current.json'];etag=s3.etags['published/current.json']
        second={**first,'release_id':'r2'};s3.fail_pointer=True
        with self.assertRaises(RuntimeError):publish(s3,second,etag)
        self.assertEqual(s3.objects['published/current.json'],prior)
        s3.fail_pointer=False
        with self.assertRaises(ValueError):publish(s3,{**first,'release_id':'r3'},'stale-etag')
        self.assertEqual(load_current(s3)['release_id'],'r1')
        publish(s3,{**first,'release_id':'r4'},etag)
        self.assertEqual(load_current(s3)['release_id'],'r4')
        # A previously loaded snapshot still pins every read to r1.
        self.assertEqual(first['release_id'],'r1')
    def test_manifest_tampering_and_out_of_namespace_outputs_fail(self):
        c,r=fixture();release=validate_candidate(c,r);s3=MemoryS3();publish(s3,release)
        s3.objects['published/releases/r1/manifest.json']=b'{}'
        with self.assertRaises(ValueError):load_current(s3)
        r['q2']['outputs']['bundles']='s3://'+BUCKET+'/gold/cases/other/'
        with self.assertRaises(ValueError):validate_candidate(c,r)
    def test_missing_success_marker_or_wrong_catalog_blocks_publication(self):
        c,r=fixture();release=validate_candidate(c,r);s3=Mock();glue=Mock()
        glue.get_table.return_value={'Table':{'StorageDescriptor':{'Location':'s3://'+BUCKET+'/wrong/'}}}
        with self.assertRaises(ValueError):check_outputs(s3,glue,release,r)
        glue.get_table.return_value={'Table':{'StorageDescriptor':{'Location':r['q1']['outputs']['daily_counts']}}}
        s3.get_paginator.return_value.paginate.side_effect=FileNotFoundError('partial output')
        with self.assertRaises(FileNotFoundError):check_outputs(s3,glue,release,r)


class DashboardTests(unittest.TestCase):
    def test_sql_pins_identity_population_currency_and_preserves_money_units(self):
        c,r=fixture();release=validate_candidate(c,r)
        sql=q1_query(release,'2022-09-01','2022-09-01',"O'Reilly",side='receiving',grain='segment',payment_format='ACH')
        self.assertIn("receiving_currency='O''Reilly'",sql)
        self.assertIn("dataset_version='fixture'",sql);self.assertIn("run_id='run'",sql)
        self.assertIn('SUM(amount_received_total)',sql);self.assertNotIn('SUM(amount_paid_total)',sql)
        self.assertIn('FROM selected',sql);self.assertNotIn('AVG(',sql)
        with self.assertRaises(ValueError):q1_query(release,'2022-09-02','2022-09-02','USD')
        with self.assertRaises(ValueError):q1_query(release,'2022-09-01','2022-09-01','USD',side='anything')
        self.assertIn("analysis_id='detect'",case_query(release))
    def test_case_identity_complete_evidence_and_safe_csv(self):
        c,r=fixture();release=validate_candidate(c,r);s3=Mock()
        case={'dataset_version':'fixture','run_id':'run','analysis_id':'detect','case_id':'abc','evidence_transaction_count':1,'transactions':[{'source_id':'=1+1','amount_paid':'0.47209301'}]}
        s3.get_object.return_value={'Body':io.BytesIO(encoded(case))}
        row={'case_id':'abc','bundle_uri':release['q2']['bundles']+'abc.json'}
        loaded,raw=get_case(s3,release,row)
        self.assertIn("'=1+1",evidence_csv(loaded));self.assertIn('0.47209301',evidence_csv(loaded))
        with self.assertRaises(ValueError):get_case(s3,release,{**row,'bundle_uri':'s3://'+BUCKET+'/other'})
    def test_timeout_cancels_paid_query(self):
        client=Mock();client.start_query_execution.return_value={'QueryExecutionId':'q'}
        client.get_query_execution.return_value={'QueryExecution':{'Status':{'State':'RUNNING'}}}
        with self.assertRaises(TimeoutError):run_query(client,'SELECT 1',timeout=0,sleep=lambda _:None)
        client.stop_query_execution.assert_called_once_with(QueryExecutionId='q')
    def test_descriptive_interval_handles_small_and_zero_populations(self):
        self.assertEqual(wilson(0,0),(None,None))
        lo,hi=wilson(0,10);self.assertAlmostEqual(lo,0);self.assertGreater(hi,.2)

if __name__=='__main__':unittest.main()
