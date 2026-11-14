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

 def test_verified_species_categories_survive_repair_and_independent_audit(self):
  from hold804_repairs import category
  from audit804 import issues_for
  from catalogue_object_rules import audit, classify
  for label,title,body in [('Beef','Fresh Beef Boneless BBQ Chunks','Fresh boneless beef chunks for BBQ.'),('Beef','Beef Kaleeji + Gurday Mix Offer','Fresh beef liver and kidneys.'),('Veal (Bachiya)','Fresh Veal (Bachiya) Biryani (Bone-in)','Fresh veal bone-in biryani cut.'),('Mutton','Mutton Kaleji','Fresh goat liver.')]:
   url='https://barkatmeathouse.com/product/item.html'
   row=dict(name=title,description=body+' Prepared fresh by our master butchers and hygienically sealed for delivery. Price per kilogram.',source_url=url,website_category_source_url=url,website_category_path=label,website_category_status='verified_navigation_membership',website_category_checked_at='2026-11-14T00:00:00Z',Category=label)
   self.assertEqual(category(row,STORE)[0],label)
   self.assertEqual(issues_for(row,source=row),[])
   self.assertTrue(audit(dict(row,Category='Meat & Poultry'),row))
   bad=dict(row,website_category_source_url=url+'/different')
   self.assertIsNone(audit(bad,bad));self.assertNotEqual((classify(bad,STORE) or (None,))[0],label)
   bad=dict(row,name='Beef grinder knife')
   self.assertIsNone(audit(bad,bad));self.assertNotEqual((classify(bad,STORE) or (None,))[0],label)

 def test_only_owner_approved_category_pages_are_fetched(self):
  from meat_source_support import OWNER_CATEGORY_PAGES
  self.assertEqual(OWNER_CATEGORY_PAGES,tuple('https://barkatmeathouse.com/shop?category='+k for k in ('beef','mutton','veal')))
