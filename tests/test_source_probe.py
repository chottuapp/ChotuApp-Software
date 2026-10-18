import sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch,Mock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'cloud'))
import source_probe as p
class SourceProbeTests(unittest.TestCase):
 def test_summary_excludes_state_values_and_url_secrets(self):
  html='<script id="__NEXT_DATA__">{"props":{"pageProps":{"token":"secret"}}}</script><script src="/app.js?key=secret"></script><link rel="canonical" href="/?token=secret">'
  data=p.inspect_page(html,'https://laam.com/');self.assertNotIn('secret',str(data));self.assertEqual(data['next_page_prop_keys'],['token'])
 def test_redirect_cannot_escape_com_pk_host(self):
  with self.assertRaises(ValueError):p.request(Mock(),'https://another.com.pk/','outfitters.com.pk',100)
 def test_rate_limit_stops_probe_without_retry(self):
  with tempfile.TemporaryDirectory() as tmp,patch.object(p,'request',return_value=(429,'https://zellbury.com/robots.txt',b'limited','text/plain')) as request:
   report=p.capture('zellbury.com',tmp,session=Mock(),wait=lambda _:None);self.assertEqual(request.call_count,1);self.assertEqual(report['responses'][0]['status'],429)
 def test_robots_blocks_catalog(self):
  def request(session,url,host,limit):return (200,url,b'User-agent: *\nDisallow: /products.json\n' if url.endswith('robots.txt') else b'<html></html>','text/plain')
  with tempfile.TemporaryDirectory() as tmp,patch.object(p,'request',side_effect=request) as call:
   report=p.capture('laam.com',tmp,session=Mock(),wait=lambda _:None);self.assertEqual(call.call_count,2);self.assertEqual(report['responses'][-1]['outcome'],'robots_disallowed')
if __name__=='__main__':unittest.main()
