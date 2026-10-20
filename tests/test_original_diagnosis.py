import json,os,runpy,sys,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock,patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'cloud'))
import source_research,laam_source_support
class DiagnosisTests(unittest.TestCase):
 def test_cloud_entrypoint_publishes_source_state_and_keeps_early_failure(self):
  handle='1864-paradise-blue-embroidered-organza-stitched-0';catalog=Mock();catalog.read.side_effect=[SimpleNamespace(text='User-agent: *'),SimpleNamespace(text='<script id="__NUXT_DATA__">[]</script>')]
  def command(args,**kwargs):
   out=json.dumps({'status':'completed','conclusion':'failure','jobs':[],'headSha':'a'*40}) if '--json' in args else 'HTTP START failing product\nEXCEPTION: RuntimeError example\n'+'upload artifact\n'*200
   return SimpleNamespace(returncode=0,stdout=out,stderr='')
  with patch.dict(os.environ,{'GITHUB_RUN_ID':'123'}),patch('subprocess.run',side_effect=command),patch.object(source_research,'publish') as publish,patch.object(source_research,'public_product_state',return_value=[{'handle':handle,'variants':[]}]),patch.object(laam_source_support,'PublicCatalog',return_value=catalog),patch('builtins.print'):
   runpy.run_path(str(ROOT/'cloud/original_three_diagnosis.py'),run_name='__main__')
  report=publish.call_args.args[0];self.assertEqual(len(report['failures']),2);self.assertEqual(report['laam_failing_product'][0]['handle'],handle);self.assertTrue(any('EXCEPTION' in line for line in report['failures'][0]['failed_log_tail']))
