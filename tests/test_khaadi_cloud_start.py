import json,tempfile,unittest,os
from pathlib import Path
from unittest.mock import patch
from start_khaadi_cloud import main
class KhaadiCloudStartTests(unittest.TestCase):
 def fixture(self,folder,verified):
  (folder/'source-diagnostics').mkdir();(folder/'cloud').mkdir()
  (folder/'source-diagnostics/khaadi-public-route.json').write_text(json.dumps({'sample_verified':verified}))
  (folder/'cloud/audit804-release.json').write_text(json.dumps({'campaign_id':'fresh804-20261021-a26dcd86'}))
 def test_unverified_source_never_dispatches_foreign_prices(self):
  with tempfile.TemporaryDirectory() as tmp:
   folder=Path(tmp);self.fixture(folder,False)
   old=Path.cwd()
   try:
    os.chdir(folder)
    with patch('start_khaadi_cloud.gh') as gh:
     with self.assertRaisesRegex(ValueError,'not verified'):main()
     gh.assert_not_called()
   finally:os.chdir(old)
 def test_verified_source_dispatches_fresh_khaadi_only_and_deduplicates(self):
  with tempfile.TemporaryDirectory() as tmp:
   folder=Path(tmp);self.fixture(folder,True);old=Path.cwd()
   try:
    os.chdir(folder)
    with patch('start_khaadi_cloud.gh',side_effect=['[]','new run']) as gh:
     main();args=gh.call_args.args;self.assertIn('stores=Khaadi | https://pk.khaadi.com',args);self.assertIn('auto_continue_limit=48',args);self.assertFalse(any(str(a).startswith('resume_run_id=') for a in args))
    with patch('start_khaadi_cloud.gh',return_value=json.dumps([{'displayTitle':'Cloud group audit804-fresh804-20261021-a26dcd86-khaadi-cloud'}])) as gh:
     main();self.assertEqual(gh.call_count,1)
   finally:os.chdir(old)
