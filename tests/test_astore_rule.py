import unittest
from locked_store_rules import allowed_product
class AstoreTests(unittest.TestCase):
 def test_womens_mens_bags_and_wallets(self):
  for name in ['Ladies Handbag','Mens Wallet','Long Travel Bag','Knot Flower Tote','Canvas Backpack','Mini Clutch','Bag set of 3','Mini Pouch','Mini Pouches','Ladies Mini Pouches']:
   self.assertTrue(allowed_product('https://www.astorebags.pk',{'title':name}))
 def test_unrelated_and_unknown_items_never_pass_from_store_name(self):
  for name in ['Watch and Wallet Set','Bag charm','Bag strap','Shoes','Collection 123','Perfume','Sunglasses']:
   self.assertFalse(allowed_product('https://astorebags.pk',{'title':name}))
 def test_rule_is_store_scoped_and_uses_explicit_product_type(self):
  self.assertTrue(allowed_product('https://servis.pk',{'title':'Shoes'}))
  self.assertTrue(allowed_product('https://astorebags.pk',{'title':'Model 123','product_type':'Ladies Bag'}))
