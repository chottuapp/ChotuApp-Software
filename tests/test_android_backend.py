import importlib.util,json,tempfile,unittest,sys
from pathlib import Path
from unittest.mock import Mock,patch
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('android_backend',ROOT/'android/app/src/main/python/mobile_backend.py');backend=importlib.util.module_from_spec(spec);spec.loader.exec_module(backend)
class AndroidBackendTests(unittest.TestCase):
 def exported(self,root):
  folder=root/'files';folder.mkdir();f=folder/'Khaadi.xlsx';f.write_bytes(b'xlsx');(root/'local-status.json').write_text(json.dumps({'status':'exported_review_required','files':[str(f)]}))
 def test_pause_does_not_upload_saved_file(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);self.exported(root)
   with patch.object(backend,'upload') as upload,patch.object(backend.requests,'Session'):
    with self.assertRaises(backend.Paused):backend.run(tmp,tmp,'secret',Mock(isPaused=Mock(return_value=True)))
    upload.assert_not_called()
 def test_existing_export_does_not_refetch_without_credentials(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);self.exported(root)
   with patch.object(backend,'load',side_effect=AssertionError('must not refetch')):
    result=json.loads(backend.run(tmp,tmp,'',Mock(spec=['isPaused'],isPaused=Mock(return_value=False))));self.assertEqual(result['status'],'ready_to_upload')
 def test_failed_upload_never_queues_marker(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);self.exported(root);session=Mock();session.get.return_value=Mock(status_code=404);session.put.return_value=Mock(status_code=403)
   with patch.object(backend.requests,'Session',return_value=session):
    with self.assertRaises(RuntimeError):backend.upload(root,'secret')
   self.assertEqual(session.put.call_count,1);self.assertTrue((root/'files/Khaadi.xlsx').exists())
 def test_embedded_headless_bundle_exports_captured_product(self):
  spec=importlib.util.spec_from_file_location('prepare_android_bundle',ROOT/'android/tools/prepare.py');bundle=importlib.util.module_from_spec(spec);spec.loader.exec_module(bundle);bundle.prepare()
  with tempfile.TemporaryDirectory() as tmp,patch('builtins.print'):
   self.assertEqual(backend.self_test(ROOT/'android/app/src/main/python/engine',tmp),'Embedded export verified')
 def test_remote_log_snapshot_redacts_tokens_and_separates_android_path(self):
  import base64
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);token='github_pat_privatefixture';(root/'local-status.json').write_text(json.dumps({'status':'running','last_event':'HTTP 200','error':'Bearer '+token}));(root/'fetch-log.txt').write_text('HTTP 200 products 20\nAuthorization: Bearer '+token+'\nrequest '+token+'\n')
   session=Mock();session.get.side_effect=[Mock(status_code=200),Mock(status_code=404)];session.put.return_value=Mock(status_code=201)
   with patch.object(backend.requests,'Session',return_value=session):result=json.loads(backend.sync_logs(root,token,True))
   self.assertEqual(result['status'],'synced');endpoint=session.put.call_args.args[0];self.assertTrue(endpoint.endswith('/local/khaadi-android.json'))
   report=json.loads(base64.b64decode(session.put.call_args.kwargs['json']['content']));self.assertNotIn(token,json.dumps(report));self.assertTrue(report['worker_active']);self.assertIn('HTTP 200 products 20',report['log_tail'])
 def test_missing_connection_is_visible_without_network_or_stopping_fetch(self):
  with tempfile.TemporaryDirectory() as tmp,patch.object(backend.requests,'Session') as session:
   result=json.loads(backend.sync_logs(tmp,'',True));self.assertEqual(result['status'],'connection_required');session.assert_not_called()
 def test_failed_remote_write_is_not_reported_synced(self):
  with tempfile.TemporaryDirectory() as tmp:
   session=Mock();session.get.side_effect=[Mock(status_code=200),Mock(status_code=404)];session.put.return_value=Mock(status_code=403)
   with patch.object(backend.requests,'Session',return_value=session):result=json.loads(backend.sync_logs(tmp,'secret',True))
   self.assertEqual(result['status'],'retry_pending');self.assertNotIn('secret',json.dumps(result))
 def test_terminal_snapshot_never_claims_worker_is_active(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);(root/'local-status.json').write_text(json.dumps({'status':'running'}));report=backend.mobile_report(root,'',False)
   self.assertEqual(report['status'],'stopped');self.assertFalse(report['worker_active'])
 def test_reporter_picks_up_new_connection_while_fetching_and_sends_terminal_event(self):
  import threading
  with tempfile.TemporaryDirectory() as tmp:
   first=threading.Event();terminal=threading.Event();bridge=Mock();bridge.githubToken.return_value='new-connection';bridge.isActive.return_value=True;bridge.isPaused.return_value=False
   def sync(data,token,active,paused):
    self.assertEqual(token,'new-connection')
    if active:first.set()
    else:terminal.set()
   with patch.object(backend,'sync_logs',side_effect=sync):
    with backend.reporting(Path(tmp),bridge,''):self.assertTrue(first.wait(2))
    self.assertTrue(terminal.wait(2))
 def test_connection_added_during_fetch_is_used_for_final_upload(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);self.exported(root);bridge=Mock();bridge.isPaused.return_value=False;bridge.githubToken.return_value='new-token'
   with patch.object(backend,'upload',return_value='a'*64) as upload:
    result=json.loads(backend._run(tmp,tmp,'',bridge));self.assertEqual(result['status'],'cloud_queued');self.assertEqual(upload.call_args.args[1],'new-token')
