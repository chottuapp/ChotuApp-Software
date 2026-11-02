import hashlib,json,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch,MagicMock
import audit804_delivery as delivery
from drive_sync import DriveOperationError,drive_command

class DriveErrors(unittest.TestCase):
 def test_safe_actionable_diagnostics_never_include_credentials(self):
  for detail,category in [('storageQuotaExceeded','storage_quota'),('userRateLimitExceeded','rate_limit'),('invalid_grant','authentication'),('insufficientFilePermissions','permission'),('Error 503','temporary_service')]:
   with self.subTest(category=category),patch('drive_sync.subprocess.run',return_value=SimpleNamespace(returncode=1,stderr=detail+' https://user:password@example.com?token=SECRET')):
    with self.assertRaises(DriveOperationError) as caught:drive_command('secret.conf','copy','private','private')
    self.assertEqual(caught.exception.category,category)
    self.assertNotIn('SECRET',str(caught.exception));self.assertNotIn('password',str(caught.exception));self.assertNotIn('private',str(caught.exception))

 def test_failed_delivery_is_retried_same_revision_and_keeps_verified_receipt(self):
  config=json.loads((delivery.ROOT/'cloud/drive-sync-release.json').read_text());config.pop('refresh_generation',None)
  store='Paklap';campaign=config['dispatcher'];receipt={'sha256':'previous-verified','shop_code':'old'}
  with tempfile.TemporaryDirectory() as tmp:
   source=Path(tmp)/'original.xlsx';source.write_bytes(b'original immutable input');sha=hashlib.sha256(source.read_bytes()).hexdigest()
   state={'audit804_campaign':campaign,'uploaded':{store:receipt},'audit804_results':{store:{'status':'hold','source_sha256':sha,'source_run':'1','held_input':'marker'}}}
   identity=MagicMock();identity.replace.side_effect=[DriveOperationError('copy','storageQuotaExceeded'),{'file_name':'Paklap.xlsx'}]
   def process(src,out,*args,**kwargs):out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(b'checked');return {}
   with patch('audit804_automation.refresh',return_value=('',0,[])),patch.object(delivery,'restore_source',return_value=source),patch.object(delivery,'normalize',return_value=(source,False)),patch('image_provenance_repair.repair',return_value=(source,[])),patch('owner_product_exclusions.apply',return_value=(source,[])),patch.object(delivery,'process',side_effect=process),patch.object(delivery,'audit',side_effect=lambda *a,**k:{'status':'pass','checked_utc':'now','products_checked':1,'workbook_sha256':'new','findings_count':0}),patch.object(delivery,'DriveIdentity',return_value=identity),patch.object(delivery,'save_held',return_value='marker'):
    delivery.run_campaign(state,config,[],lambda *a:'',lambda *a:'')
    self.assertEqual(state['uploaded'][store],receipt);self.assertNotIn(store,state['audit804_processed'])
    self.assertEqual(state['sync_status'],'pending_drive_delivery')
    self.assertEqual(state['audit804_results'][store]['audit_status'],'pass');self.assertEqual(state['audit804_results'][store]['delivery_status'],'blocked')
    delivery.run_campaign(state,config,[],lambda *a:'',lambda *a:'')
   self.assertEqual(identity.replace.call_count,2);self.assertEqual(state['uploaded'][store]['sha256'],'new');self.assertEqual(state['audit804_results'][store]['delivery_status'],'verified');self.assertIn(store,state['audit804_processed'])
