import json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace
import audit804_delivery as delivery
from drive_sync import GitHubOperationError,gh

class DownloadRecoveryTests(unittest.TestCase):
 def test_partial_download_retries_in_clean_directory_and_clears_old_error(self):
  state={'audit804_source_download_errors':{'1':{'error':'old'}}};calls=[]
  def fetch(*args):
   stage=Path(args[-1]);self.assertFalse(list(stage.iterdir()));calls.append(stage)
   if len(calls)==1:
    (stage/'partial.xlsx').write_bytes(b'partial')
    raise GitHubOperationError(args,'HTTP 502: gateway failure')
   (stage/'complete.xlsx').write_bytes(b'complete')
  with tempfile.TemporaryDirectory() as tmp,patch.object(delivery.time,'sleep'):
   out=delivery.download_source(fetch,'1',2,tmp,state)
   self.assertEqual((out/'complete.xlsx').read_bytes(),b'complete');self.assertNotEqual(calls[0],calls[1]);self.assertFalse(state['audit804_source_download_errors'])
 def test_permanent_failure_preserves_verified_state_and_does_not_mark_artifact_processed(self):
  receipt={'sha256':'verified'};state={'uploaded':{'A':receipt},'audit804_artifacts':{}}
  with tempfile.TemporaryDirectory() as tmp,patch.object(delivery.time,'sleep') as sleep:
   result=delivery.download_source(lambda *a:(_ for _ in ()).throw(GitHubOperationError(a,'HTTP 403: access denied')),'1',2,tmp,state)
  self.assertIsNone(result);sleep.assert_not_called();self.assertEqual(state['uploaded'],{'A':receipt});self.assertEqual(state['audit804_artifacts'],{});self.assertEqual(state['audit804_source_download_errors']['1']['attempts'],1)
 def test_failed_run_does_not_block_next_run_or_claim_complete_scan(self):
  root=delivery.ROOT;config=json.loads((root/'cloud/drive-sync-release.json').read_text());generation=config['refresh_generation'];campaign=config['dispatcher']
  runs=[{'databaseId':2,'displayTitle':'Cloud group audit804-'+campaign+'-'+generation+'-2'},{'databaseId':1,'displayTitle':'Cloud group audit804-'+campaign+'-'+generation+'-1'}];seen=[];state={'uploaded':{'Existing':{'sha256':'old'}}}
  def fetch(*args):
   if args[0]=='api':return json.dumps({'artifacts':[{'id':7,'name':'chotuapp-excel-files'}]})
   if args[:2]==('run','download'):
    seen.append(args[2])
    if args[2]=='1':raise GitHubOperationError(args,'HTTP 403: access denied')
    return ''
   raise AssertionError(args)
  with patch('audit804_automation.refresh',return_value=('',0,[])),patch.object(delivery,'completed_files',return_value=[]):
   delivery.run_campaign(state,config,runs,fetch,lambda *a:None)
  self.assertEqual(seen,['1','2']);self.assertIn('1',state['audit804_source_download_errors']);self.assertIn('2',state['audit804_artifacts']);self.assertNotIn('1',state['audit804_artifacts']);self.assertEqual(state['uploaded'],{'Existing':{'sha256':'old'}});self.assertEqual(state['sync_status'],'pending_source_artifacts')
 def test_preserved_continuation_reopens_artifact_when_store_leaves_fresh_scope(self):
  config=json.loads((delivery.ROOT/'cloud/drive-sync-release.json').read_text())
  store='Asim Jofa'
  config.update(preserve_active_run_ids=['10'],refresh_stores=[store],additional_completed_sources=[])
  runs=[{'databaseId':11,'displayTitle':'Automatic continuation of 10'}]
  state={}
  def fetch(*args):
   if args[0]=='api':
    return json.dumps({'artifacts':[{'id':7,'name':'chotuapp-excel-files'}]})
   stage=Path(args[-1])
   (stage/(store+'.xlsx')).write_bytes(b'source workbook')
  files=[{'store':store,'name':store+'.xlsx','complete':True}]
  with patch('audit804_automation.refresh',return_value=('',0,[])),patch.object(delivery,'completed_files',return_value=files),patch.object(delivery,'normalize',side_effect=ValueError('test audit gate')) as normalize,patch.object(delivery,'save_held',return_value='input/manifest.json'):
   delivery.run_campaign(state,config,runs,fetch,lambda *a:None)
   normalize.assert_not_called()
   first_receipt=state['audit804_artifacts']['11']
   config['refresh_stores']=[]
   delivery.run_campaign(state,config,runs,fetch,lambda *a:None)
   normalize.assert_called_once()
   self.assertNotEqual(state['audit804_artifacts']['11'],first_receipt)
   self.assertEqual(state['audit804_results'][store]['source_run'],'11')
   self.assertEqual(state['audit804_results'][store]['delivery_status'],'blocked')
   self.assertNotIn(store,state.get('uploaded',{}))
 def test_invalid_export_receipt_leaves_verified_copy_and_other_runs_processable(self):
  config=json.loads((delivery.ROOT/'cloud/drive-sync-release.json').read_text())
  campaign=config['dispatcher'];generation=config['refresh_generation']
  config['additional_completed_sources']=[]
  prefix='Cloud group audit804-'+campaign+'-'+generation+'-'
  runs=[{'databaseId':20,'displayTitle':prefix+'1'},{'databaseId':21,'displayTitle':prefix+'2'}]
  verified={'sha256':'old'}
  state={'uploaded':{'Bata':verified}}
  def fetch(*args):
   if args[0]=='api':return json.dumps({'artifacts':[{'id':7,'name':'chotuapp-excel-files'}]})
   stage=Path(args[-1]);files=[]
   if args[2]=='21':
    (stage/'Bata.xlsx').write_bytes(b'changed bytes')
    files=[{'store':'Bata','name':'Bata.xlsx','complete':True,'sha256':'wrong'}]
   (stage/'completion-manifest.json').write_text(json.dumps({'files':files}))
  with patch('audit804_automation.refresh',return_value=('',0,[])),patch.object(delivery,'normalize') as normalize:
   delivery.run_campaign(state,config,runs,fetch,lambda *a:None)
   normalize.assert_not_called()
  self.assertEqual(state['uploaded']['Bata'],verified)
  self.assertIn('checksum mismatch',state['audit804_source_download_errors']['21']['error'])
  self.assertNotIn('21',state['audit804_artifacts'])
  self.assertIn('20',state['audit804_artifacts'])
 def test_two_approved_stores_in_one_artifact_both_reach_audit(self):
  config=json.loads((delivery.ROOT/'cloud/drive-sync-release.json').read_text())
  stores=('Bata','Breakout')
  config['additional_completed_sources']=[{'store':store,'run_id':'77','refresh_generation':config['refresh_generation']} for store in stores]
  run={'id':77,'head_branch':'main','path':'.github/workflows/cloud-fetch.yml','event':'workflow_dispatch',
       'head_repository':{'full_name':'chottuapp/ChotuApp-Software'},'status':'completed','conclusion':'success',
       'display_title':'Cloud group requested','head_sha':'a'*40}
  state={}
  def fetch(*args):
   if args[0]=='api':
    return json.dumps({'artifacts':[{'id':7,'name':'chotuapp-excel-files'}]} if 'artifacts' in args[1] else run)
   stage=Path(args[-1])
   for store in stores:(stage/(store+'.xlsx')).write_bytes(store.encode())
  files=[{'store':store,'name':store+'.xlsx','complete':True} for store in stores]
  with patch('audit804_automation.refresh',return_value=('',0,[])),patch.object(delivery,'completed_files',return_value=files),patch.object(delivery,'normalize',side_effect=ValueError('test audit gate')) as normalize,patch.object(delivery,'save_held',return_value='input/manifest.json'):
   delivery.run_campaign(state,config,[],fetch,lambda *a:None)
  self.assertEqual(normalize.call_count,2)
  self.assertTrue(all('77:'+store in state['audit804_artifacts'] for store in stores))

 def test_transient_download_failure_stops_after_three_attempts(self):
  calls=[];state={}
  def fetch(*args):
   calls.append(args);raise GitHubOperationError(args,'HTTP 503: unavailable')
  with tempfile.TemporaryDirectory() as tmp,patch.object(delivery.time,'sleep'):
   self.assertIsNone(delivery.download_source(fetch,'1',2,tmp,state))
  self.assertEqual(len(calls),3);self.assertEqual(state['audit804_source_download_errors']['1']['attempts'],3)
 def test_report_read_failure_never_replaces_saved_state_with_empty_state(self):
  import drive_sync,os
  config='[chotudrive]\ntype = drive\ntoken = {}\n'
  with patch.dict(os.environ,{'CHOTU_DRIVE_RCLONE_CONFIG':config}),patch.object(drive_sync,'gh',side_effect=GitHubOperationError(('api','contents'),'HTTP 503: unavailable')),patch.object(drive_sync,'publish') as publish:
   with self.assertRaises(GitHubOperationError):drive_sync.main()
  publish.assert_not_called()
 def test_error_diagnostic_redacts_credentials(self):
  with patch('drive_sync.subprocess.run',return_value=SimpleNamespace(returncode=1,stderr='HTTP 502: https://user:pass@example.com/file?token=secret')):
   with self.assertRaises(GitHubOperationError) as raised:gh('run','download','1')
  self.assertNotIn('user:pass',str(raised.exception));self.assertNotIn('token=secret',str(raised.exception));self.assertTrue(raised.exception.transient)

class HeldRestoreRecoveryTests(unittest.TestCase):
 def test_missing_manifest_keeps_receipts_and_reaches_original_artifact_fallback(self):
  import requests
  root=delivery.ROOT;config=json.loads((root/'cloud/drive-sync-release.json').read_text());store='Alkaram Studio';campaign=config['dispatcher'];generation=config['refresh_generation']
  report={'status':'pass','store':store,'source_run':'1','source_sha256':'a'*64};receipt={'sha256':'verified','shop_code':''}
  state={'audit804_campaign':campaign,'uploaded':{store:receipt},'audit804_results':{store:report}};seen=[]
  runs=[{'databaseId':1,'displayTitle':'Cloud group audit804-'+campaign+'-'+generation+'-1'}]
  def fetch(*args):
   seen.append(args)
   if args[0]=='api':return json.dumps({'artifacts':[{'id':7,'name':'chotuapp-excel-files'}]})
   if args[:2]==('run','download'):return ''
   raise AssertionError(args)
  with patch('audit804_automation.refresh',return_value=('',0,[])),patch.object(delivery,'restore_held',side_effect=requests.HTTPError('404 missing manifest')),patch.object(delivery,'completed_files',return_value=[]):
   delivery.run_campaign(state,config,runs,fetch,lambda *a:None)
  self.assertTrue(any(a[:2]==('run','download') for a in seen));self.assertEqual(state['uploaded'][store],receipt);self.assertEqual(state['audit804_results'][store],report);self.assertNotIn(store,state['audit804_processed']);self.assertIn(store,state['audit804_source_restore_errors']);self.assertEqual(state['sync_status'],'pending_source_artifacts')
 def test_corrupt_input_is_not_used_or_marked_processed(self):
  state={'uploaded':{'A':{'sha256':'verified'}}}
  with tempfile.TemporaryDirectory() as tmp:
   out=Path(tmp)/'A.xlsx'
   def corrupt(*args):out.write_bytes(b'partial');raise ValueError('Held workbook changed')
   with patch.object(delivery,'restore_held',side_effect=corrupt):self.assertIsNone(delivery.restore_source('marker',out,'A','campaign',state))
   self.assertFalse(out.exists());self.assertEqual(state['uploaded'],{'A':{'sha256':'verified'}})
 def test_successful_restore_clears_prior_source_error(self):
  state={'audit804_source_restore_errors':{'A':{'error':'old'}}}
  with patch.object(delivery,'restore_held',return_value=Path('A.xlsx')):
   self.assertEqual(delivery.restore_source('marker',Path('A.xlsx'),'A','campaign',state),Path('A.xlsx'))
  self.assertEqual(state['audit804_source_restore_errors'],{})
