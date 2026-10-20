import hashlib,importlib.util,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('fresh_windows',ROOT/'catalog-tools/start_fresh26_rule804_drive_windows.py');helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
class FreshWindowsTests(unittest.TestCase):
 def test_checked_artifacts_allow_only_expected_identity_and_bytes(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);file=root/'Miss Rose.xlsx';file.write_bytes(b'verified');record={'store':'Miss Rose','name':file.name,'sha256':hashlib.sha256(file.read_bytes()).hexdigest()}
   self.assertEqual(len(helper.checked_files(root,{'files':[record]})),1)
   for change in ({'name':'../Miss Rose.xlsx'},{'store':'LAAM','name':'LAAM.xlsx'},{'sha256':'0'*64}):
    with self.assertRaises(ValueError):helper.checked_files(root,{'files':[dict(record,**change)]})
 def test_runner_tracking_ignores_other_lanes(self):
  runs=[{'databaseId':3,'displayTitle':'Automatic continuation of 2'},{'databaseId':2,'displayTitle':'Cloud group fresh26-1-1'},{'databaseId':1,'displayTitle':'Cloud group solo-laam'}]
  self.assertEqual([r['databaseId'] for r in helper.related(runs,['fresh26-1-1'])],[3,2])
 def test_only_one_drive_helper_can_run_for_batch(self):
  with tempfile.TemporaryDirectory() as tmp:
   path=Path(tmp)/'lock'
   with helper.lease(path):
    with self.assertRaises(OSError):
     with helper.lease(path):pass
   with helper.lease(path):pass
