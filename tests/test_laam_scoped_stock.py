import copy,json,unittest
from pathlib import Path
from bs4 import BeautifulSoup
import laam_source_support as source
from test_laam_source import html

class ScopedStockTests(unittest.TestCase):
 def setUp(self):
  self.raw=json.loads((Path(__file__).parent/'fixtures/laam_chambeli_empty_variants.json').read_text())
 def parse(self,availability='OutOfStock',url=None,currency='PKR',duplicate=None):
  soup=BeautifulSoup(html(self.raw),'html.parser');script=soup.select_one('script[type="application/ld+json"]')
  offer={'@type':'Product','url':url or source.BASE+'/products/'+self.raw['handle'],'offers':{'priceCurrency':currency,'price':599000,'availability':'https://schema.org/'+availability}}
  script.string=json.dumps([offer,duplicate] if duplicate else offer)
  return source.product_state(soup,self.raw['handle'])
 def test_current_pkr_offer_and_zero_local_inventory_confirm_unavailability(self):
  before=copy.deepcopy(self.raw)
  with self.assertRaises(source.ConfirmedOutOfStock):self.parse()
  self.assertEqual(self.raw,before)
 def test_positive_other_store_quantity_without_matched_offer_still_blocks(self):
  with self.assertRaisesRegex(ValueError,'Conflicting LAAM'):source.normalize(self.raw,self.raw['handle'])
  for kwargs in ({'availability':'InStock'},{'url':source.BASE+'/products/unrelated'}):
   with self.assertRaises(ValueError) as caught:self.parse(**kwargs)
   self.assertNotIsInstance(caught.exception,source.ConfirmedOutOfStock)
 def test_conflicting_matching_offers_and_foreign_currency_are_not_approved(self):
  other={'@type':'Product','url':source.BASE+'/products/'+self.raw['handle'],'offers':{'priceCurrency':'PKR','availability':'https://schema.org/InStock'}}
  with self.assertRaisesRegex(ValueError,'Conflicting LAAM'):self.parse(duplicate=other)
  with self.assertRaises(source.SourceAccessError):self.parse(currency='USD')
 def test_invalid_store_quantities_stay_blocked_even_with_out_of_stock_offer(self):
  for value in (-1,True,'0'):
   self.raw['total_sellable_inventory_on_store']['68']=value
   with self.assertRaisesRegex(ValueError,'Conflicting LAAM'):self.parse()
 def test_unavailable_product_does_not_abort_other_catalog_products(self):
  import tempfile
  from types import SimpleNamespace
  from unittest.mock import patch
  from test_laam_source import FIXTURES
  bad=self.raw;good=copy.deepcopy(FIXTURES[0]['product']);urls=[source.BASE+'/products/'+v['handle'] for v in (bad,good)]
  soup=BeautifulSoup(html(bad),'html.parser');soup.select_one('script[type="application/ld+json"]').string=json.dumps({'@type':'Product','url':urls[0],'offers':{'priceCurrency':'PKR','availability':'https://schema.org/OutOfStock'}})
  class Reader(source.PublicCatalog):
   def read(self,url,**kwargs):
    text='User-agent: *\nSitemap: '+source.BASE+'/sitemap.xml' if url.endswith('robots.txt') else '<urlset>'+''.join('<url><loc>'+u+'</loc></url>' for u in urls)+'</urlset>' if url.endswith('.xml') else str(soup) if url==urls[0] else html(good)
    return SimpleNamespace(text=text,content=text.encode(),status_code=200)
  with tempfile.TemporaryDirectory() as tmp,patch.object(source,'owner_price_allowed',return_value=True):
   reader=Reader({'_chotu_tls':SimpleNamespace(saved_api_path=Path(tmp)/'api.sqlite3')},lambda _:None)
   try:
    products,complete=reader.catalog();self.assertTrue(complete);self.assertEqual([v['id'] for v in products],[good['id']])
    self.assertEqual(reader.cache.get(urls[0])['_excluded_reason'],'confirmed-out-of-stock')
   finally:reader.close()
