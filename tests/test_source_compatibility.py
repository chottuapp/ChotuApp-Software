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
 def test_other_verified_sources_are_unchanged(self):
  g,calls=self.engine(None);self.assertEqual(g['discover']('https://zellbury.com',lambda _:None),('original','https://zellbury.com'));self.assertEqual(calls,[])
if __name__=='__main__':unittest.main()
