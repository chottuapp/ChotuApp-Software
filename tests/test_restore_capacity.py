import contextlib,io,json,sys,tempfile,unittest,zipfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'cloud'))
from cli import restore_capacity,restore,MAX_RESTORE_BYTES,RESTORE_RESERVE_BYTES
GiB=1024**3
class RestoreCapacityTests(unittest.TestCase):
 def check(self,size,free):
  entries=[SimpleNamespace(file_size=size)]
  with patch('shutil.disk_usage',return_value=SimpleNamespace(free=free)),contextlib.redirect_stdout(io.StringIO()):return restore_capacity(entries,'.')
 def test_legitimate_cache_over_old_eight_gib_limit_can_restore(self):self.assertEqual(self.check(9*GiB,12*GiB),9*GiB)
 def test_disk_budget_reserves_working_space(self):
  with self.assertRaisesRegex(ValueError,'Insufficient disk space'):self.check(9*GiB,9*GiB+RESTORE_RESERVE_BYTES-1)
 def test_finite_expansion_cap_remains(self):
  with self.assertRaisesRegex(ValueError,'safety limit'):self.check(MAX_RESTORE_BYTES+1,100*GiB)
 def test_low_disk_failure_happens_before_any_checkpoint_entry_is_written(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);archive=root/'checkpoint.zip';data=root/'data'
   with zipfile.ZipFile(archive,'w') as z:z.writestr('template.xlsx',b'original template');z.writestr('saved_runs/response.txt',b'durable')
   with patch('shutil.disk_usage',return_value=SimpleNamespace(free=0)),contextlib.redirect_stdout(io.StringIO()):
    with self.assertRaisesRegex(ValueError,'Insufficient disk space'):restore(archive,data)
   self.assertFalse((data/'template.xlsx').exists());self.assertFalse((data/'saved_runs/response.txt').exists());self.assertTrue(archive.is_file())
 def test_valid_archive_restores_content_exactly_and_keeps_archive(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);archive=root/'checkpoint.zip';data=root/'data';payload=b'successful saved response'
   with zipfile.ZipFile(archive,'w') as z:z.writestr('saved_runs/cache.bin',payload)
   before=archive.read_bytes()
   with patch('shutil.disk_usage',return_value=SimpleNamespace(free=20*GiB)),contextlib.redirect_stdout(io.StringIO()):restore(archive,data)
   self.assertEqual((data/'saved_runs/cache.bin').read_bytes(),payload);self.assertEqual(archive.read_bytes(),before)
 def test_duplicate_entries_are_rejected_before_extraction(self):
  import warnings
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);archive=root/'checkpoint.zip';data=root/'data'
   with warnings.catch_warnings():
    warnings.simplefilter('ignore')
    with zipfile.ZipFile(archive,'w') as z:z.writestr('template.xlsx',b'one');z.writestr('template.xlsx',b'two')
   with contextlib.redirect_stdout(io.StringIO()):
    with self.assertRaisesRegex(ValueError,'Duplicate'):restore(archive,data)
   self.assertFalse((data/'template.xlsx').exists())
if __name__=='__main__':unittest.main()

class PreparedResumeTests(unittest.TestCase):
 def test_restore_marker_is_bound_to_source_and_saved_queue(self):
  from prepare_resume import prepare,prepared
  from resume_support import RunStore
  import threading
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);data=root/'data';template=root/'template.xlsx';template.write_bytes(b'template')
   from cli import checkpoint
   store=RunStore(root/'source/saved_runs');state=store.fresh([{'name':'Czone','url':'https://www.czone.com.pk'},{'name':'Outfitters','url':'https://outfitters.com.pk'}],template)
   output=root/'source/ANAS_DATA_FETCH/Czone.xlsx';output.parent.mkdir();output.write_bytes(b'completed export');stat=output.stat()
   store.update(lambda s:s['sites'][0].update(status='done',output={'path':str(output),'size':stat.st_size,'mtime_ns':stat.st_mtime_ns}))
   with contextlib.redirect_stdout(io.StringIO()):checkpoint(root/'source',root/'checkpoint.zip');needs=prepare(root/'checkpoint.zip',data,'123')
   self.assertFalse(needs);self.assertTrue(prepared(data,'123'));self.assertFalse(prepared(data,'124'))
   RunStore(data/'saved_runs').update(lambda s:s.update(id='different-state'))
   self.assertFalse(prepared(data,'123'))
 def test_pending_czone_still_gets_browser(self):
  from prepare_resume import prepare
  from resume_support import RunStore
  from cli import checkpoint
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);template=root/'template.xlsx';template.write_bytes(b'template');store=RunStore(root/'source/saved_runs');store.fresh([{'name':'Czone','url':'https://www.czone.com.pk'}],template);store.update(lambda s:s['sites'][0].update(status='done',output={'path':'missing.xlsx','size':1,'mtime_ns':1}))
   with contextlib.redirect_stdout(io.StringIO()):checkpoint(root/'source',root/'checkpoint.zip');self.assertTrue(prepare(root/'checkpoint.zip',root/'restored','123'))

class SupervisorResumeTests(unittest.TestCase):
 def test_prepared_checkpoint_is_not_extracted_twice(self):
  import os
  from background_run import supervise
  from unittest.mock import Mock
  for ready in (True,False):
   with tempfile.TemporaryDirectory() as tmp:
    process=Mock();process.poll.return_value=0;process.returncode=0
    with patch.dict(os.environ,{'CLOUD_MINUTES':'300','RESUME_RUN_ID':'123','RUNNER_TEMP':tmp,'SAVE_CHECKPOINT':'true'}),patch('prepare_resume.prepared',return_value=ready),patch('background_run.subprocess.Popen',return_value=process) as launch:
     self.assertEqual(supervise(tmp),0)
    args=launch.call_args.args[0];self.assertIn('--continue-saved',args);self.assertEqual('--restore' in args,not ready)
