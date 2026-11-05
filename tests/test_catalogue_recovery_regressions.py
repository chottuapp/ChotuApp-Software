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
 def test_culotte_pair_with_optional_scarf_excluded(self):
  self.assertEqual(review('Stitched Lawn Shirt + Culotte','Cut: Boxy\nDupatta: Not Included\nTrouser: Printed culotte Included','Clothing Sets'),[])
  self.assertIsNone(review('Stitched Lawn Shirt + Culotte','Cut: Boxy\nTrouser: Not Included','Clothing Sets'))
 def test_bundle_requires_multiple_explicit_supplied_items(self):
  row={'name':'DIY Bundle','description':'Pack Contents\n1 × Spirit Level 60cm\n1 × Steel Measuring Tape 8m\n1 × Snap-Off Blade Knife 18mm','source_url':'https://houseoftools.com.pk/product/diy-bundle/'}
  self.assertEqual(classify(row,'House of Tools')[0],'Tool Sets')
  from catalogue_object_rules import audit
  self.assertEqual(audit(dict(row,Category='Tool Sets'),row),[])
  row['description']='Pack Contents\n1 × Spirit Level 60cm\nSuggested accessories: measuring tape and knife.'
  self.assertIsNone(classify(row,'House of Tools'))
  self.assertIsNone(audit(dict(row,Category='Tool Sets'),row))
 def test_ambiguous_identical_names_use_each_original_body(self):
  base={'name':'WISDOM FRESH EFFECT SENSITIVE 1S'}
  a=dict(base,description='A toothpaste for everyday oral care.')
  b=dict(base,description='A toothbrush for everyday oral care.')
  self.assertEqual(classify(a,'Rios')[0],'Toothpastes')
  self.assertEqual(classify(b,'Rios')[0],'Toothbrushes')
  self.assertIsNone(classify(dict(base,description='Fresh effect.'),'Rios'))
 def test_concrete_source_type_not_a_brand_guess(self):
  row={'name':'JCS-102','brand':'Boys Cotton Silk Shalwar','description':'Size: 2 Y, 4 Y'}
  self.assertEqual(classify(row,'Junaid Jamshed')[0],'Shalwars')
  self.assertEqual(review(row['name'],row['description'],'Shalwars',source_type=row['brand']),[])
  self.assertIsNone(classify(dict(row,brand='J.'),'Junaid Jamshed'))
 def test_excluded_paired_trouser_does_not_turn_shirt_into_set(self):
  row={'name':'SS23BSP226F','description':'SHOULDER: 18 | 19\nSLEEVE LENGTH 3/4: 14 | 15\nTrouser: Not Included but Paired with SS23TRE226'}
  self.assertEqual(classify(row,'Sana Safinaz')[0],'Shirts')
  self.assertEqual(review(row['name'],row['description'],'Shirts'),[])
 def test_measured_lehenga_components_do_not_imply_stitched(self):
  row={'name':'N243','description':'Component Details (3 Piece): Measurement\nShirt Lining: 2 Meters\nDupatta: 2.5 Meters\nLehnga: 5 Meters'}
  self.assertEqual(classify(row,'Sana Safinaz')[0],'Unstitched Lehenga Sets')
  self.assertEqual(review(row['name'],row['description'],'Unstitched Lehenga Sets'),[])
 def test_public_tags_must_identify_exact_object_not_brand(self):
  from unittest.mock import patch
  from catalogue_object_rules import audit
  row={'name':'Power - Women','source_url':'https://www.bata.com.pk/products/551-2096','description':'551-2096\nSize: 36'}
  with patch('hold804_repairs.public_facts',return_value={'published_tags':['Sneakers','Women']}):
   self.assertEqual(classify(row,'Bata')[0],'Sneakers')
   self.assertEqual(audit(dict(row,Category='Sneakers'),row),[])
  with patch('hold804_repairs.public_facts',return_value={'published_tags':['Power','Women']}):
   self.assertIsNone(classify(row,'Bata'))
 def test_bundle_source_recovery_reads_page_when_api_is_empty(self):
  from audit804_automation import request_from_holds
  state={'audit804_results':{'Rawayat':{'status':'hold','findings':[{'name':'Ruby Bundle','product_id':'p1','source_url':'https://rawayat.com.pk/products/ruby-bundle'}]}}}
  request=request_from_holds(state,{'Rawayat':{'url':'https://rawayat.com.pk'}})
  self.assertTrue(request['products'][0]['inspect_bundle'])
 def test_conflicting_public_object_tags_stay_held(self):
  from unittest.mock import patch
  row={'name':'Power - Women','source_url':'https://www.bata.com.pk/products/551-2096','description':'551-2096'}
  with patch('hold804_repairs.public_facts',return_value={'published_tags':['Sneakers','Men Sandals']}):
   self.assertIsNone(classify(row,'Bata'))
 def test_coded_outfit_uses_positive_fields_not_missing_scarf(self):
  self.assertEqual(review('R-114','Cut: Short Shirt\nDupatta: Not Included\nTrouser: Raw Silk Culotte Included','Clothing Sets'),[])
  self.assertIsNone(review('R-114','Cut: Short Shirt\nDupatta: Not Included\nTrouser: Not Included','Clothing Sets'))
 def test_nonbreaking_spaces_in_source_component_fields(self):
  self.assertEqual(review('Stitched Shirt + Culotte','Cut: Basic\nDupatta: Not Included\nTrouser:\u00a0Black Raw Silk Culotte Included','Clothing Sets'),[])
