import subprocess,tempfile,unittest
from unittest.mock import patch
from cloud_sync_windows import readable_progress_report,Sync
class GlitchTests(unittest.TestCase):
 def test_done_store_does_not_look_incomplete_but_running_counts_remain(self):
  source='STORE STATUS\nRawayat: done\n  product prices and pages: 3500/3535 tasks\n  ETA unavailable\n  Last successful HTTP response (UTC): yesterday\nJunaid: running\n  product prices and pages: 4700/4807 tasks\n'
  result=readable_progress_report(source)
  self.assertNotIn('3500/3535',result);self.assertIn('4700/4807',result);self.assertIn('Rawayat: done',result);self.assertIn('yesterday',result)
 def test_hung_local_api_call_becomes_retryable_error(self):
  with tempfile.TemporaryDirectory() as tmp:
   sync=Sync('gh','owner/repo','123',tmp)
   with patch('cloud_sync_windows.subprocess.run',side_effect=subprocess.TimeoutExpired('gh',120)):
    with self.assertRaisesRegex(RuntimeError,'will retry'):sync.call(['run','view','123'])
if __name__=='__main__':unittest.main()
