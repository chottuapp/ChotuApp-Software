import unittest
from hold804_repairs import category,description
from audit804_semantics import review
class HeldObjectRecovery(unittest.TestCase):
 def test_bag_word_does_not_override_hair_accessory_set(self):
  row={'name':'Bag Hair Accessory box-19 (Assorted Colors)','description':'Bag Hair Accessory box-19 (Assorted Colors)'}
  self.assertEqual(category(row,'Rawayat')[0],'Hair Accessory Sets')
  self.assertIn('hair accessory set',description(row,'Rawayat')[0])
 def test_hair_pony_alias_retains_colour_and_reference(self):
  row={'name':'Organza Pony-01 (Blue)','description':'Organza Pony-01 (Blue)'}
  self.assertEqual(category(row,'Rawayat')[0],'Hair Ties & Scrunchies')
  self.assertEqual(review(row['name'],description(row,'Rawayat')[0],category(row,'Rawayat')[0]),[])
 def test_unverifiable_bundle_not_invented(self):
  row={'name':'Two of a Kind Deal','description':'Two of a Kind Deal'}
  self.assertEqual(description(row,'Bonanza Satrangi')[0],row['description'])
 def test_spf_not_inferred_from_brand_or_product_name(self):
  row={'name':'Janssen -Face guard advanced 50ml','description':'A skin product.'}
  self.assertNotEqual((category(row,'Elite Cosmetics') or [None])[0],'Facial Sun Protection')

 def test_reviewed_label_replaces_only_exact_copied_supplier_body(self):
  from audit804 import issues_for
  from hold804_repairs import visual_review
  original={'product_id': 'CP815360dae141', 'name': 'Tea Tree Oil 10ml - Xpel', 'description': '100% vegan · Enriched with Community Trade tea tree oil from the foothills of Mount Kenya · Our 20ml bottle is packed with the oil of 15,000 tea tree leaves.', 'source_url': 'https://elitecosmeticspk.com/products/tea-tree-oil-10ml', 'Category': 'Essential Oils'}
  output=dict(original)
  output['Category']=category(original,'Elite Cosmetics')[0]
  output['description']=description(original,'Elite Cosmetics')[0]
  self.assertNotIn('20ml',output['description'])
  self.assertIn('10 ml',output['description'])
  self.assertNotIn('Description lost source numeric facts',issues_for(output,original))
  changed=dict(original,description=original['description']+' New verified batch 77.')
  self.assertIsNone(visual_review(changed,'Elite Cosmetics'))
  self.assertIn('Description lost source numeric facts',issues_for(output,changed))
 def test_hand_cream_does_not_become_facial_treatment(self):
  row={'name':'Kojic Hand & Feet Cream - Urgent Facial 100ml','description':'Apply to hands and feet. Wash face after use.'}
  self.assertEqual(category(row,'Elite Cosmetics')[0],'Hand & Foot Creams')
