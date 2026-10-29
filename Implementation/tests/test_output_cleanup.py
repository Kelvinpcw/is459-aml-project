import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'deployment'))
from cleanup_run_outputs import candidates
class CleanupTests(unittest.TestCase):
    def test_source_pointer_and_new_release_rejected(self):
        for key in ['raw/old/data','references/annotations/a','scripts/full-v6/a','published/current.json','curated/run_id=new/data','published/releases/new/manifest.json','gold/../raw/a']:
            with self.subTest(key=key),self.assertRaises(ValueError):candidates([{'Key':key,'ETag':'"abc"'}],'new')
    def test_only_exact_old_keys_with_nonwildcard_etags(self):
        item={'Key':'gold/risk/run_id=old/file.parquet','ETag':'"abc"'}
        self.assertEqual(candidates([item],'new'),[{'Key':item['Key'],'ETag':'abc'}])
        with self.assertRaises(ValueError):candidates([item,item],'new')
        with self.assertRaises(ValueError):candidates([dict(item,ETag='*')],'new')
if __name__=='__main__':unittest.main()
