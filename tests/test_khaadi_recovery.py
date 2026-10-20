import importlib.util,json,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('khaadi_recovery',ROOT/'catalog-tools/watch_khaadi_recovery_windows.py');recovery=importlib.util.module_from_spec(spec);spec.loader.exec_module(recovery)
class RecoveryTests(unittest.TestCase):
 def test_local_telemetry_does_not_claim_dead_worker_is_running(self):
  import time
  from unittest.mock import patch
  with tempfile.TemporaryDirectory() as tmp:
   data=Path(tmp);(data/'local-status.json').write_text(json.dumps({'status':'running','worker_pid':123,'last_progress_epoch':time.time(),'token':'never-publish'}))
   with patch.object(recovery,'occupied',return_value=False):report=recovery.local_report(data)
   self.assertEqual(report['status'],'stopped');self.assertFalse(report['worker_active']);self.assertNotIn('token',report);self.assertNotIn('worker_pid',report)
 def test_network_errors_retry_but_parser_stock_currency_and_tls_do_not(self):
  for error in ('SOURCE PAUSED: temporary server 500','curl failed: curl: (28) timed out','curl failed: curl: (6) resolve failed'):self.assertTrue(recovery.transient(error),error)
  for error in ('ADAPTER ERROR: price mismatch','Currency unverified','Stock ambiguous','curl failed: curl: (60) SSL certificate error','list index out of range'):self.assertFalse(recovery.transient(error),error)
 def test_new_release_retries_parser_but_same_release_waits(self):
  state={'status':'failed_resume_available','error':'ADAPTER ERROR: price mismatch'}
  self.assertEqual(recovery.action(2,state,'a','a'),'wait_for_fix');self.assertEqual(recovery.action(2,state,'b','a'),'new_release')
 def test_manual_stop_and_completion_never_restart(self):
  self.assertEqual(recovery.action(130,{},'new','old'),'manual_stop')
  self.assertEqual(recovery.action(2,{'status':'paused'},'new','old'),'manual_stop')
  self.assertEqual(recovery.action(0,{'status':'exported_review_required'},'new','old'),'complete')
 def test_existing_worker_lock_is_detected_and_released(self):
  with tempfile.TemporaryDirectory() as tmp:
   path=Path(tmp)/'active.lock'
   with recovery.lease(path):self.assertTrue(recovery.occupied(path))
   self.assertFalse(recovery.occupied(path))
 def test_release_requires_pinned_commit_and_hash(self):
  for spec in ({},{'commit':'main','sha256':'a'*64},{'commit':'b'*40,'sha256':'bad'}):
   with self.assertRaises(ValueError):recovery.release_spec({'schema':1,'khaadi_worker':spec})
  expected={'commit':'b'*40,'sha256':'a'*64};self.assertEqual(recovery.release_spec({'schema':1,'khaadi_worker':expected}),expected)
 def test_published_worker_hash_matches_approved_version(self):
  import hashlib
  marker=json.loads((ROOT/'cloud/recovery-release.json').read_text());spec=recovery.release_spec(marker)
  payload=(ROOT/'catalog-tools/start_khaadi_local_fetch_windows.py').read_bytes()
  self.assertEqual(hashlib.sha256(payload).hexdigest(),spec['sha256'])
