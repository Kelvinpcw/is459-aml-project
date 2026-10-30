import io,json,os,sys,unittest
from pathlib import Path
from unittest.mock import Mock,patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
sys.path.insert(0,str(Path(__file__).resolve().parent))
from test_release_dashboard import fixture
from test_q2_detect import transaction,CONFIG
from jobs.q2_detect import build_cases,encode_case
from pipeline.release import validate_candidate,encoded,sha

class ApplicationTests(unittest.TestCase):
 def test_connected_views_render_and_case_download_keeps_complete_source_evidence(self):
  from streamlit.testing.v1 import AppTest
  candidate,reports=fixture();release=validate_candidate(candidate,reports)
  rows=[transaction(str(i),'H',f'P{i}') for i in range(5)]
  case=build_cases(rows,CONFIG)[0][0]
  case.update(dataset_version='fixture',run_id='run',analysis_id='detect')
  body=encode_case(case)
  case_row={'case_id':case['case_id'],'bundle_uri':release['q2']['bundles']+case['case_id']+'.json','pattern_type':'fan_out','participant_count':'6','evidence_transaction_count':'5'}
  metrics=encoded({'detector_transaction_metrics':{'population':10,'positive_labels':0,'precision':None,'recall':None,'unique_alerted_transactions':5},'annotation_metrics':{'eligible_attempts':0}})
  release['evaluation']['metrics']['sha256']=sha(metrics)
  s3=Mock()
  s3.get_object.side_effect=lambda **kw:{'Body':io.BytesIO(metrics if kw['Key']=='evaluation/metrics.json' else body)}
  session=Mock();session.client.side_effect=lambda service:Mock(get_caller_identity=lambda:{'Account':'160885259244'}) if service=='sts' else s3 if service=='s3' else Mock()
  def query(client,sql):
   if ' AS currency' in sql:return [{'currency':'US Dollar'}]
   if 'GROUP BY event_date' in sql:return [{'event_date':release['q1']['dates'][0],'n':'10','l':'2'}]
   if 'SELECT * FROM aml.cases_run' in sql:return [case_row]
   return [{'payment_format':'ACH','n':'10','l':'2','baseline_n':'10','baseline_l':'2','rate':'0.2','lift':'1.0','support':'low_support','selected_currency_amount':'0.47209301'}]
  with patch.dict(os.environ,{'AML_AWS_PROFILE':'synthetic-profile'}),patch('boto3.Session',return_value=session),patch('dashboard.data.run_query',side_effect=query):
   app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'dashboard/app.py'),default_timeout=30)
   app.session_state['release']=release;app.run()
   self.assertFalse(app.exception,list(app.exception))
   self.assertFalse(app.error,list(app.error))
   self.assertEqual(app.radio(key='workspace_page').options,['Monitoring overview','Connected cases','Evaluation & coverage','Release & provenance'])
   self.assertTrue(any('No supported groups' in element.value for element in app.info))
   app.radio(key='workspace_page').set_value('Case explorer').run()
   self.assertFalse(app.exception,list(app.exception));self.assertFalse(app.error,list(app.error))
   self.assertEqual([tab.label for tab in app.tabs],['Accounts & entities','Evidence preview'])
   evidence=next(df.value for df in app.dataframe if 'Source ID' in df.value.columns)
   self.assertEqual(list(evidence['Source ID']),[tx['source_id'] for tx in case['transactions']])
   self.assertTrue(any('Download complete case JSON'==element.label for element in app.get('download_button')))
   app.radio(key='workspace_page').set_value('Evaluation').run()
   self.assertFalse(app.exception,list(app.exception));self.assertFalse(app.error,list(app.error))

if __name__=='__main__':unittest.main()
