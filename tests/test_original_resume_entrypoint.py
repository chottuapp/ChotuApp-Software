import importlib.util,json,os,sys,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock,patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'cloud'))
spec=importlib.util.spec_from_file_location('original_resume',ROOT/'cloud/resume_originals_release.py');controller=importlib.util.module_from_spec(spec);spec.loader.exec_module(controller)
import laam_source_support as laam
class OriginalResumeTests(unittest.TestCase):
 def test_laam_source_validation_checkpoint_dispatch_and_live_snapshot(self):
  calls=[];listed=[0];source=Mock();source.read.side_effect=[SimpleNamespace(text='User-agent: *'),SimpleNamespace(text='<script></script>')]
  site={'name':'LAAM','parent':'39410937297','group':'solo-laam','url':'https://laam.com'}
  original_read=Path.read_text
  def read(path,*args,**kwargs):
   if path.name=='originals-resume-release.json':return json.dumps({'sources':[site]})
   return original_read(path,*args,**kwargs)
  def gh(*args):
   calls.append(args)
   if args[:2]==('run','list'):
    listed[0]+=1
    return '[]' if listed[0]==1 else json.dumps([{'databaseId':999,'displayTitle':'Cloud group solo-laam','status':'in_progress'}])
   if args[0]=='api':return json.dumps({'artifacts':[{'name':'chotuapp-checkpoint'}]})
   return ''
  def execute(args,**kwargs):
   folder=Path(args[args.index('--dir')+1]);(folder/'store-status.txt').write_text('LAAM: running\npublic product pages: 1000/183187')
   return SimpleNamespace(returncode=0,stdout='',stderr='')
  with patch.dict(os.environ,{'GITHUB_RUN_ID':'77'}),patch.object(Path,'read_text',read),patch.object(controller,'gh',side_effect=gh),patch.object(controller,'publish') as publish,patch.object(controller.subprocess,'run',side_effect=execute),patch.object(laam,'PublicCatalog',return_value=source),patch.object(laam,'product_state',side_effect=laam.ConfirmedOutOfStock('Confirmed')),patch('builtins.print'):
   controller.main()
  record=publish.call_args.args[0]['sources'][0];self.assertEqual(record['run_id'],'999');self.assertIn('1000/183187',record['snapshot'])
  dispatch=[c for c in calls if c[:2]==('workflow','run')];self.assertEqual(len(dispatch),1);self.assertIn('resume_run_id=39410937297',dispatch[0]);self.assertFalse(any('cloud-stop.yml' in c for c in calls))
