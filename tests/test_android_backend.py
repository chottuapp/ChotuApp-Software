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
   with patch.object(backend,'upload') as upload:
    with self.assertRaises(backend.Paused):backend.run(tmp,tmp,'secret',Mock(isPaused=Mock(return_value=True)))
    upload.assert_not_called()
 def test_existing_export_does_not_refetch_without_credentials(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);self.exported(root)
   with patch.object(backend,'load',side_effect=AssertionError('must not refetch')):
    result=json.loads(backend.run(tmp,tmp,'',Mock(isPaused=Mock(return_value=False))));self.assertEqual(result['status'],'ready_to_upload')
 def test_failed_upload_never_queues_marker(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);self.exported(root);session=Mock();session.get.return_value=Mock(status_code=404);session.put.return_value=Mock(status_code=403)
   with patch.object(backend.requests,'Session',return_value=session):
    with self.assertRaises(RuntimeError):backend.upload(root,'secret')
   self.assertEqual(session.put.call_count,1);self.assertTrue((root/'files/Khaadi.xlsx').exists())
 def test_embedded_headless_bundle_exports_captured_product(self):
  with tempfile.TemporaryDirectory() as tmp,patch('builtins.print'):
   self.assertEqual(backend.self_test(ROOT/'android/app/src/main/python/engine',tmp),'Embedded export verified')
