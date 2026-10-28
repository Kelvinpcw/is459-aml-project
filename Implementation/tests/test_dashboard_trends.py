import os,re,sqlite3,sys,unittest
from datetime import date,timedelta
from pathlib import Path
from unittest.mock import Mock,patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from dashboard.data import q1_trend_query
from dashboard.trends import daily_population,population_total,reporting_periods,endpoint_comparison,trend_chart
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

    def test_main_and_tail_split_has_no_overlap_and_plot_does_not_join_populations(self):
        self.assertEqual(reporting_periods('2022-09-01','2022-09-28'),[('Main period','2022-09-01','2022-09-16'),('Sparse tail','2022-09-17','2022-09-28')])
        self.assertEqual(reporting_periods('2022-09-17','2022-09-17'),[('Sparse tail','2022-09-17','2022-09-17')])
        daily=daily_population([{'event_date':'2022-09-16','n':1000,'l':10},{'event_date':'2022-09-17','n':10,'l':8}],'2022-09-16','2022-09-17',['2022-09-16','2022-09-17'])
        fig=trend_chart(daily);lines=[t for t in fig.data if t.type=='scatter'];self.assertEqual(len(lines),2);self.assertTrue(all(not t.connectgaps for t in lines));self.assertEqual(list(lines[0].y),[.01]);self.assertEqual(list(lines[1].y),[.8]);self.assertTrue(fig.layout.shapes)
        comparison=endpoint_comparison(daily);self.assertIn('10 → 8 (-2)',comparison);self.assertIn('different traffic populations',comparison)

    def test_full_range_app_renders_and_ranking_queries_stay_within_chosen_period(self):
        days=[(date(2022,9,1)+timedelta(days=i)).isoformat() for i in range(28)]
        release={'release_id':'synthetic-trend-range','dataset_version':'fixture','run_id':'run','release_kind':'full','q1':{'dates':days},'q2':{'window_start':days[0],'window_end':days[-1]},'catalog':{'database':'fixture','q1_table':'q1'},'timestamp_policy':'dataset-local','warnings':[]}
        observed=[]
        def query(client,sql):
            observed.append(sql)
            if 'DISTINCT' in sql:return [{'currency':'US Dollar'}]
            start,end=re.search(r"BETWEEN DATE '([^']+)' AND DATE '([^']+)'",sql).groups();scope=[d for d in days if start<=d<=end]
            rows=[{'event_date':d,'n':1000 if d<'2022-09-17' else 10,'l':2 if d<'2022-09-17' else 8} for d in scope]
            if 'GROUP BY event_date' in sql:return rows
            n=sum(r['n'] for r in rows);l=sum(r['l'] for r in rows)
            return [{'payment_format':'ACH','n':str(n),'l':str(l),'baseline_n':str(n),'baseline_l':str(l),'rate':l/n,'lift':'1','support':'supported' if n>=1000 else 'low_support','selected_currency_amount':'0.47209301'}]
        session=Mock();session.client.return_value.get_caller_identity.return_value={'Account':'160885259244'}
        with patch.dict(os.environ,{'AML_AWS_PROFILE':'synthetic-trend-test'}),patch('boto3.Session',return_value=session),patch('pipeline.release.load_current',return_value=release),patch('dashboard.data.run_query',side_effect=query):
            app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'dashboard/app.py')).run(timeout=20)
            app.selectbox(key='q1_end').set_value('2022-09-28').run(timeout=20)
            self.assertEqual(len(app.exception),0);self.assertEqual(len(app.error),0)
            self.assertTrue(any('16,120' in m.value and '128' in m.value for m in app.markdown))
            daily=next(f.value for f in app.dataframe if 'Date' in f.value.columns);self.assertEqual(len(daily),28)
            ranking_sql=[s for s in observed if 'grouped_segments' in s];self.assertTrue(all("AND DATE '2022-09-16'" in s for s in ranking_sql))
            app.button_group(key='q1_ranking_period').set_value('Sparse tail').run(timeout=20)
            self.assertEqual(len(app.error),0);self.assertEqual(len(app.exception),0)
            self.assertIn("BETWEEN DATE '2022-09-17' AND DATE '2022-09-28'",next(s for s in reversed(observed) if 'grouped_segments' in s))


if __name__=='__main__':unittest.main()
