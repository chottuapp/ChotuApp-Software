import json,tempfile,threading,unittest
from pathlib import Path
from unittest.mock import Mock,patch
from runtime import CloudService
from resume_support import RunStore
import drive_sync

class CompletedCheckpointResume(unittest.TestCase):
 def service(self,root,paused=False):
  output=root/'saved.xlsx';output.write_bytes(b'unchanged saved export');stat=output.stat()
  service=CloudService.__new__(CloudService);service.thread=None;service.lock=threading.RLock();service.event=Mock();service.store=RunStore(root/'state')
  service.store.save({'id':'original','status':'incomplete','sites':[{'name':'Gift4U' if paused else 'Saved Store','url':'https://gift4u.pk' if paused else 'https://example.com','status':'done','output':{'path':str(output),'size':stat.st_size,'mtime_ns':stat.st_mtime_ns}}]})
  return service,output
 def test_complete_valid_outputs_are_successfully_retained_without_scheduler(self):
  with tempfile.TemporaryDirectory() as folder:
   service,output=self.service(Path(folder));before=output.read_bytes()
   with patch.dict('os.environ',{'CLOUD_RUNNER_GROUP':''}),patch('runtime.StoreScheduler') as scheduler:
    service.start(resume=True)
   self.assertEqual(service.store.load()['status'],'complete');self.assertEqual(output.read_bytes(),before);scheduler.assert_not_called()
 def test_owner_pause_is_still_enforced(self):
  with tempfile.TemporaryDirectory() as folder:
   service,_=self.service(Path(folder),paused=True)
   with self.assertRaisesRegex(ValueError,'OWNER PAUSED'):service.start(resume=True)
 def test_absent_state_is_not_complete(self):
  with tempfile.TemporaryDirectory() as folder:
   service,_=self.service(Path(folder));service.store.load=Mock(return_value=None)
   with self.assertRaisesRegex(ValueError,'No saved run'):service.start(resume=True)

class FreshDeliveryGeneration(unittest.TestCase):
 def config(self,root,**changes):
  (root/'cloud').mkdir();base={'dispatcher':'campaign','audit804_enabled':True,'stores':['Saved Store'],'destination_folder':'Approved','refresh_generation':'old','refresh_stores':['Old Store']}
  request={'campaign_id':'campaign','refresh_generation':'new','destination_folder':'Approved','requested_date_pkt':'2026-11-12'};request.update(changes)
  (root/'cloud/drive-sync-release.json').write_text(json.dumps(base));(root/'cloud/audit804-release.json').write_text(json.dumps(request));(root/'cloud/fetch-update-release.json').write_text(json.dumps({'fresh_stores':[{'name':'Saved Store','url':'https://example.com','enabled':True}]}))
 def test_delivery_follows_current_authorized_generation_without_manual_second_config_edit(self):
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder);self.config(root)
   with patch.object(drive_sync,'ROOT',root):result=drive_sync.load_config()
   self.assertEqual(result['refresh_generation'],'new');self.assertEqual(result['refresh_stores'],['Saved Store']);self.assertEqual(result['destination_folder'],'Approved')
 def test_different_campaign_cannot_redirect_delivery(self):
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder);self.config(root,campaign_id='unapproved')
   with patch.object(drive_sync,'ROOT',root):self.assertEqual(drive_sync.load_config()['refresh_generation'],'old')
 def test_destination_cannot_change_silently(self):
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder);self.config(root,destination_folder='Other')
   with patch.object(drive_sync,'ROOT',root),self.assertRaisesRegex(ValueError,'destination'):drive_sync.load_config()
 def test_fresh_registry_cannot_bypass_store_allowlist(self):
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder);self.config(root);p=root/'cloud/drive-sync-release.json';c=json.loads(p.read_text());c['stores']=[];p.write_text(json.dumps(c))
   with patch.object(drive_sync,'ROOT',root),self.assertRaisesRegex(ValueError,'outside approved'):drive_sync.load_config()
 def test_current_saved_resume_record_seeds_exact_store_checked_roots(self):
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder);self.config(root);(root/'catalog-reports').mkdir()
   record={'refresh_generation':'new','groups':[{'parent_run':'123','runner_group':'audit804-campaign-new-1','stores':['Saved Store']}]}
   (root/'catalog-reports/fetch-resume-20261112.json').write_text(json.dumps(record))
   with patch.object(drive_sync,'ROOT',root):self.assertEqual(drive_sync.load_config()['refresh_root_run_ids'],['123'])
   record['groups'][0]['stores']=['Other Store'];(root/'catalog-reports/fetch-resume-20261112.json').write_text(json.dumps(record))
   with patch.object(drive_sync,'ROOT',root),self.assertRaisesRegex(ValueError,'approved store plan'):drive_sync.load_config()
