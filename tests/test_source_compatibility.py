import sys,unittest
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from source_compatibility_support import enable_source_compatibility
class CompatibilityTests(unittest.TestCase):
 def engine(self,response):
  calls=[];g={'_chotu_wait':lambda:None,'S':SimpleNamespace(get=lambda url,**kwargs:(calls.append(url) or response)),'discover':lambda base,log:('original',base)};enable_source_compatibility(g);return g,calls
 def test_khaadi_foreign_redirect_cannot_export_us_prices(self):
  g,calls=self.engine(SimpleNamespace(url='https://us.khaadi.com/',status_code=200,text='US'))
  with self.assertRaisesRegex(RuntimeError,'Pakistan locale/currency unverified'):g['discover']('https://pk.khaadi.com',lambda _:None)
  self.assertEqual(calls,['https://pk.khaadi.com/'])
 def test_sapphire_disallowed_variant_api_is_never_requested(self):
  g,calls=self.engine(SimpleNamespace(url='https://pk.sapphireonline.pk/robots.txt',status_code=200,text='User-agent: *\nDisallow: /on/demandware.store/'))
  with self.assertRaisesRegex(RuntimeError,'robots rules disallow'):g['discover']('https://sapphireonline.pk',lambda _:None)
  self.assertEqual(calls,['https://pk.sapphireonline.pk/robots.txt'])
 def test_preflight_does_not_replay_saved_redirect_or_robots(self):
  from resume_support import SessionProxy
  from unittest.mock import Mock
  for base,response in [('https://pk.khaadi.com',SimpleNamespace(url='https://pk.khaadi.com/',status_code=200,text='Pakistan')),('https://sapphireonline.pk',SimpleNamespace(url='https://pk.sapphireonline.pk/robots.txt',status_code=200,text='User-agent: *\nAllow: /'))]:
   cache=Mock();session=Mock();session.get.return_value=response;pause=Mock()
   proxy=SessionProxy(session,SimpleNamespace(saved_response_cache=cache),pause)
   g={'_chotu_wait':lambda:None,'S':proxy,'discover':lambda *a:None};enable_source_compatibility(g)
   with self.assertRaisesRegex(RuntimeError,'verified Pakistan product/variant adapter|variant response format'):g['discover'](base,lambda _:None)
   session.get.assert_called_once();cache.get.assert_not_called();cache.put.assert_not_called();pause.assert_called_once()
 def test_other_verified_sources_are_unchanged(self):
  g,calls=self.engine(None);self.assertEqual(g['discover']('https://zellbury.com',lambda _:None),('original','https://zellbury.com'));self.assertEqual(calls,[])
if __name__=='__main__':unittest.main()
