import copy,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import laam_source_support as source
from test_laam_source import FIXTURES,html

class LaamIncompleteListingTests(unittest.TestCase):
 def test_active_empty_variants_are_incomplete_not_available_or_sold_out(self):
  raw=copy.deepcopy(FIXTURES[0]['product']);raw.update(id=518174,handle='3p-br3981',title='3P #BR3981',options=[],variants=[],status='ACTIVE',stock_status='limited-stock');before=copy.deepcopy(raw)
  with self.assertRaises(source.IncompleteListing) as caught:source.normalize(raw,raw['handle'],active_only=True,in_stock_only=True)
  self.assertEqual(caught.exception.raw,before);self.assertEqual(raw,before)
 def test_incomplete_listing_receipt_is_saved_and_other_products_continue(self):
  bad=copy.deepcopy(FIXTURES[0]['product']);bad.update(id=518174,handle='000-incomplete',options=[],variants=[],status='ACTIVE',stock_status='limited-stock');good=copy.deepcopy(FIXTURES[1]['product'])
  urls=[source.BASE+'/products/'+bad['handle'],source.BASE+'/products/'+good['handle']]
  sitemap='<urlset>'+''.join('<url><loc>'+url+'</loc></url>' for url in urls)+'</urlset>'
  class Reader(source.PublicCatalog):
   def read(self,url,**kwargs):
    text='User-agent: *\nSitemap: '+source.BASE+'/sitemap.xml' if url.endswith('robots.txt') else sitemap if url.endswith('.xml') else html(bad if url==urls[0] else good)
    return SimpleNamespace(text=text,content=text.encode(),status_code=200)
  with tempfile.TemporaryDirectory() as tmp,patch('locked_store_rules.record_incomplete_product') as receipt,patch.object(source,'owner_price_allowed',return_value=True):
   tls=SimpleNamespace(saved_api_path=Path(tmp)/'api.sqlite3');reader=Reader({'_chotu_tls':tls},lambda _:None)
   try:
    products,complete=reader.catalog();self.assertTrue(complete);self.assertEqual([p['id'] for p in products],[good['id']]);receipt.assert_called_once()
    original=receipt.call_args.args[0];self.assertEqual(original['variants'],[]);self.assertEqual(original['id'],bad['id'])
    cached=reader.cache.get(urls[0]);self.assertEqual(cached['_excluded_reason'],'incomplete-source-listing');self.assertEqual(cached['_original_source_product']['variants'],[])
   finally:reader.close()
 def test_price_and_option_conflicts_remain_errors(self):
  raw=copy.deepcopy(FIXTURES[0]['product']);raw['variants'][0]['price']='not-a-price'
  with self.assertRaises(ValueError) as caught:source.normalize(raw,raw['handle'])
  self.assertNotIsInstance(caught.exception,source.IncompleteListing)
