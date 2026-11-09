import unittest
from subcategory_inference_support import infer,apply
from sold_object_category_support import source_object
from sold_object_audit import review
from hold804_repairs import category,public_index
class SoldObjectTests(unittest.TestCase):
 def test_shoe_styling_never_becomes_clothing(self):
  for companion in ('straight pants','a flirty dress','jackets and coats'):
   for title in ('TIFFANY','Another seller model'):
    result=infer(title,'The ankle strap black heel has a leather sole. Can be worn with '+companion+'.')
    self.assertEqual(result[0],'Heels & Pumps')
  self.assertEqual(infer('CAMILA','Vacation in style with our Pearson sandals. Wear yours with a flirty dress.')[0],'Sandals & Slides')
 def test_khussa_foundation_and_chain_design_are_not_cosmetics_or_jewellery(self):
  self.assertEqual(infer('Dia khussa (black)','This khussa has a black foundation and leather inner sole.')[0],'Khussas')
  self.assertEqual(infer('Dual Chain','These sandals have a chain strap and soft sole.')[0],'Sandals & Slides')
 def test_source_type_precedes_ambiguous_title(self):
  row={'name':'BALLET COAT - WHITE','description':'','source_product_type':'flats'};apply(row);self.assertEqual(row['subcategory'],'Flats')
  self.assertEqual(source_object('Unnamed','',website_path='Women > Sandals')[0],'Sandals & Slides')
 def test_actual_merchant_collection_precedes_ballet_coat_name(self):
  fact=next(v for v in public_index().values() if v['store']=='Blackbeiger' and v['public_title']=='BALLET COAT - WHITE')
  row={'name':fact['public_title'],'product_id':fact['product_id'],'source_url':fact['source_url'],'description':fact['description'],'Category':'Jackets & Coats'}
  self.assertEqual(category(row,'Blackbeiger')[0],'Flats');self.assertTrue(review(row))
  row['Category']='Flats';self.assertEqual(review(row),[])
 def test_generic_styles_and_related_footwear_do_not_define_object(self):
  self.assertIsNone(infer('Mystery','Wear yours with trousers.'))
  self.assertIsNone(infer('Mystery','Pair this dress with loafers.'))
  self.assertIsNone(infer('BALLET COAT - WHITE','Refund policy.'))
  self.assertNotEqual(infer('Bootcut jeans','Denim trousers.')[0],'Boots')
  self.assertNotEqual(infer('Shirt','A cotton shirt. Pair with loafers.')[0],'Loafers')
  self.assertIsNone(source_object('Heel cream','For cracked heels.'))
  self.assertIsNone(source_object('Shoe brush','Cleans shoes and sandals.'))
 def test_independent_audit_rejects_cross_domain_errors(self):
  for wrong in ('Trousers','Dresses & Maxis','Jackets & Coats','Foundations','Jewellery Chains'):
   row=dict(name='Dia khussa',description='This khussa has a leather sole and black foundation.',Category=wrong)
   self.assertTrue(review(row))
  self.assertEqual(review(dict(name='Dia khussa',description='Leather sole.',Category='Khussas')),[])

 def test_full_independent_audit_cannot_pass_footwear_as_trousers(self):
  from audit804 import issues_for
  self.assertTrue(issues_for(dict(name='Dia khussa',description='This khussa has a leather inner sole.',Category='Trousers')))
  self.assertEqual(issues_for(dict(name='Dia khussa',description='This khussa has a leather inner sole.',Category='Khussas')),[])

 def test_shoe_design_named_lace_uses_actual_collection_not_lace_accessory_guess(self):
  self.assertEqual(source_object('BELLE LACE - BEIGE','',product_type='Flats')[0],'Flats')
  self.assertIsNone(source_object('Replacement shoe laces','For boots and sneakers.'))
