import copy,json,tempfile,unittest
from pathlib import Path
from alfateh_source_support import normalize,IncompleteProduct,BASE
URL=BASE+'/product/controlled-shirt'
def page(variants=None,offer=None):
 variants=copy.deepcopy(variants if variants is not None else [dict(id='v1',sku='sku1',regularPrice='2000',salePrice=None,size={'value':'M'},color={'name':'Cream'},isActive=True,availableStock=3),dict(id='v2',sku='sku2',regularPrice='2500',salePrice='2100',size={'value':'L'},color={'name':'Black'},isActive=True,availableStock=0)])
 raw={'@type':'Product','name':'Controlled Cotton Shirt','description':'Cotton shirt with exact source specifications and care.','sku':'sku1','image':[BASE+'/uploads/one.jpg'],'brand':{'name':'Controlled Brand'},'offers':offer or {'url':URL,'priceCurrency':'PKR','price':'2000','availability':'https://schema.org/InStock'}}
 stream='1:'+json.dumps(['$','Provider',None,{'variants':variants,'children':'Published product details'}])+'\n'
 return '<main><h1>Controlled Cotton Shirt</h1><div class="mt-8 space-y-4"><p>Cotton shirt with exact source specifications and care.</p><dl><dt>Care</dt><dd>Wash at 30 degrees.</dd></dl></div></main><script type="application/ld+json">'+json.dumps(raw)+'</script><script>self.__next_f.push('+json.dumps([1,stream])+')</script>'
class AlfatehTests(unittest.TestCase):
 def test_exact_pkr_prices_stock_sizes_colors_and_source_details_preserved(self):
  p=normalize(page(),URL)
  self.assertEqual([v['price'] for v in p['variants']],['2000','2100']);self.assertEqual(p['variants'][1]['compare_at_price'],'2500')
  self.assertEqual([v['available'] for v in p['variants']],[True,False]);self.assertEqual([v['inventory_quantity'] for v in p['variants']],[3,0])
  self.assertEqual([(v['option1'],v['option2']) for v in p['variants']],[('M','Cream'),('L','Black')]);self.assertIn('30 degrees',p['body_html'])
 def test_unpublished_stock_is_incomplete_never_invented(self):
  variants=[dict(id='v1',sku='sku1',regularPrice='2000',salePrice=None,size={'value':'M'},color={'name':'Cream'},isActive=True)]
  with self.assertRaises(IncompleteProduct):normalize(page(variants),URL)
 def test_foreign_offer_price_or_stock_conflict_still_fails(self):
  for change in ({'url':'https://foreign.test/product/controlled-shirt'},{'priceCurrency':'USD'},{'price':'1'},{'availability':'https://schema.org/OutOfStock'}):
   offer=dict(url=URL,priceCurrency='PKR',price='2000',availability='https://schema.org/InStock');offer.update(change)
   with self.assertRaises(ValueError):normalize(page(offer=offer),URL)
 def test_duplicate_variant_or_bad_price_is_rejected(self):
  variants=[dict(id='v1',sku='sku1',regularPrice='2000',salePrice='2100',size={'value':'M'},color={'name':'Cream'},isActive=True,availableStock=3)]
  with self.assertRaises(ValueError):normalize(page(variants),URL)
 def test_runtime_ships_and_enables_adapter(self):
  from runtime import prepare_engine
  with tempfile.TemporaryDirectory() as tmp:
   engine=prepare_engine(Path(tmp));self.assertTrue((engine.parent/'alfateh_source_support.py').is_file());self.assertTrue((engine.parent/'next_public_support.py').is_file());self.assertIn('enable_alfateh_source(globals())',engine.read_text())
