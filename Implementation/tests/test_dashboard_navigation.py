"""Synthetic app interactions: active-page reads and consistent Q1 filters."""
import json,os,sys,unittest
from pathlib import Path
from unittest.mock import Mock,patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from streamlit.testing.v1 import AppTest


class DashboardNavigationTests(unittest.TestCase):
    def test_pages_only_load_their_own_inputs_and_currency_changes_query_population(self):
        window={'window_start':'2022-09-01T00:00:00','window_end':'2022-09-02T00:00:00','snapshot_cutoff':'2022-09-02T00:00:00','case_count':1,'history_complete':False}
        release={'release_id':'synthetic-ui','dataset_version':'fixture','run_id':'fixture','release_kind':'pilot','q1':{'dates':['2022-09-01']},'q2':{**window,'analysis_id':'fixture','snapshots':[window],'bundles':'s3://fixture/'},'catalog':{'database':'fixture','q1_table':'q1','q2_table':'q2'},'evaluation':{'metrics':{}},'timestamp_policy':'dataset-local','warnings':['Synthetic fixture']}
        nodes=[{'node_id':json.dumps([str(i),str(i)]),'bank':str(i),'account':str(i),'entity_id':'entity-'+str(i),'entity_name':'Fixture entity','entity_unknown':False} for i in range(3)]
        case={'pattern_type':'cycle_3','case_id':'a'*64,'rule_version':'fixture','participant_count':3,'evidence_transaction_count':3,'schema_version':3,'nodes':nodes,'edges':[{'source':nodes[i]['node_id'],'target':nodes[(i+1)%3]['node_id'],'transaction_count':1} for i in range(3)],'transactions':[{'source_id':'fixture:'+str(i),'amount_paid':'0.47209301','payment_currency':'US Dollar','amount_received':'0.47000000','receiving_currency':'Euro'} for i in range(3)],'interpretation':'Synthetic structural lead'}
        sqls=[]
        def query(client,sql):
            sqls.append(sql)
            if 'DISTINCT' in sql:return [{'currency':'US Dollar'}]
            if 'FROM fixture.q2' in sql:return [{'case_id':'a'*64,'pattern_type':'cycle_3','participant_count':'3','evidence_transaction_count':'3'}]
            return [{'payment_format':'ACH','n':'2000','l':'3','baseline_n':'2000','baseline_l':'3','rate':'.0015','lift':'1','support':'supported','selected_currency_amount':'0.47209301'}]
        tx={'population':2000,'positive_labels':3,'unique_alerted_transactions':1,'precision':None,'recall':None}
        metrics={'detector_transaction_metrics':tx,'annotation_metrics':{'eligible_attempts':0,'attempt_recovery':None},'limitations':['Fixture only']}
        session=Mock();session.client.return_value.get_caller_identity.return_value={'Account':'160885259244'}
        with patch.dict(os.environ,{'AML_AWS_PROFILE':'synthetic-test','AML_USE_INSTANCE_ROLE':''}),patch('boto3.Session',return_value=session),patch('pipeline.release.load_current',return_value=release),patch('pipeline.release.verify_ref',return_value=metrics) as metric_read,patch('dashboard.data.run_query',side_effect=query),patch('dashboard.data.get_case',return_value=(case,b'{}')) as case_read:
            app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'dashboard/app.py')).run(timeout=20)
            self.assertEqual(len(app.exception),0);self.assertEqual(len(app.error),0);self.assertFalse(case_read.called);self.assertFalse(metric_read.called);self.assertTrue(any("payment_currency='US Dollar'" in x for x in sqls))
            self.assertEqual(app.dataframe[0].value['US Dollar amount (paid)'].iloc[0],'0.47209301')
            app.selectbox(key='q1_side').set_value('receiving').run(timeout=20)
            self.assertEqual(len(app.error),0);self.assertTrue(any("receiving_currency='US Dollar'" in x for x in sqls));self.assertFalse(case_read.called)
            app.button_group(key='workspace_page').set_value('Case explorer').run(timeout=20)
            self.assertEqual(len(app.exception),0);self.assertEqual(len(app.error),0);self.assertTrue(case_read.called);self.assertFalse(metric_read.called)
            app.button_group(key='workspace_page').set_value('Evaluation').run(timeout=20)
            self.assertEqual(len(app.exception),0);self.assertEqual(len(app.error),0);self.assertTrue(metric_read.called)
            self.assertTrue(any('Not measurable' in x.value for x in app.markdown))
            app.button_group(key='workspace_page').set_value('Monitoring').run(timeout=20)
            self.assertEqual(app.selectbox(key='q1_side').value,'receiving')
            self.assertEqual(len(app.error),0)


if __name__=='__main__':unittest.main()
