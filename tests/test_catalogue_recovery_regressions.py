import unittest
from audit804_semantics import review
from catalogue_object_rules import classify

class RecoveryRegressions(unittest.TestCase):
 def test_optional_third_piece_does_not_negate_supplied_pair(self):
  self.assertEqual(review('Stitched Embroidered Lawn Shirt + Shalwar',
   'Dupatta: Not Included\nTrouser: Lawn Zuri Shalwar Included', 'Clothing Sets'), [])
  self.assertIsNone(review('Shirt + Shalwar', 'Trouser: Not Included\nDupatta: Not Included', 'Clothing Sets'))
 def test_makeup_brand_is_not_a_desktop(self):
  self.assertNotEqual(review('MAC Studio Fix Powder Plus Foundation NC41', 'Face powder foundation.', 'Face Powders'), ['Complete desktop computer incorrectly classified as a component'])
  self.assertEqual(review('Apple Mac Studio M4', 'Desktop computer.', 'Desktop Computers'), [])
  self.assertTrue(review('Apple Mac Studio M4', 'Desktop computer.', 'Face Powders'))
 def test_original_details_untouched_by_object_recovery(self):
  examples=[('Hemani Herbals','Anti Dandruff Hair Mist 100ml','Hair Mists'),
   ('Xcessories Hub','TORRAS Phone Cases for iPhone 17 Pro Max','Phone Cases'),
   ('Limelight','Button Down Sweater','Sweaters'),('Habitt','Granite Tawa 35cm','Tawas')]
  for store,title,label in examples:
   with self.subTest(store=store):
    row={'name':title,'description':'Full specifications: 100 ml. Care: wash gently. Ingredients: coconut oil.'}
    before=dict(row)
    self.assertEqual(classify(row,store)[0],label)
    self.assertEqual(review(title,row['description'],label),[])
    self.assertEqual(row,before)
  self.assertIsNone(classify({'name':'Replacement cover for room heater','description':''},'Xcessories Hub'))
