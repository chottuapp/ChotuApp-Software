import hashlib,importlib.util,tempfile,unittest,datetime
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('fresh_windows',ROOT/'catalog-tools/start_fresh26_rule804_drive_windows.py');helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
class FreshWindowsTests(unittest.TestCase):
 def test_checked_artifacts_allow_only_expected_identity_and_bytes(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);file=root/'Miss Rose.xlsx';file.write_bytes(b'verified');record={'store':'Miss Rose','name':file.name,'sha256':hashlib.sha256(file.read_bytes()).hexdigest(),'rule804':'automated evidence-bound pass','pipeline_revision':'a'*64,'source_sha256':'b'*64}
   self.assertEqual(len(helper.checked_files(root,{'files':[record]})),1)
   for change in ({'rule804':''},{'pipeline_revision':'bad'},{'name':'../Miss Rose.xlsx'},{'store':'LAAM','name':'LAAM.xlsx'},{'sha256':'0'*64}):
    with self.assertRaises(ValueError):helper.checked_files(root,{'files':[dict(record,**change)]})
 def test_daily_folder_uses_pakistan_midnight(self):
  utc=datetime.timezone.utc
  self.assertEqual(helper.daily_folder(datetime.datetime(2026,10,20,18,59,tzinfo=utc)),'ChotuApp 20-10-2026 Fresh')
  self.assertEqual(helper.daily_folder(datetime.datetime(2026,10,20,19,0,tzinfo=utc)),'ChotuApp 21-10-2026 Fresh')
 def test_rollover_retains_previous_uploads_and_rechecks_new_day(self):
  state={'dispatcher':'123','uploaded':{'Adam Cheese':'hash'},'seen_artifacts':{'1':7}}
  helper.activate_day(state,helper.LEGACY_FOLDER)
  self.assertEqual(state['uploaded'],{'Adam Cheese':'hash'})
  helper.activate_day(state,'ChotuApp 21-10-2026 Fresh')
  self.assertEqual(state['uploaded'],{});self.assertEqual(state['seen_artifacts'],{})
  self.assertEqual(state['daily_uploads'][helper.LEGACY_FOLDER],{'Adam Cheese':'hash'})
  state['uploaded']['Miss Rose']='newhash'
  helper.activate_day(state,'ChotuApp 21-10-2026 Fresh')
  self.assertEqual(state['uploaded'],{'Miss Rose':'newhash'});self.assertEqual(state['dispatcher'],'123')
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
