import unittest
from subcategory_inference_support import infer
from audit804 import issues_for
class ReviewedRepairs(unittest.TestCase):
 def test_primary_objects_outrank_compatibility_and_components(self):
  cases=[('ASUS CPU Liquid Cooler','CPU Coolers'),('Active Stylus Pen for iPad','Stylus Pens'),('HP Top Load Laptop Bag','Laptop Bags & Backpacks'),('Sony DualSense Wireless Controller for PlayStation 5','Game Controllers'),('Logitech BRIO Business Webcam','Webcams'),('Miss Rose Eyelash Serum','Eyelash Serums'),('Buy Cocoa Butter Body Lotion 500ml & Get Baby Milk Lotion 250ml Free','Body Lotions')]
  for title,expected in cases:
   with self.subTest(title=title):self.assertEqual(infer(title,'')[0],expected)
 def test_loose_leaf_evidence_does_not_override_tea_bags(self):
  description='Premium tea blend containing curled leaves from Kenya.'
  self.assertEqual(infer('Dawoodi Blend 900 GM',description)[0],'Loose-Leaf Tea')
  self.assertEqual(infer('Tea Bags 100',description)[0],'Tea Bags')
 def test_independent_audit_accepts_reviewed_aliases_but_rejects_wrong_types(self):
  examples=[('Active Stylus Pen for iPad','Stylus Pens'),('CPU Liquid Cooler','CPU Coolers'),('Amson Yogurt Pouch','Yoghurt'),('Mouse Pad for Optical Mouse','Mouse Pads'),('Wireless Headset','Headsets & Headphones')]
  for title,category in examples:
   row={'name':title,'description':title+' with product details and specifications.','Category':category}
   self.assertFalse(issues_for(row),(title,issues_for(row)))
   row['Category']='Perfumes & Fragrances';self.assertTrue(issues_for(row))
 def test_audit_does_not_treat_fabric_shampoo_as_hair_or_ssd_specs_as_laptop(self):
  self.assertFalse(issues_for({'name':'White Cleansing Shampoo','description':'Fabric cleanser removes stains from clothes.','Category':'Fabric Detergents'}))
  self.assertFalse(issues_for({'name':'Lenovo Laptop, 16GB RAM 512GB SSD','description':'Laptop computer with memory and storage specifications.','Category':'Laptops'}))
  self.assertTrue(issues_for({'name':'SSD Enclosure','description':'External enclosure compatible with solid state storage drives.','Category':'Solid-State Drives'}))
