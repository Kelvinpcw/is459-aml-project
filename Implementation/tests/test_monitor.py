"""Budget cancellation and private-record regressions use mocked AWS clients."""
import contextlib,datetime,io,json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import Mock,patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'deployment'))
import monitor


class MonitorTests(unittest.TestCase):
    def execute(self,root,over_budget=False):
        private=root/'Implementation/data/aws-operations-20261028';private.mkdir(parents=True)
        ledger={'full_completion':{},'paid_resources_started_by_this_project':[],'active_paid_resources':[]}
        (private/'resource-ledger.json').write_text(json.dumps(ledger))
        reviews=root/'Implementation/aws/reviews';reviews.mkdir(parents=True)
        (reviews/'full-recovery1-start.json').write_text(json.dumps({'executionArn':'recovery'}))
        public=root/'Implementation/aws/resource-ledger.json';public.write_text('historical-public-snapshot')
        sts=Mock();sts.get_caller_identity.return_value={'Account':'160885259244'}
        sf=Mock();sf.describe_execution.return_value={'status':'RUNNING'}
        glue=Mock();now=datetime.datetime.now(datetime.timezone.utc)
        run={'Id':'owned-detect','JobRunState':'RUNNING' if over_budget else 'SUCCEEDED','ExecutionTime':28800 if over_budget else 60,'StartedOn':now-datetime.timedelta(seconds=28800 if over_budget else 60),'NumberOfWorkers':10}
        glue.get_job_runs.side_effect=lambda **kw:{'JobRuns':[run] if kw['JobName']=='is459-aml-full-detect' else []}
        session=Mock();session.client.side_effect={'sts':sts,'stepfunctions':sf,'glue':glue}.__getitem__
        with patch.object(monitor,'ROOT',root),patch('boto3.Session',return_value=session),patch.object(sys,'argv',['monitor','--profile','synthetic','--enforce-budget']),patch.object(monitor.subprocess,'run') as verify,contextlib.redirect_stdout(io.StringIO()):
            monitor.main()
        self.assertEqual(public.read_text(),'historical-public-snapshot')
        return sf,glue,json.loads((private/'resource-ledger.json').read_text()),json.loads((reviews/'full-monitor-latest.json').read_text())

    def test_existing_private_ledger_updated_without_touching_public_snapshot(self):
        with tempfile.TemporaryDirectory() as d:
            sf,glue,ledger,result=self.execute(Path(d))
            self.assertEqual(ledger['full_completion']['status'],'RUNNING')
            self.assertEqual(ledger['active_paid_resources'],[])
            self.assertEqual(len(ledger['paid_resources_started_by_this_project']),1)
            sf.stop_execution.assert_not_called();glue.batch_stop_job_run.assert_not_called()
            self.assertLess(result['guard_total_estimate_usd'],28)

    def test_budget_guard_stops_only_owned_active_runs(self):
        with tempfile.TemporaryDirectory() as d:
            sf,glue,ledger,result=self.execute(Path(d),True)
            self.assertTrue(result['budget_stop_requested'])
            sf.stop_execution.assert_called_once()
            glue.batch_stop_job_run.assert_called_once_with(JobName='is459-aml-full-detect',JobRunIds=['owned-detect'])
            self.assertEqual(len(ledger['active_paid_resources']),1)

if __name__=='__main__':unittest.main()
