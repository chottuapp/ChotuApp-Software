import contextlib,io,json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'cloud'));sys.path.insert(0,str(ROOT))
from background_run import finish
from cli import checkpoint,restore
from resume_support import RunStore
from openpyxl import Workbook
class FinalizationTests(unittest.TestCase):
 def test_packing_can_run_past_old_thirty_second_timeout(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);(root/'fetch-phase.json').write_text('{"phase":"checkpoint"}');clock=[0]
   def sleep(seconds):
    clock[0]+=seconds
    if clock[0]>=45:(root/'background-result.json').write_text('{"exit_code":2}')
   with patch('background_run.time.monotonic',side_effect=lambda:clock[0]),patch('background_run.time.sleep',side_effect=sleep),contextlib.redirect_stdout(io.StringIO()):code=finish(root,timeout=900,poll=5)
   self.assertEqual(code,2);self.assertGreaterEqual(clock[0],45);self.assertFalse((root/'stop-request').exists())
 def test_timeout_reports_explicit_failure(self):
  with tempfile.TemporaryDirectory() as tmp,contextlib.redirect_stdout(io.StringIO()) as out:
   self.assertEqual(finish(Path(tmp),timeout=0),2);self.assertIn('FINALIZATION TIMEOUT',out.getvalue())
 def test_completed_caches_omitted_but_pending_and_exports_preserved(self):
  import zipfile
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);data=root/'data';store=RunStore(data/'saved_runs');template=root/'template.xlsx';Workbook().save(template)
   state=store.fresh([{'name':'Done','url':'https://done.example'},{'name':'Pending','url':'https://pending.example'}],template)
   output=data/'ANAS_DATA_FETCH';output.mkdir();file=output/'Done.xlsx';Workbook().save(file);stat=file.stat()
   store.update(lambda s:s['sites'][0].update(status='done',output={'path':str(file),'size':stat.st_size,'mtime_ns':stat.st_mtime_ns}))
   for index in ('0','1'):
    folder=store.root/state['id']/index;folder.mkdir();(folder/'api.sqlite3').write_bytes(b'cache')
   archive=root/'checkpoint.zip';checkpoint(data,archive)
   with zipfile.ZipFile(archive) as z:
    self.assertNotIn('saved_runs/'+state['id']+'/0/api.sqlite3',z.namelist());self.assertIn('saved_runs/'+state['id']+'/1/api.sqlite3',z.namelist());self.assertIn('ANAS_DATA_FETCH/Done.xlsx',z.namelist())
   restored=root/'restored';restore(archive,restored);self.assertEqual((restored/'saved_runs'/state['id']/'1'/'api.sqlite3').read_bytes(),b'cache')
if __name__=='__main__':unittest.main()
