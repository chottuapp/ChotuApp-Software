import copy,json,tempfile,unittest
from pathlib import Path
from mansab_source_support import normalize
F=json.loads((Path(__file__).parent/'fixtures/mansab_public_product.json').read_text())
def page(raw,currency='PKR',price=None):
 p={'@type':'Product','name':raw['name'],'offers':{'url':F['url'],'priceCurrency':currency,'price':price if price is not None else raw['sale_price'] if raw.get('sale_price') is not None else raw['price'],'availability':'https://schema.org/InStock' if raw['stock']>0 else 'https://schema.org/OutOfStock'}}
 return '<script type="application/ld+json">'+json.dumps(p)+'</script>'
class MansabTests(unittest.TestCase):
 def test_real_public_sizes_prices_and_stock_preserved_without_native_id_invention(self):
  raw=copy.deepcopy(F['product']);before=copy.deepcopy(raw);p=normalize(page(raw),F['url'],raw)
  self.assertEqual(raw,before);self.assertEqual([v['option1'] for v in p['variants']],['L','M']);self.assertEqual([v['inventory_quantity'] for v in p['variants']],[1,1]);self.assertEqual([v['price'] for v in p['variants']],['3000','3000']);self.assertEqual([v['compare_at_price'] for v in p['variants']],['4890','4890']);self.assertTrue(all(v['_source_variant_id']=='' and v['sku']=='' for v in p['variants']));self.assertEqual(len({v['id'] for v in p['variants']}),2)
  for value in ('Imported Burberry','Chest 21','Length 30'):self.assertIn(value,p['body_html'])
  import main
  self.assertEqual(main.product_stock_quantity(p,p['variants']),2)
 def test_real_zero_quantity_is_unavailable_not_removed_or_distributed(self):
  raw=copy.deepcopy(F['product']);raw['size_stock']={'L':0,'M':2};p=normalize(page(raw),F['url'],raw)
  self.assertEqual([v['available'] for v in p['variants']],[False,True]);self.assertEqual([v['_public_stock_quantity'] for v in p['variants']],[0,2])
 def test_ambiguous_stock_foreign_prices_or_identity_stay_blocking(self):
  for edit in ('missing_stock','total','negative','unknown_size','slug','price','foreign'):
   raw=copy.deepcopy(F['product'])
   if edit=='missing_stock':raw.pop('size_stock')
   if edit=='total':raw['stock']=99
   if edit=='negative':raw['size_stock']['L']=-1
   if edit=='unknown_size':raw['size_stock']['S']=1
   if edit=='slug':raw['slug']='other'
   with self.subTest(edit=edit),self.assertRaises(ValueError):normalize(page(raw,currency='USD' if edit=='foreign' else 'PKR',price=1 if edit=='price' else None),F['url'],raw)
 def test_runtime_ships_source_and_hook(self):
  from runtime import prepare_engine
  with tempfile.TemporaryDirectory() as tmp:
   engine=prepare_engine(Path(tmp));self.assertIn('enable_mansab_source(globals())',engine.read_text());self.assertTrue((engine.parent/'mansab_source_support.py').exists())
 def test_missing_native_ids_do_not_create_false_duplicate_source_ids(self):
  import main
  raw=copy.deepcopy(F['product']);p=normalize(page(raw),F['url'],raw)
  rows=[dict(product_id='p',name=p['title'],description=raw['description'],**{'base_price (PKR)':4890,'available (yes/no)':'yes'})]
  combos=[dict(combination_id=v['id'],product_id='p',source_variant_id='',**{'base_price (PKR)':4890,'sale_price (PKR, agar discount ho)':3000,'available (yes/no)':'yes'}) for v in p['variants']]
  with tempfile.TemporaryDirectory() as tmp:
   target=Path(tmp)/'audit.csv';main.quality_validation(rows,[],[],[],combos,target,lambda _:None)
   self.assertNotIn('DUPLICATE_VARIANT_ID',target.read_text())
   for c in combos:c['source_variant_id']='actual-native-id'
   main.quality_validation(rows,[],[],[],combos,target,lambda _:None);self.assertIn('DUPLICATE_VARIANT_ID',target.read_text())
