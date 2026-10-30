"""Synthetic UI regression for names across rankings, selectors and details."""
import os,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import Mock,patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from streamlit.testing.v1 import AppTest

class BankRouteUiTests(unittest.TestCase):
    def test_route_labels_across_monitoring_views(self):
        release={'timestamp_policy':'dataset-local','warnings':[],'release_id':'bank-ui','dataset_version':'fixture','run_id':'fixture',
                 'q2':{'window_start':'2022-09-01','window_end':'2022-09-02'},'q1':{'dates':['2022-09-01']},'catalog':{'database':'fixture','q1_table':'q1'}}
        def query(client,sql):
            if 'DISTINCT' in sql:return [{'currency':'US Dollar'}]
            if 'GROUP BY event_date' in sql:return [{'event_date':'2022-09-01','n':'2000','l':'3'}]
            return [{**({'payment_format':'ACH'} if 'GROUP BY payment_format)' in sql else {'sender_bank':'11','receiver_bank':'214',**({'payment_format':'ACH'} if 'GROUP BY sender_bank, receiver_bank, payment_format)' in sql else {})}),
                     'n':'2000','l':'3','baseline_n':'2000','baseline_l':'3','rate':'.0015',
                     'lift':'1.2','support':'supported','selected_currency_amount':'12.34000000'}]
        session=Mock();session.client.return_value.get_caller_identity.return_value={'Account':'160885259244'}
        expected='Bank of Miami (11) → First Bank of Dallas (214)'
        with tempfile.TemporaryDirectory() as directory:
            lookup=Path(directory)/'banks.csv'
            lookup.write_text('Bank ID,Bank Name\n011,Bank of Miami\n00214,First Bank of Dallas\n')
            with patch.dict(os.environ,{'AML_AWS_PROFILE':'synthetic','AML_USE_INSTANCE_ROLE':'',
                                       'AML_BANK_NAMES_CSV':str(lookup)}),\
                 patch('boto3.Session',return_value=session),\
                 patch('pipeline.release.load_current',return_value=release),\
                 patch('dashboard.data.run_query',side_effect=query):
                app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'dashboard/app.py')).run(timeout=20)
                app.selectbox(key='q1_grain').set_value('bank_pair').run(timeout=20)
                self.assertFalse(app.exception);self.assertFalse(app.error)
                self.assertEqual(app.selectbox(key='q1_inspect_bank_pair').options,[expected])
                tables=[x.value for x in app.dataframe if 'Segment' in x.value.columns]
                self.assertTrue(tables)
                for table in tables:self.assertEqual(table['Segment'].iloc[0],expected)
                self.assertTrue(any('Sending bank → Receiving bank' in x.value for x in app.caption))
                self.assertTrue(any(expected in x.value for x in app.markdown))

if __name__=='__main__':unittest.main()
