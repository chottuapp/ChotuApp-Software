import sys,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'cloud'))
import download_checkpoint as module
class DownloadTests(unittest.TestCase):
 def test_egress_503_retries_in_clean_staging_and_never_logs_signed_url(self):
  calls=[];clock=[0.0]
  def run(args,**kwargs):
   calls.append(args);folder=Path(args[args.index('--dir')+1]);(folder/'partial').write_text('partial')
   if len(calls)==1:return SimpleNamespace(returncode=1,stdout='',stderr='HTTP 503: Egress is over the account limit. https://storage.example/artifact?sig=private')
   (folder/'partial').unlink();(folder/'checkpoint.zip').write_bytes(b'verified downstream');return SimpleNamespace(returncode=0,stdout='',stderr='')
  with tempfile.TemporaryDirectory() as tmp,patch.object(module.subprocess,'run',side_effect=run),patch.object(module.time,'monotonic',side_effect=lambda:clock[0]),patch.object(module.time,'sleep',side_effect=lambda delay:clock.__setitem__(0,clock[0]+delay)),patch('builtins.print') as output:
   target=Path(tmp)/'restore';module.download('123','owner/repo',target)
   self.assertEqual((target/'checkpoint.zip').read_bytes(),b'verified downstream');self.assertFalse((target/'partial').exists());self.assertEqual(len(calls),2);self.assertNotIn('private',str(output.call_args_list))
 def test_missing_artifact_does_not_loop_or_replace_existing_data(self):
  with tempfile.TemporaryDirectory() as tmp,patch.object(module.subprocess,'run',return_value=SimpleNamespace(returncode=1,stdout='',stderr='No artifact found')) as run:
   target=Path(tmp)/'restore'
   with self.assertRaisesRegex(RuntimeError,'without a retryable'):module.download('123','owner/repo',target)
   self.assertEqual(run.call_count,1);self.assertFalse(target.exists())
   target.mkdir();(target/'important').write_text('keep')
   with self.assertRaisesRegex(ValueError,'not empty'):module.download('123','owner/repo',target)
   self.assertEqual((target/'important').read_text(),'keep')
 def test_storage_retry_budget_is_bounded(self):
  with tempfile.TemporaryDirectory() as tmp,patch.object(module.subprocess,'run',return_value=SimpleNamespace(returncode=1,stdout='',stderr='HTTP 503')) as run:
   with self.assertRaisesRegex(RuntimeError,'retry budget'):module.download('123','owner/repo',Path(tmp)/'restore',attempts=1)
   self.assertEqual(run.call_count,1)
