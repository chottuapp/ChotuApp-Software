import unittest
from types import SimpleNamespace
from breakout_source_support import enable_breakout_source,SHOP
class BreakoutTests(unittest.TestCase):
 def engine(self,text):
  calls=[];g={'_chotu_wait':lambda:None,'S':SimpleNamespace(get=lambda *a,**k:SimpleNamespace(status_code=200,url='https://www.breakout.com.pk/',text=text)),'get_json':lambda u:{'products':[{'id':1,'handle':'shirt','variants':[{'id':2,'price':'2500'}]}]},'_chotuapp_run_site_original':lambda *a:calls.append(a)};enable_breakout_source(g);return g,calls
 def test_only_explicitly_advertised_source_passes_to_canonical_engine(self):
  g,calls=self.engine('checkout.breakout.com.pk bktt.myshopify.com');g['_chotuapp_run_site_original']('https://www.breakout.com.pk','Breakout','template',lambda x:None);self.assertEqual(calls[0][:3],(SHOP,'Breakout','template'))
 def test_missing_origin_evidence_does_not_export(self):
  g,calls=self.engine('Unrelated storefront')
  with self.assertRaises(ValueError):g['_chotuapp_run_site_original']('https://www.breakout.com.pk','Breakout','template',lambda x:None)
  self.assertFalse(calls)
