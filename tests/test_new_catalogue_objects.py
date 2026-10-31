import unittest
from catalogue_object_rules import classify, overview, audit

class NewCatalogueObjectTests(unittest.TestCase):
 def row(self,title,body='',host='houseoftools.com.pk'):
  return {'name':title,'description':body,'source_url':'https://'+host+'/products/test'}
 def test_accessories_are_not_the_machine_or_makeup(self):
  cases=[('27 Pcs Hex key and torx key set','Hex & Torx Keys'),('Cordless hydraulic cable cutter CRCLI2005','Cutting Tools'),('Diamond disc for floor saw','Saw Blades & Chains'),('1/2 inch Impact socket','Sockets & Socket Sets'),('USB socket HESST182US','Electrical Switches & Sockets'),('Pump pliers','Pliers'),('Saw chain','Saw Blades & Chains'),('Steel wire brush','Brushes')]
  for title,label in cases:
   with self.subTest(title=title):
    r=self.row(title);self.assertEqual(classify(r,'House of Tools')[0],label);self.assertEqual(audit(dict(r,Category=label),r),[])
 def test_power_machine_and_accessory_names_keep_their_sold_identity(self):
  for title,label in [('Cordless Rotary Hammer','Drills & Drivers'),('SDS plus hammer drill','Drills & Drivers'),('Mini Hacksaw frame','Saw Frames'),('Foldable Extension Pole','Extension Poles'),('Square to Hex Adapter','Tool Adapters')]:
   r=self.row(title);self.assertEqual(classify(r,'House of Tools')[0],label);self.assertEqual(audit(dict(r,Category=label),r),[])
 def test_prepared_food_is_not_its_ingredient(self):
  for title,label in [('Chocolate Cake','Cakes & Desserts'),('Peanut Butter Pretzels (200g)','Biscuits & Crackers'),('Cheddar Cheese Crackers','Biscuits & Crackers'),('Strawberry Greek Yogurt','Yoghurt'),('Coconut Milk','Milk & Cream'),('Milk Chocolate','Chocolate & Confectionery'),('Strawberries 500g','Fruit')]:
   r=self.row(title,title,'freshbasket.com.pk');self.assertEqual(classify(r,'Fresh Basket')[0],label)
 def test_sparse_identity_keeps_quantities_without_claims(self):
  r=self.row('Anmol Strawberry Greek Yogurt 500g','Anmol Strawberry Greek Yogurt 500g','freshbasket.com.pk');text,reason=overview(r,'Fresh Basket');self.assertIn(r['name'],text);self.assertTrue(reason);self.assertNotIn('organic',text)
 def test_unrelated_store_and_unknown_model_stay_unresolved(self):
  r=self.row('Unknown 123');self.assertIsNone(classify(r,'House of Tools'));self.assertIsNone(classify(self.row('Drill'),'Other Store'))
  self.assertIsNone(audit(dict(r,Category='Drills & Drivers'),r));self.assertIsNone(audit(dict(r,Category='Drills & Drivers'),None))
 def test_original_source_disproves_changed_category(self):
  source=self.row('Cordless drill','20V motor');self.assertIsNone(audit(dict(source,name='Chocolate',Category='Chocolate & Confectionery'),source))
 def test_wallet_pocket_does_not_change_sold_object(self):
  r=self.row('Slim Leather Wallet','A slim leather wallet that fits in a trouser pocket.','gsevenleather.com');self.assertEqual(classify(r,'G7 Leather')[0],'Wallets');self.assertEqual(audit(dict(r,Category='Wallets'),r),[])
 def test_fabric_needs_actual_source_evidence(self):
  r=self.row('Premium Cotton - Sand',"Our 4.5-meter men's suit fabric.",'binfahad.pk');self.assertEqual(classify(r,'Bin Fahad')[0],'Unstitched Fabric');self.assertIsNone(classify(self.row('Cotton colour','Unknown'),'Bin Fahad'))


class MerchantTypeRecoveryTests(unittest.TestCase):
 def test_generic_names_require_exact_identity_matched_merchant_type(self):
  from unittest.mock import patch
  row={'name':'Unnamed range 123','description':'Unnamed range 123','product_id':'p','source_url':'https://freshbasket.com.pk/products/p'}
  with patch('hold804_repairs.public_facts',return_value={'product_type':'Coffee','published_tags':[],'source_url':row['source_url']}):
   self.assertEqual(classify(row,'Fresh Basket')[0],'Tea & Coffee');self.assertEqual(audit(dict(row,Category='Tea & Coffee'),row),[])
  with patch('hold804_repairs.public_facts',return_value={'product_type':'New Arrivals','published_tags':['Brand','Gold'],'source_url':row['source_url']}):self.assertIsNone(classify(row,'Fresh Basket'))
  with patch('hold804_repairs.public_facts',return_value={'product_type':'Coffee','published_tags':['Cheese'],'source_url':row['source_url']}):self.assertIsNone(classify(row,'Fresh Basket'))
 def test_source_tags_survive_validation(self):
  from audit804_automation import validated_facts
  from datetime import datetime,timezone
  report={'checked_utc':datetime.now(timezone.utc).isoformat(),'run_id':'1','results':[{'store':'Fresh Basket','product_id':'p','name':'Range','source_url':'https://freshbasket.com.pk/products/range','product':{'handle':'range','title':'Range','type':'Coffee','tags':['Coffee','New Arrivals'],'description':'Range'}}]}
  facts=validated_facts(report,{'Fresh Basket':{'url':'https://freshbasket.com.pk'}});self.assertEqual(facts[0]['published_tags'],['Coffee','New Arrivals'])

if __name__=='__main__':unittest.main()
