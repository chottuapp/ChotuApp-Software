import importlib.util,sys,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('local_check',ROOT/'catalog-tools/check_khaadi_local_adapter_windows.py');helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
class LocalCheckTests(unittest.TestCase):
 def test_curl_keeps_tls_validation_and_reads_status_and_final_url(self):
  def execute(args,**kwargs):
   self.assertIn('--proto-redir',args);self.assertNotIn('-k',args);self.assertNotIn('--insecure',args)
   Path(args[args.index('--output')+1]).write_bytes(b'PKR product')
   return SimpleNamespace(returncode=0,stdout='200\nhttps://pk.khaadi.com/product.html',stderr='')
  with patch.object(helper.subprocess,'run',side_effect=execute):r=helper.CurlSession().get('https://pk.khaadi.com/product.html')
  self.assertEqual(r.status_code,200);self.assertEqual(r.text,'PKR product');self.assertEqual(r.url,'https://pk.khaadi.com/product.html')
 def test_curl_connection_failure_not_reported_as_product_success(self):
  with patch.object(helper.subprocess,'run',return_value=SimpleNamespace(returncode=60,stderr='Certificate verification failed',stdout='')):
   with self.assertRaisesRegex(RuntimeError,'Certificate'):helper.CurlSession().get('https://pk.khaadi.com/product.html')
 def test_foreign_redirect_is_recorded_without_success(self):
  sys.path.insert(0,str(ROOT));import khaadi_source_support as source
  class Session:
   def get(self,url,**kwargs):return SimpleNamespace(status_code=200,url='https://us.khaadi.com/',content=b'foreign',text='foreign')
   get_fresh=get
  with tempfile.TemporaryDirectory() as tmp:
   out=Path(tmp)/'report.json'
   with patch.object(helper,'print',create=True):result=helper.run_check(source,Session(),out)
   self.assertEqual(result,2);self.assertIn('foreign host',out.read_text());self.assertIn('"sample_verified": false',out.read_text())
