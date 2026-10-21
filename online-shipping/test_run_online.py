import importlib.util,json,os,subprocess,tempfile,unittest
from pathlib import Path
spec=importlib.util.spec_from_file_location('run_online',Path(__file__).with_name('run_online.py'));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class SnapshotTests(unittest.TestCase):
 def test_live_snapshot_excludes_excel_until_final_and_keeps_source(self):
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp);source=root/'repo';remote=root/'remote.git';source.mkdir()
   def g(*args):return subprocess.run(['git',*args],cwd=source,check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True).stdout
   subprocess.run(['git','init','--bare',str(remote)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
   g('init');g('config','user.name','Test');g('config','user.email','test@example.invalid');(source/'source.txt').write_text('preserve');g('add','source.txt');g('commit','-m','source');g('remote','add','origin',str(remote));g('switch','-c','shipping-results-1-1')
   output=source/'shipping-output';output.mkdir();(output/'progress.json').write_text('{"products":1}');(output/'Products_Delivery_Audit.xlsx').write_bytes(b'xlsx')
   prior=Path.cwd()
   try:
    os.chdir(source);m.snapshot(Path('shipping-output'));listed=g('ls-tree','-r','--name-only','HEAD');self.assertIn('progress.json',listed);self.assertNotIn('.xlsx',listed)
    m.snapshot(Path('shipping-output'),final=True);self.assertIn('.xlsx',g('ls-tree','-r','--name-only','HEAD'));self.assertEqual((source/'source.txt').read_text(),'preserve')
   finally:os.chdir(prior)
if __name__=='__main__':unittest.main()
