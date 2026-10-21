import importlib.util,unittest,tempfile,json,hashlib,os,subprocess
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('cloud_drive_sync',ROOT/'cloud/drive_sync.py');sync=importlib.util.module_from_spec(spec);spec.loader.exec_module(sync)
CONFIG='[chotudrive]\ntype = drive\ntoken = {"refresh_token":"test-value"}\n'
class DriveSyncTests(unittest.TestCase):
 def test_config_rejects_other_remotes(self):
  self.assertEqual(sync.config_text(CONFIG),CONFIG)
  with self.assertRaises(ValueError):sync.config_text(CONFIG+'\n[private]\ntype=drive\n')
 def exercise(self,fail=False):
  record={'name':'Miss Rose.xlsx','store':'Miss Rose','sha256':hashlib.sha256(b'checked').hexdigest(),'source_sha256':'a'*64,'pipeline_revision':'b'*64,'rule804':'automated pass'}
  def gh(*args):
   if args[0]=='api' and 'contents/latest' in args[1]:raise RuntimeError('No prior state')
   if args[:2]==('run','list'):return json.dumps([{'databaseId':123,'displayTitle':'Cloud group fresh26-39450710625-1','status':'in_progress'}])
   if args[0]=='api':return json.dumps({'artifacts':[{'name':'chotuapp-rule804-files','id':9}]})
   if args[:2]==('run','download'):
    root=Path(args[-1]);(root/record['name']).write_bytes(b'checked');(root/'manifest.json').write_text(json.dumps({'files':[record]}));return ''
   raise AssertionError(args)
  def command(args,**kw):
   if args[0]!='rclone':raise AssertionError(args)
   self.assertIn('chotudrive:ChotuApp 19-10-2026 11-36AM',args)
   config=Path(args[2]);self.assertEqual(config.read_text(),CONFIG)
   if fail and 'check' in args:return SimpleNamespace(returncode=1)
   return SimpleNamespace(returncode=0)
  with patch.object(sync,'load_config',return_value={**json.loads((ROOT/'cloud/drive-sync-release.json').read_text()),'audit804_enabled':False,'dispatcher':'39450710625'}),patch('original_store_ingest.upload',return_value=[]),patch.object(sync,'gh',side_effect=gh),patch.object(sync,'publish') as publish,patch('subprocess.run',side_effect=command),patch.dict(os.environ,{'CHOTU_DRIVE_RCLONE_CONFIG':CONFIG,'GITHUB_RUN_ID':'777'}),patch('builtins.print'):
   if fail:
    with self.assertRaises(RuntimeError):sync.main()
    for saved in publish.call_args_list:self.assertFalse(saved.args[0]['uploaded']);self.assertFalse(saved.args[0]['processed_artifacts'])
   else:
    sync.main();report=publish.call_args.args[0]
    self.assertEqual(report['uploaded']['Miss Rose']['sha256'],record['sha256']);self.assertEqual(report['processed_artifacts']['123'],9)
    self.assertNotIn('refresh_token',json.dumps(report));self.assertIn('verified_utc',report['uploaded']['Miss Rose'])
 def test_upload_is_marked_only_after_checksum_verification(self):self.exercise()
 def test_failed_checksum_never_marks_upload_verified(self):self.exercise(True)
 def test_missing_secret_never_calls_drive(self):
  with patch.dict(os.environ,{},clear=True),patch.object(sync,'gh') as gh:
   with self.assertRaises(RuntimeError):sync.main()
   gh.assert_not_called()
