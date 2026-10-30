import os,re,sqlite3,sys,unittest
from datetime import date,timedelta
from pathlib import Path
from unittest.mock import Mock,patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from dashboard.data import q1_trend_query
from dashboard.trends import daily_population,population_total,range_options,date_window,coverage_counts,endpoint_comparison,trend_chart
from streamlit.testing.v1 import AppTest


class TrendTests(unittest.TestCase):
    def test_daily_sql_keeps_population_both_currency_sides_format_and_count_weighting(self):
        release={'dataset_version':'fixture','run_id':'run','q1':{'dates':['2022-09-01','2022-09-02']},'catalog':{'database':'fixture','q1_table':'q1'}}
        db=sqlite3.connect(':memory:');db.row_factory=sqlite3.Row;db.execute("ATTACH DATABASE ':memory:' AS fixture")
        db.execute('CREATE TABLE fixture.q1 (dataset_version TEXT,run_id TEXT,event_date TEXT,payment_currency TEXT,receiving_currency TEXT,payment_format TEXT,transaction_count INTEGER,laundering_count INTEGER)')
        rows=[('fixture','run','2022-09-01','USD','EUR','ACH',100,2),('fixture','run','2022-09-01','USD','USD','ACH',300,3),('fixture','run','2022-09-02','USD','EUR','ACH',10,5),('fixture','run','2022-09-02','EUR','EUR','ACH',500,1),('fixture','run','2022-09-02','USD','EUR','Wire',40,0),('other','run','2022-09-01','USD','EUR','ACH',9999,9999)]
        db.executemany('INSERT INTO fixture.q1 VALUES (?,?,?,?,?,?,?,?)',rows)
        def query(currency,side):
            sql=q1_trend_query(release,'2022-09-01','2022-09-02',currency,side,'ACH')
            self.assertNotIn('LIMIT 500',sql);self.assertNotIn('AVG(',sql.upper());self.assertIn("run_id='run'",sql)
            # SQLite uses ISO date strings; Athena's DATE literal is the only
            # dialect difference for this aggregate fixture.
            return [dict(r) for r in db.execute(re.sub(r"DATE '([^']+)'",r"'\1'",sql))]
        overall=query(None,'payment');self.assertEqual([(r['n'],r['l']) for r in overall],[(400,5),(510,6)])
        paid=query('USD','payment');self.assertEqual([(r['n'],r['l']) for r in paid],[(400,5),(10,5)])
        received=query('EUR','receiving');self.assertEqual([(r['n'],r['l']) for r in received],[(100,2),(510,6)])
        daily=daily_population(paid,'2022-09-01','2022-09-02',release['q1']['dates']);self.assertEqual(population_total(daily),(410,10,10/410));self.assertNotAlmostEqual(population_total(daily)[2],sum(r['rate'] for r in daily)/2)
        with self.assertRaises(ValueError):q1_trend_query(release,'2022-09-01','2022-09-03','USD')
        with self.assertRaises(ValueError):q1_trend_query(release,'2022-09-01','2022-09-02','USD',side='invalid')

    def test_missing_coverage_is_not_zero_and_empty_filtered_days_have_no_rate(self):
        daily=daily_population([{'event_date':'2022-09-01','n':'0','l':'0'}],'2022-09-01','2022-09-03',['2022-09-01','2022-09-02'])
        self.assertEqual([r['n'] for r in daily],[0,0,None]);self.assertTrue(all(r['rate'] is None for r in daily));self.assertEqual(population_total(daily),(None,None,None))
        self.assertIn('unavailable',endpoint_comparison(daily))
        with self.assertRaises(ValueError):daily_population([{'event_date':'2022-09-01','n':'1','l':'2'}],'2022-09-01','2022-09-01',['2022-09-01'])
        with self.assertRaises(ValueError):daily_population([{'event_date':'2022-09-01','n':'1','l':'0'}]*2,'2022-09-01','2022-09-01',['2022-09-01'])

    def test_rolling_windows_anchor_to_latest_published_date_and_clip_short_history(self):
        days=[(date(2031,7,1)+timedelta(days=i)).isoformat() for i in range(45)]
        self.assertEqual(date_window(days,'Last 7 days'),('2031-08-08','2031-08-14'))
        self.assertEqual(date_window(days,'Last 30 days'),('2031-07-16','2031-08-14'))
        self.assertEqual(date_window(days+['2031-08-15'],'Last 7 days'),('2031-08-09','2031-08-15'))
        self.assertEqual(date_window(['2005-01-01','2005-01-02'],'Last 30 days'),('2005-01-01','2005-01-02'))
        self.assertNotIn('All available',range_options(['2000-01-01','2031-01-01']))
        with self.assertRaises(ValueError):date_window(['2000-01-01','2031-01-01'],'All available')
        with self.assertRaises(ValueError):date_window(days,'Custom dates','2031-08-14','2031-07-01')

    def test_volume_flags_do_not_infer_incompleteness_or_depend_on_labels(self):
        rows=[{'event_date':'2031-01-01','n':10000,'l':9999},{'event_date':'2031-01-02','n':10,'l':0}]
        daily=daily_population(rows,'2031-01-01','2031-01-02',['2031-01-01','2031-01-02'])
        self.assertFalse(daily[0]['low_volume']);self.assertTrue(daily[1]['low_volume']);self.assertEqual([r['coverage'] for r in daily],['unknown','unknown']);self.assertEqual(coverage_counts(daily)['partial'],0)
        explicit=daily_population(rows,'2031-01-01','2031-01-02',['2031-01-01','2031-01-02'],{'2031-01-01':'complete','2031-01-02':'partial'})
        self.assertEqual(coverage_counts(explicit)['partial'],1);self.assertEqual(population_total(daily),population_total(explicit))
        self.assertIn('provisional',endpoint_comparison(explicit))

    def test_chart_has_no_calendar_split_and_retains_real_gaps(self):
        daily=daily_population([{'event_date':'2031-01-01','n':1000,'l':10},{'event_date':'2031-01-03','n':10,'l':8}],'2031-01-01','2031-01-03',['2031-01-01','2031-01-03'])
        fig=trend_chart(daily);line=next(t for t in fig.data if t.type=='scatter' and t.yaxis=='y2')
        self.assertEqual(list(line.y),[.01,None,.8]);self.assertFalse(line.connectgaps);self.assertFalse(fig.layout.shapes)
        comparison=endpoint_comparison(daily);self.assertIn('10 → 8 (-2)',comparison);self.assertNotIn('different traffic populations',comparison)

    def test_arbitrary_full_range_app_uses_one_filtered_window_for_rates_and_rankings(self):
        days=[(date(2031,7,1)+timedelta(days=i)).isoformat() for i in range(28)]
        release={'release_id':'synthetic-trend-range','dataset_version':'fixture','run_id':'run','release_kind':'full','q1':{'dates':days},'q2':{'window_start':days[0],'window_end':days[-1]},'catalog':{'database':'fixture','q1_table':'q1'},'timestamp_policy':'dataset-local','warnings':[]}
        observed=[]
        def query(client,sql):
            observed.append(sql)
            if 'DISTINCT' in sql:return [{'currency':'US Dollar'}]
            start,end=re.search(r"BETWEEN DATE '([^']+)' AND DATE '([^']+)'",sql).groups();scope=[d for d in days if start<=d<=end]
            rows=[{'event_date':d,'n':1000 if d<'2031-07-17' else 10,'l':2 if d<'2031-07-17' else 8} for d in scope]
            if 'GROUP BY event_date' in sql:return rows
            n=sum(r['n'] for r in rows);l=sum(r['l'] for r in rows)
            return [{'payment_format':'ACH','n':str(n),'l':str(l),'baseline_n':str(n),'baseline_l':str(l),'rate':l/n,'lift':'1','support':'supported' if n>=1000 else 'low_support','selected_currency_amount':'0.47209301'}]
        session=Mock();session.client.return_value.get_caller_identity.return_value={'Account':'160885259244'}
        with patch.dict(os.environ,{'AML_AWS_PROFILE':'synthetic-trend-test'}),patch('boto3.Session',return_value=session),patch('pipeline.release.load_current',return_value=release),patch('dashboard.data.run_query',side_effect=query):
            app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'dashboard/app.py')).run(timeout=20)
            app.selectbox(key='q1_range').set_value('All available').run(timeout=20)
            self.assertEqual(len(app.exception),0);self.assertEqual(len(app.error),0)
            self.assertTrue(any('16,120' in m.value and '128' in m.value for m in app.markdown))
            daily=next(f.value for f in app.dataframe if 'Date' in f.value.columns);self.assertEqual(len(daily),28)
            ranking_sql=[s for s in observed if 'grouped_segments' in s]
            self.assertTrue(all("BETWEEN DATE '2031-07-01' AND DATE '2031-07-28'" in q for q in ranking_sql))
            self.assertFalse(any(g.key=='q1_ranking_period' for g in app.get('button_group')))
            app.selectbox(key='q1_range').set_value('Last 7 days').run(timeout=20)
            self.assertEqual(len(app.error),0);self.assertEqual(len(app.exception),0)
            self.assertIn("BETWEEN DATE '2031-07-22' AND DATE '2031-07-28'",next(q for q in reversed(observed) if 'grouped_segments' in q))
            app.selectbox(key='q1_range').set_value('Custom dates').run(timeout=20)
            app.selectbox(key='q1_start').set_value('2031-07-10').run(timeout=20)
            app.selectbox(key='q1_end').set_value('2031-07-20').run(timeout=20)
            self.assertEqual(len(app.error),0)
            self.assertIn("BETWEEN DATE '2031-07-10' AND DATE '2031-07-20'",next(q for q in reversed(observed) if 'grouped_segments' in q))

    def test_refresh_advances_rolling_window_and_retains_last_release_on_failure(self):
        import copy
        days=[(date(2033,12,1)+timedelta(days=i)).isoformat() for i in range(36)]
        base={'release_id':'synthetic-refresh-v1','dataset_version':'fixture','run_id':'refresh-v1','release_kind':'full','q1':{'dates':days[:35]},'q2':{'window_start':days[0],'window_end':days[-1]},'catalog':{'database':'fixture','q1_table':'q1'},'timestamp_policy':'dataset-local','warnings':[]}
        updated=copy.deepcopy(base);updated.update(release_id='synthetic-refresh-v2',run_id='refresh-v2');updated['q1']['dates']=days
        observed=[]
        def query(client,sql):
            observed.append(sql)
            if 'DISTINCT' in sql:return [{'currency':'US Dollar'}]
            start,end=re.search(r"BETWEEN DATE '([^']+)' AND DATE '([^']+)'",sql).groups();scope=[d for d in days if start<=d<=end]
            if 'GROUP BY event_date' in sql:return [{'event_date':d,'n':10000,'l':5} for d in scope]
            n=10000*len(scope);l=5*len(scope)
            return [{'payment_format':'ACH','n':n,'l':l,'baseline_n':n,'baseline_l':l,'rate':l/n,'lift':1,'support':'supported','selected_currency_amount':'0.47209301'}]
        session=Mock();session.client.return_value.get_caller_identity.return_value={'Account':'160885259244'}
        with patch.dict(os.environ,{'AML_AWS_PROFILE':'synthetic-refresh-test'}),patch('boto3.Session',return_value=session),patch('pipeline.release.load_current',side_effect=[base,updated,RuntimeError('injected incomplete publication')]),patch('dashboard.data.run_query',side_effect=query):
            app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'dashboard/app.py')).run(timeout=20)
            app.selectbox(key='q1_range').set_value('Last 7 days').run(timeout=20)
            self.assertIn("BETWEEN DATE '2033-12-29' AND DATE '2034-01-04'",observed[-1])
            app.button(key='refresh_monitoring').click().run(timeout=20)
            self.assertEqual(len(app.exception),0);self.assertEqual(len(app.error),0);self.assertEqual(app.selectbox(key='q1_range').value,'Last 7 days')
            self.assertIn("BETWEEN DATE '2033-12-30' AND DATE '2034-01-05'",observed[-1]);self.assertIn("run_id='refresh-v2'",observed[-1])
            app.button(key='refresh_monitoring').click().run(timeout=20)
            self.assertEqual(len(app.exception),0);self.assertEqual(app.session_state['release']['release_id'],'synthetic-refresh-v2')
            self.assertTrue(any('previous release is still selected' in error.value for error in app.error))



if __name__=='__main__':unittest.main()
