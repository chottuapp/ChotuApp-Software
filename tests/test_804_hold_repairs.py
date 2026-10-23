import unittest
from audit804 import issues_for
from audit804_semantics import review
from reviewed804_repairs import description,numbers
from subcategory_inference_support import infer
class HoldRepairsTests(unittest.TestCase):
 def test_independent_explicit_footwear_evidence(self):
  for title,label in [('Pink Pumps','Heels & Pumps'),('Casual Flip Flop','Sandals & Slides'),('Black Sneaker','Sneakers & Trainers'),('Pack of Hair Clips','Hair Clips & Pins')]:
   self.assertEqual(review(title,'',label),[])
  self.assertIsNone(review('Unknown collection','No product type supplied','Heels & Pumps'))
 def test_accessory_does_not_inherit_target_device_category(self):
  self.assertEqual(infer('CPU Thermal Paste 2g','Thermal compound')[0],'Thermal Paste')
  self.assertEqual(infer('DDR5 SO-DIMM Laptop Memory 8GB','')[0],'Computer Memory (RAM)')
  self.assertEqual(infer('UGREEN Mouse, 26000 DPI and USB','')[0],'Computer Mice')
  self.assertNotEqual(infer('Mouse Trap Book Rat Catching','Mouse trap')[0],'Computer Mice')
 def test_ubtan_sandal_is_not_footwear(self):self.assertEqual(infer('Khas Sandal Ubtan Powder','Fine powder for skin')[0],'Ubtan Powders')
 def test_concerns_rewrite_preserves_source_facts(self):
  row={'name':'3% Oat Extract Gentle Cleanser','description':'Dryness, Dehydration & Sensitivity'}
  fixed,reason=description(row,'Skin Factor',set())
  self.assertTrue(reason);self.assertIn(row['description'],fixed);self.assertTrue(numbers(row['description'])<=numbers(fixed))
  self.assertNotIn('dermatologist',fixed)
 def test_colonless_note_structure_is_reviewable(self):
  self.assertEqual(review('Lady Prive','Top\nCitrus, Coffee\nHeart\nRose\nBase\nVanilla','Perfumes & Fragrances'),[])
  self.assertIsNone(review('Opaque 30ml','No source product description','Perfumes & Fragrances'))
if __name__=='__main__':unittest.main()
