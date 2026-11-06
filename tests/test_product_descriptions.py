import re,unittest
from product_description_support import render_description,completeness_issues,numeric_facts,overview_matches
class ProductDescriptionTests(unittest.TestCase):
 def test_concise_material_design_and_pack_facts_are_complete(self):
  for name,body in [('Stainless Steel Openable Kara -45','Stainless Steel Kara'),('Moti Mala -02 (Multi)','Crystal Mala'),('Gold Bangles-142 (Golden)','Set of 4 Bangles'),('Calligraphy Allah Pendant-11','Calligraphy Allah Pendant'),('Feather Earring (White)','Feather Earring')]:
   with self.subTest(name=name):
    self.assertFalse(completeness_issues(body,name))
    self.assertFalse(completeness_issues(render_description(body,name),name))
 def test_options_codes_and_category_padding_cannot_pass_as_a_description(self):
  for name,body in [('Bata - Bags','901-6196\nProduct Info\n\nProduct Options:\nSize: 10\nColor: Black'),('Stella Perfum For Ladies PR0134','Stella Perfum For Ladies PR0134 is a fragrance.\nProduct Options:\nColor: Multy\nSize: Standard')]:
   with self.subTest(name=name):
    self.assertTrue(completeness_issues(body,name));self.assertTrue(completeness_issues(render_description(body,name),name))
 def test_real_jewellery_facts_are_polished_without_promotional_filler(self):
  body='Gold Platted Mala\nStandard size\nWe provide 100% same & fine quality product as show in picture.\nJewellery Care : Keep away from water perfume & other chemicals Clean it with dry and soft cloth.\nWe provide very reasonable prices as compared to other stores.\nAll items are packed in the Rawayat Ecommerce Box'
  after=render_description(body,'Layer Beaded Mala-07 (Golden/Multi)','Necklaces')
  self.assertIn('gold-plated mala',after);self.assertIn('Standard size',after);self.assertIn('Care Instructions',after);self.assertIn('water, perfume',after);self.assertIn('dry, soft cloth',after);self.assertIn('Rawayat Ecommerce Box',after)
  self.assertNotIn('100%',after);self.assertNotIn('reasonable prices',after);self.assertEqual(numeric_facts(body),numeric_facts(after));self.assertFalse(completeness_issues(after,'Layer Beaded Mala-07 (Golden/Multi)'))
 def test_real_numbers_warnings_material_contents_and_options_are_preserved(self):
  body='A cotton shirt with a button front and printed sleeves.\nFabric: 80% cotton, 20% polyester\nMeasurements: Chest 21.5 inches; length 46 inches\nCare Instructions: Wash at 30 degrees. Do not bleach.\nProduct Options:\nSize: S, M, L\nColor: Blue, Green'
  after=render_description(body,'Printed Shirt','Shirts')
  for fragment in ('80% cotton','20% polyester','21.5 inches','46 inches','30 degrees','Do not bleach','Size: S, M, L','Color: Blue, Green'):self.assertIn(fragment,after)
  self.assertEqual(numeric_facts(body),numeric_facts(after));self.assertEqual(render_description(after,'Printed Shirt','Shirts'),after)
 def test_long_electronic_specs_and_numbered_directions_are_not_truncated(self):
  body='A controller with an LCD display and USB connectivity.\nSpecifications:\n'+ '\n'.join('Parameter '+str(i)+': '+str(i*2)+' mm' for i in range(100))+'\nHow to Use Step 1: Connect USB. Step 2: Press the power button.'
  after=render_description(body,'Controller','Controllers')
  self.assertEqual(numeric_facts(body),numeric_facts(after));self.assertIn('Parameter 99: 198 mm',after);self.assertIn('Step 2:',after)
 def test_reviewed_photo_identity_can_survive_safe_display_formatting(self):
  overview='Loose decorative stones with faceted faces and pointed backs for jewellery decoration. The product photograph shows a red design; no gemstone composition is specified.'
  after=render_description(overview+'\n\nListing: Stone','Stone','Decorative Jewellery Stones')
  self.assertNotIn('Listing:',after);self.assertTrue(overview_matches(after,overview))
 def test_no_missing_ingredients_benefits_materials_or_capacity_are_invented(self):
  body='A rectangular hair clip with a flower design and a metal clasp.'
  after=render_description(body,'Flower Clip','Hair Clips')
  for word in ('hypoallergenic','waterproof','premium','guaranteed','gold-plated'):self.assertNotIn(word,after)
  with self.assertRaisesRegex(ValueError,'Excel cell capacity'):render_description('Useful product detail. '*2000,'Long product')

 def test_ordered_promotional_list_does_not_keep_broken_bullets_or_false_numeric_facts(self):
  body='1. Feather Earring\n2. This Earing available very reasonable price.\n3. Fancy Jewelry for wedding season is normally trendy in Pakistan.\n4. We provide 100% same & fine quality product as show in picture.\nJewellery Care: Keep away from water perfume & other chemicals Clean it with dry and soft cloth.'
  result=render_description(body,'Feather Earring (White)','Earrings')
  self.assertNotIn('100%',result);self.assertNotIn('reasonable price',result);self.assertNotIn('trendy in Pakistan',result);self.assertNotIn('• 2.',result)
  self.assertEqual(numeric_facts(body),numeric_facts(result))

 def test_customer_headings_do_not_erase_explicit_jewellery_set_components(self):
  from audit804_semantics import review
  text='Zircon Mala set with Studs.\nJewellery Care: Keep away from water perfume and other chemicals.'
  result=render_description(text,'Mala Set-08 (Maroon)','Jewellery Sets')
  self.assertEqual(review('Mala Set-08 (Maroon)',result,'Jewellery Sets'),[])
  self.assertNotEqual(review('Mala Set-08','Mala set without studs.','Jewellery Sets'),[])
 def test_dense_narrative_is_readable_without_losing_sentences(self):
  from description_readability import issues
  text=' '.join('This sourced product feature retains its exact dimensions and construction details.' for i in range(20))
  result=render_description(text,'Fixture')
  self.assertEqual(issues(result),[]);self.assertEqual(result.count('exact dimensions'),20)

 def test_toy_age_warnings_and_exact_option_values_are_preserved(self):
  text='A building block set with animal-shaped pieces for creative play.\nRecommended Age: 3 years and above\nPrecautions: Not suitable for children under 3 years. Small parts.\nProduct Options:\nColor: Gold Platted, Multy\nSize: Standard'
  out=render_description(text,'Animal Blocks','Building Blocks')
  self.assertIn('Age & Suitability',out);self.assertIn('Not suitable for children under 3 years',out);self.assertIn('Color: Gold Platted, Multy',out);self.assertNotIn('Available Options',out);self.assertEqual(numeric_facts(text),numeric_facts(out))

 def test_colour_kit_conditioner_does_not_change_primary_product_type(self):
  from audit804 import issues_for
  row=dict(name='Casting Brown Hair Color 400',Category='Hair Colours',description='A brown hair colour kit with colouring cream, developer and a hair conditioner. Follow the included directions.')
  self.assertNotIn('Primary product type and Category disagree: hair conditioner',issues_for(row))
  self.assertTrue(any('Primary product type' in x for x in issues_for(dict(row,Category='Hair Conditioners'))))

 def test_specific_named_hair_product_wins_over_secondary_ingredients(self):
  from audit804 import issues_for
  from audit804_semantics import review
  for name,body,label in [('Brown Colour Enhancing Hair Mask 200ml','A conditioning hair mask to maintain your hair colour.','Hair Masks'),('Color Protect Condtioner 175Ml','A conditioner to help protect hair colour and shine.','Hair Conditioners')]:
   self.assertFalse(any('Primary product type' in i for i in issues_for(dict(name=name,description=body,Category=label))))
  body='The no-ammonia Creme formula blends away grey hair. Colour lasts up to 28 shampoos. After colouring, apply the coconut oil conditioner.'
  self.assertEqual(review('Casting Dark Brown 300',body,'Hair Colours'),[])
  self.assertNotEqual(review('Colour Protect Conditioner',body,'Hair Colours'),[])

 def test_short_explicit_facts_are_written_naturally_without_word_count_padding(self):
  cases=[('White Solid Tank Top PT6052','Solid camisole\nProduct Options:\nColor: White\nSize: M','A solid camisole in white.'),('Cushion Hair Brush CL007','CUSHION HAIR BRUSH','A cushioned hairbrush.'),('Mirada Pour Homme Perfume 100ml','Mirada Pour Homme Perfume 100ml is a fragrance.',"men's perfume in a 100ml size."),('Peshawari - Men','A Peshawari chappal style.\nProduct Options:\nColor: Brown','Peshawari chappals in brown.')]
  for name,source,expected in cases:
   with self.subTest(name=name):
    result=render_description(source,name)
    self.assertIn(expected,result);self.assertFalse(completeness_issues(source,name));self.assertFalse(completeness_issues(result,name))
  self.assertTrue(completeness_issues('Product Info\n901-6196\nProduct Options:\nSize: 10\nColor: Black','Bata - Bags'))
