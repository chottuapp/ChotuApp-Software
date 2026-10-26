import json,unittest
from pathlib import Path
from test_product_stock_images import main
from locked_store_rules import allowed_product
from subcategory_inference_support import export_values
class MaaliTests(unittest.TestCase):
 def test_actual_source_combinations_and_images(self):
  p=json.loads((Path(__file__).parent/'fixtures/maali_variants.json').read_text())
  self.assertEqual(len(p['variants']),29)
  self.assertEqual({v['option3'] for v in p['variants'] if v['option2']=='GROWPOT'},{'STANDARD'})
  self.assertFalse(any(v['option1']=='SMALL' and v['option2']=='NOVA' for v in p['variants']))
  self.assertTrue(all(main.variant_image_url(p,v)==v['featured_image']['src'] for v in p['variants']))
  selected=next(v for v in p['variants'] if v['id']==48709535039742)
  self.assertEqual([selected['option1'],selected['option2'],selected['option3']],['SMALL','ROXSTAR','LEMON'])
  self.assertEqual(main.shopify_minor_price(selected['price']),1499)
 def test_only_reviewed_optional_giftboxes_excluded_for_this_store(self):
  for h in ['ralli-patchwork','desi-pop','colour-playground','clay-sage']:
   self.assertFalse(allowed_product('https://hellomaali.com',{'handle':h}))
   self.assertTrue(allowed_product('https://other.example',{'handle':h}))
  self.assertTrue(allowed_product('https://hellomaali.com',{'handle':'china-palm'}))
  self.assertTrue(allowed_product('https://hellomaali.com',{'handle':'mini-cactus-trio-bundle'}))
 def test_confirmed_owner_code_export(self):
  self.assertEqual(export_values({'source_url':'https://hellomaali.com/products/china-palm'})['shop_code'],'CAS01')
