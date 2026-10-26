import unittest
from hold804_repairs import category
from audit804 import issues_for
class NewStoreRecoveryTests(unittest.TestCase):
 def test_shoe_component_mentions_do_not_replace_sold_object(self):
  row={'name':"Men's Soft-Insole Slides",'description':'Slides with a cushioned insole and an open toe.'}
  self.assertEqual(category(row,'Ndure')[0],'Slides')
  self.assertEqual(issues_for(dict(row,Category='Slides')),[])
 def test_bag_set_keeps_bundle_identity_and_count(self):
  row={'name':'Posh set of 3 Bag brown','description':'Three bags with matching straps.'}
  self.assertEqual(category(row,'Astore Bags')[0],'Bag Sets')
  self.assertEqual(issues_for(dict(row,Category='Bag Sets')),[])
 def test_brand_only_name_cannot_establish_a_footwear_type(self):
  self.assertIsNone(category({'product_id':'unknown','source_url':'https://www.bata.com.pk/products/unknown','name':'Bata - Men','description':'Article 999-0000'},'Bata'))
