import unittest
from catalogue_object_rules import classify
from audit804_semantics import review
from hold804_repairs import description

class PrimaryElectronicsTests(unittest.TestCase):
 def test_named_object_survives_commas_and_compatibility_targets(self):
  examples=[('Redragon RGB (Wired, Wireless 2.4G, Bluetooth) Mechanical Keyboard','Keyboards'),('Apple Magic Keyboard for iPad Pro','Keyboards'),('Dell Tower PC 16GB 512GB SSD Keyboard & Mouse Included','Desktop Computers'),('Dark Flash ATX Gaming Tower PC Case','Computer Cases'),('Apple AirPods 4 With Wireless Charging Case','Earbuds'),('Apple AirPods Silicone Case','Earbud Cases'),('TP-Link 8-Port Gigabit Desktop Switch','Network Switches')]
  for name,expected in examples:
   with self.subTest(name=name):
    row=dict(name=name,description='Source-provided model details.')
    self.assertEqual(classify(row,'Paklap')[0],expected)
    self.assertEqual(review(name,row['description'],expected),[])
 def test_auditor_rejects_component_substitution_and_device_accessory_confusion(self):
  for name,wrong in [('Dell Tower PC 512GB SSD Keyboard & Mouse Included','Solid State Drives'),('Apple iMac 512GB SSD Magic Mouse Included','Computer Mice'),('Apple Magic Keyboard for iPad Pro','Tablets'),('Dark Flash ATX Gaming Tower PC Case','Desktop Computers'),('Apple AirPods Silicone Case','Earbuds')]:
   with self.subTest(name=name):self.assertTrue(review(name,'Exact source description.',wrong))
  self.assertEqual(review('Xbox Series X Gaming Console with 1 Controller','Source console specifications.','Gaming Consoles'),[])
  self.assertTrue(review('Controller for Xbox Gaming Console','Source controller specifications.','Gaming Consoles'))
 def test_unknown_model_and_store_name_do_not_establish_object_type(self):
  self.assertIsNone(classify(dict(name='Range Z123',description='New arrivals'),'Paklap'))
  self.assertIsNone(classify(dict(name='Universal Bundle',description=''),'House of Tools'))
 def test_sparse_copy_uses_only_named_object_and_retains_original_facts(self):
  row=dict(name='Coolbell CB-18 Cooling Pad For 14-17 Inch Laptops',description='Model CB-18')
  fixed,reason=description(row,'Paklap');self.assertTrue(reason);self.assertIn(row['name'],fixed);self.assertIn(row['description'],fixed);self.assertNotIn('warranty',fixed.lower())
 def test_bundle_repair_uses_verified_contents_and_preserves_component_specs(self):
  from unittest.mock import patch
  from catalogue_object_rules import audit
  row=dict(name='DIY Bundle',product_id='p',source_url='https://houseoftools.com.pk/product/diy/',description='Existing supplier note.')
  fact=dict(bundle_components=[dict(name='Drill'),dict(name='Hammer')],bundle_page_sha256='a'*64,verified_bundle_description='Pack Contents\n1 drill, 42V and 99Nm.\n1 hammer, 500g.')
  with patch('hold804_repairs.public_facts',return_value=fact):
   self.assertEqual(classify(row,'House of Tools')[0],'Tool Sets');self.assertEqual(audit(dict(row,Category='Tool Sets'),row),[])
   fixed,why=description(row,'House of Tools');self.assertTrue(why);self.assertIn('42V and 99Nm',fixed);self.assertIn(row['description'],fixed)
  with patch('hold804_repairs.public_facts',return_value=None):self.assertIsNone(classify(row,'House of Tools'));self.assertIsNone(audit(dict(row,Category='Tool Sets'),row))
