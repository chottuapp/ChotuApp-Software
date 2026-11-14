import copy,json,unittest
from pathlib import Path
from meat_source_support import normalize_capture,STORE,CODE

class MeatSourceTests(unittest.TestCase):
 def setUp(self):self.fixtures=json.loads((Path(__file__).parent/'fixtures/meat_public_offers.json').read_text())
 def test_real_public_offers_use_live_price_stock_and_source_units(self):
  for capture in self.fixtures:
   p=normalize_capture(capture)
   self.assertTrue(p['is_in_stock']);self.assertEqual(p['sku'],capture['url'].rsplit('-',1)[-1][:-5]);self.assertEqual(p['permalink'],capture['url'])
   self.assertNotIn('Barkat Meat House',p['description']);self.assertEqual(p['_source_branding']['original_source_description'],capture['description'])
  sale=normalize_capture(self.fixtures[1]);self.assertEqual(sale['prices']['price'],'89950');self.assertEqual(sale['prices']['regular_price'],'99950')
  pack=normalize_capture(self.fixtures[2]);self.assertEqual(pack['attributes'][0]['terms'][0]['name'],'1 set of four');self.assertEqual(pack['attributes'][0]['name'],'Quantity')
 def test_observed_option_prices_are_preserved_without_multiplication(self):
  c=copy.deepcopy(self.fixtures[0]);c['states'].append(dict(label='1 kg',selected='1 kg',price_html='Rs. 3,250',cart_text='ADD TO CART — Rs. 3,250',enabled=True))
  p=normalize_capture(c);self.assertEqual(p['_observed_variants'][1]['prices']['price'],'325000');self.assertNotEqual(p['_observed_variants'][1]['prices']['price'],'319900')
 def test_price_stock_identity_and_selected_option_conflicts_block(self):
  for kind in ('price','selection','currency','host'):
   c=copy.deepcopy(self.fixtures[0])
   if kind=='price':c['states'][0]['cart_text']='ADD TO CART — Rs. 1'
   if kind=='selection':c['states'][0]['selected']='2 kg'
   if kind=='currency':
    for schema in c['schemas']:schema['offers']['priceCurrency']='USD'
   if kind=='host':c['url']=c['url'].replace('barkatmeathouse.com','evil.test')
   with self.assertRaises(ValueError):normalize_capture(c)
 def test_owner_store_name_and_unique_code_are_bound(self):
  codes=json.loads((Path(__file__).resolve().parents[1]/'cloud/confirmed-shop-codes.json').read_text())
  self.assertEqual(STORE,'ChotuApp Meat House');self.assertEqual(CODE,'SE10086');self.assertEqual(codes[STORE],CODE);self.assertEqual(list(codes.values()).count(CODE),1)
