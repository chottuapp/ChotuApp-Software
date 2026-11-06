import copy,json,unittest
from pathlib import Path
from laam_source_support import normalize,HiddenProduct,ConfirmedOutOfStock
class OwnerFilterTests(unittest.TestCase):
 def fixture(self):return json.loads((Path(__file__).parent/'fixtures/laam_public_product_0085.json').read_text())
 def test_only_instock_source_variants_retained(self):
  raw=self.fixture();p=normalize(raw,raw['handle'],active_only=True,in_stock_only=True);self.assertEqual(len(p['variants']),1);self.assertTrue(all(v['available'] for v in p['variants']))
  selected=[v for v in raw['variants'] if v['stock_status'] in ('in-stock','limited-stock')];self.assertEqual(p['variants'][0]['price'],selected[0]['price'])
 def test_hidden_draft_archived_excluded(self):
  for changes in ({'status':'draft'},{'status':'archived'},{'hidden':True},{'is_visible':False},{'published':False},{'visibility':'unlisted'},{'visibility':'private'}):
   raw=self.fixture();raw.update(changes)
   with self.assertRaises(HiddenProduct):normalize(raw,raw['handle'],active_only=True,in_stock_only=True)
 def test_all_outofstock_excluded(self):
  raw=self.fixture()
  for v in raw['variants']:v['stock_status']='sold-out';v['inventory_quantity']=0
  with self.assertRaises(ConfirmedOutOfStock):normalize(raw,raw['handle'],active_only=True,in_stock_only=True)

class PriceRangeTests(unittest.TestCase):
 def test_owner_reenabled_only_laam(self):
  from locked_store_rules import owner_paused
  self.assertFalse(owner_paused('LAAM','https://laam.com'))
  for name in ('Khaadi','Bachaa Party','Axis PK','Gift4U'):self.assertTrue(owner_paused(name))
 def test_inclusive_available_selling_price_range_and_variant_preservation(self):
  from laam_source_support import owner_price_allowed
  for price,expected in [('1999.99',False),('2000',True),('7000',True),('7000.01',False)]:
   product={'variants':[{'price':price,'available':True},{'price':'1','available':False}]}
   before=copy.deepcopy(product)
   self.assertEqual(owner_price_allowed(product),expected);self.assertEqual(product,before)
  self.assertFalse(owner_price_allowed({'variants':[]}))
 def test_cheapest_available_variant_defines_product_price(self):
  from laam_source_support import owner_price_allowed
  self.assertFalse(owner_price_allowed({'variants':[{'price':'1900','available':True},{'price':'3000','available':True}]}))

 def test_catalog_applies_price_scope_after_source_parsing(self):
  import requests
  from unittest.mock import patch
  from laam_source_support import PublicCatalog,BASE
  from test_laam_source import html,FIXTURES
  raw=copy.deepcopy(FIXTURES[0]['product'])
  for v in raw['variants']:v['price']='2500'
  class Catalog(PublicCatalog):
   def read(self,url,allow_missing=False):
    body={BASE+'/robots.txt':'User-agent: *\nAllow: /\nSitemap: '+BASE+'/sitemap.xml',BASE+'/sitemap.xml':'<urlset><url><loc>'+BASE+'/products/'+raw['handle']+'</loc></url></urlset>',BASE+'/products/'+raw['handle']:html(raw)}[url]
    r=requests.Response();r.status_code=200;r._content=body.encode();r.encoding='utf-8';return r
  products,complete=Catalog({},lambda _:None).catalog()
  self.assertTrue(complete);self.assertEqual(len(products),1)
  for v in raw['variants']:v['price']='7500'
  products,complete=Catalog({},lambda _:None).catalog()
  self.assertTrue(complete);self.assertEqual(products,[])
