import unittest
from hold804_repairs import category,description
from audit804 import issues_for
class SourceBoundHoldTests(unittest.TestCase):
 def row(self,name,body='Source product specifications retained.',**kwargs):return dict(name=name,description=body,source_url='https://stylo.pk/products/example',**kwargs)
 def test_real_sold_objects_outrank_colours_components_and_promotions(self):
  cases=[('Mehndi Ethnic Khussa For Women EC8785','Khussa Shoes'),('Skin Seamless Bra For Women LB5383','Bras'),('Thermalright AM5 CPU Contact Frame V2','CPU Contact Frames'),('Thermalright ARGB Fan Hub X10','Fan & Lighting Controllers'),('Lian Li UNI Fan SL Infinity FLEX 120mm Wireless Normal Blade ARGB Fan 3 Pack, L-Wireless Controller Included','Cooling Fans')]
  for name,label in cases:
   with self.subTest(name=name):
    row=self.row(name);actual=category(row,'Computer Zone' if 'Thermalright' in name or 'Lian' in name else 'Stylo');self.assertEqual(actual[0],label)
 def test_included_controller_and_technical_ring_are_not_sold_objects(self):
  row=self.row('8BitDo Ultimate 2 Wireless Controller, RGB Fire Ring')
  self.assertIsNone(category(row,'Computer Zone'))
  self.assertEqual(category(self.row('Wash & Wear Kurta Pajama - 2612'),'Zellbury')[0],'Kurta & Pyjama Sets')
  self.assertEqual(category(self.row('Disposable Compressed Towels, Travel Wipes'),'Elite Cosmetics')[0],'Compressed Towels')
 def test_promo_retains_both_quantities_without_inventing_a_third_item(self):
  name='Buy Baby Washing Gel 500 ML & Get Body Lotion 100 ML Free';fixed,reason=description(self.row(name,name),'Cool and Cool')
  self.assertEqual(fixed,'Baby Washing Gel 500 ML. Includes Body Lotion 100 ML as a complimentary item.');self.assertTrue(reason)
 def test_named_pack_does_not_add_material_or_pair_quantity(self):
  name='Spiral Hair Ties-19 (Pack of 2)';fixed,reason=description(self.row(name,name),'Rawayat')
  self.assertIn('pack of 2',fixed);self.assertIn('19',fixed);self.assertNotIn('silk',fixed)
  name='Fancy Earring-331 (White)';fixed,reason=description(self.row(name,name),'Rawayat');self.assertNotIn('pair',fixed);self.assertIn('331',fixed)
 def test_verified_collection_is_product_evidence_not_a_guess_from_a_colour(self):
  row=self.row('Mint','Mint',website_category_path='Fragrances > Gourmand',website_category_status='verified_navigation_membership',website_category_source_url='https://stylo.pk/collections/gourmand',website_category_checked_at='2026-10-21T00:00:00+00:00')
  fixed,reason=description(row,'Cool and Cool');self.assertIn('fragrance',fixed);self.assertIn('Gourmand',fixed)
  self.assertEqual(issues_for(dict(row,description=fixed,Category='Perfumes & Fragrances')),[])
  row['website_category_source_url']='https://other.example/collections/gourmand';self.assertEqual(description(row,'Cool and Cool'),('Mint',None))
 def test_unsupported_object_and_growth_serum_are_not_rewritten_as_eyelashes(self):
  self.assertIsNone(category(self.row('Unidentified Collection 01'),'Stylo'))
  result=category(self.row('Eyelashes Growth Serum'),'Elite Cosmetics');self.assertTrue(result is None or result[0]!='False Eyelashes')
 def test_image_does_not_override_named_product_identity(self):
  self.assertIsNone(category(self.row('Key Ring Holder'),'Stylo'))
if __name__=='__main__':unittest.main()
