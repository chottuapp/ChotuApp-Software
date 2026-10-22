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

class NetworkResumeTests(unittest.TestCase):
 def test_disconnect_and_server_failure_resume_same_request(self):
  ok=Mock(status_code=200);busy=Mock(status_code=503)
  request=Mock(side_effect=[backend.requests.ConnectionError('offline'),busy,ok]);notify=Mock();wait=Mock()
  self.assertIs(backend.retry_network(request,lambda:None,notify,wait),ok)
  self.assertEqual(request.call_count,3);busy.close.assert_called_once();self.assertEqual(notify.call_args.args,(False,))
 def test_pause_interrupts_network_wait(self):
  check=Mock(side_effect=[None,backend.Paused()]);request=Mock(side_effect=backend.requests.Timeout())
  with self.assertRaises(backend.Paused):backend.retry_network(request,check,wait=Mock())
  self.assertEqual(request.call_count,1)
 def test_tls_and_access_errors_are_not_retried(self):
  request=Mock(side_effect=backend.requests.exceptions.SSLError('invalid certificate'))
  with self.assertRaises(backend.requests.exceptions.SSLError):backend.retry_network(request,lambda:None,wait=Mock())
  self.assertEqual(request.call_count,1)
  denied=Mock(status_code=403);request=Mock(return_value=denied)
  self.assertIs(backend.retry_network(request,lambda:None,wait=Mock()),denied);self.assertEqual(request.call_count,1)

class GitHubConnectionTests(unittest.TestCase):
 def test_read_access_does_not_hide_failed_heartbeat_write(self):
  with patch.object(backend,'verify_token',return_value='Connected'),patch.object(backend,'sync_logs',return_value=json.dumps({'status':'retry_pending','message':'GitHub denied access'})):
   result=json.loads(backend.connect_github('/unused','private-fixture'))
  self.assertEqual(result['status'],'connection_failed');self.assertIn('denied',result['message']);self.assertNotIn('private-fixture',json.dumps(result))
 def test_connection_requires_first_successful_remote_write(self):
  with patch.object(backend,'verify_token',return_value='Connected'),patch.object(backend,'sync_logs',return_value=json.dumps({'status':'synced','last_success_utc':'2026-10-21T10:00:00Z'})) as send:
   self.assertEqual(json.loads(backend.connect_github('/unused','fixture',True))['status'],'connected');self.assertTrue(send.call_args.args[2])
 def test_concurrent_branch_update_retries_latest_file_sha(self):
  with tempfile.TemporaryDirectory() as tmp:
   session=Mock();session.get.side_effect=[Mock(status_code=200),Mock(status_code=404),Mock(status_code=200,json=Mock(return_value={'sha':'newer-file-sha'}))];session.put.side_effect=[Mock(status_code=409),Mock(status_code=201)]
   with patch.object(backend.requests,'Session',return_value=session):result=json.loads(backend.sync_logs(tmp,'fixture',True))
   self.assertEqual(result['status'],'synced');self.assertEqual(session.put.call_count,2);self.assertEqual(session.put.call_args.kwargs['json']['sha'],'newer-file-sha')

class NativeHeartbeatTests(unittest.TestCase):
 def test_native_reporter_does_not_spawn_duplicate_python_sender(self):
  bridge=Mock();bridge.hasNativeReporter.return_value=True
  with tempfile.TemporaryDirectory() as tmp,patch.object(backend,'sync_logs') as send:
   with backend.reporting(Path(tmp),bridge,''):pass
   send.assert_not_called()
 def test_heartbeat_declares_real_reporting_target_without_claiming_progress(self):
  with tempfile.TemporaryDirectory() as tmp:
   report=backend.mobile_report(Path(tmp),'',False)
   self.assertEqual(report['app_version'],'1.5-studio');self.assertEqual(report['heartbeat_target_seconds'],30)
   self.assertFalse(report['worker_active']);self.assertIsNone(report['progress_age_seconds'])

class LiveRunnerOverlayTests(unittest.TestCase):
 def test_live_state_updates_without_fabricating_source_progress(self):
  old={'runs':[{'databaseId':1,'status':'in_progress','stores':{'A':'running'},'snapshot':'old source progress','snapshot_utc':'2026-10-20T00:00:00Z'}]}
  response=Mock();response.json.return_value={'workflow_runs':[{'id':1,'status':'completed','conclusion':'failure'},{'id':2,'status':'in_progress','display_title':'Saved LAAM'}]}
  with patch.object(backend.requests,'get',return_value=response):result=backend.live_runner_states(old,'fixture')
  self.assertEqual(result['active_runners'],1);self.assertEqual(result['runs'][1]['snapshot'],'old source progress')
  self.assertTrue(result['runs'][1]['snapshot_stale']);self.assertEqual(result['runs'][1]['snapshot_utc'],'2026-10-20T00:00:00Z')
  self.assertEqual(old['runs'][0]['status'],'in_progress')
 def test_missing_token_does_not_send_anonymous_rate_limited_api_polls(self):
  with patch.object(backend.requests,'get') as get:
   backend.live_runner_states({},'');get.assert_not_called()
