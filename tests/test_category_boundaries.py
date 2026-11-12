import unittest
from sold_object_category_support import correct_audience_category,source_object
from sold_object_audit import category_boundary_issues
from audit804 import issues_for

class CategoryBoundaries(unittest.TestCase):
 def test_opposite_audience_and_unknown_do_not_pass(self):
  for name,wrong,right in [('Gents Cotton Suit',"Women's Suits","Men's Suits"),('Ladies Sandals',"Men's Sandals","Women's Sandals")]:
   row={'name':name,'Category':wrong,'description':'Source product details.'}
   self.assertTrue(category_boundary_issues(row))
   self.assertEqual(correct_audience_category(row,wrong),right)
   self.assertFalse(category_boundary_issues(dict(row,Category=right)))
  row={'name':'Cotton Suit','Category':"Women's Suits"}
  self.assertEqual(correct_audience_category(row,row['Category']),'Suits')
  self.assertTrue(category_boundary_issues(row))
 def test_gender_not_guessed_from_colour_brand_or_styling(self):
  row={'name':'Pink Cotton Suit','brand':'Ladies Collection','description':'Style with mens shoes.'}
  self.assertEqual(correct_audience_category(row,"Women's Suits"),'Suits')
  self.assertEqual(correct_audience_category(row,'Clothing Sets'),'Clothing Sets')
 def test_verified_path_must_be_from_exact_product_domain(self):
  row={'name':'Cotton Suit','source_url':'https://shop.example/products/a','website_category_status':'verified_product_breadcrumb','website_category_checked_at':'2026-11-12','website_category_source_url':'https://other.example/products/a','website_category_path':'Women > Suits'}
  self.assertEqual(correct_audience_category(row,"Women's Suits"),'Suits')
  row['website_category_source_url']=row['source_url']
  self.assertEqual(correct_audience_category(row,"Women's Suits"),"Women's Suits")
 def test_conflicts_stay_neutral(self):
  row={'name':'Men and Women Cotton Suit'}
  self.assertEqual(correct_audience_category(row,"Women's Suits"),'Suits')
 def test_all_seller_family_errors_are_nonwaivable(self):
  for kind,wrong in [('shirt','Foundations'),('shampoo','Shirts'),('sandals','Trousers'),('notebook','Face Serums')]:
   source={'name':'Model A','source_product_type':kind,'description':'Original useful source product details.'}
   row=dict(source,Category=wrong)
   self.assertTrue(category_boundary_issues(row,source))
   self.assertTrue(issues_for(row,source))
 def test_exact_object_types_across_families(self):
  for kind,label in [('shirt','Shirts'),('shampoo','Shampoos'),('face serum','Face Serums'),('notebook','Notebooks'),('lunch box','Lunch Boxes')]:
   self.assertEqual(source_object('Model A','',kind)[0],label)
  for vague in ['Women','New Arrivals','Premium','Pink']:
   self.assertIsNone(source_object('Model A','',vague))
 def test_repairs_preserve_original_facts(self):
  row={'name':'Gents Cotton Suit','Category':"Women's Suits",'base_price (PKR)':5000,'available (yes/no)':'yes'}
  before=dict(row);correct_audience_category(row,row['Category']);self.assertEqual(row,before)
 def test_fresh_export_also_corrects_stale_gender_category(self):
  from subcategory_inference_support import apply
  row={'name':'Gents Model A','description':'Original source details.','subcategory':"Women's Clothing Sets"}
  apply(row);self.assertEqual(row['subcategory'],"Men's Clothing Sets")
  manual=dict(row,subcategory="Women's Clothing Sets",subcategory_source='manual')
  apply(manual);self.assertEqual(manual['subcategory'],"Women's Clothing Sets")
