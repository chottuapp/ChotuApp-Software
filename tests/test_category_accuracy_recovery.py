import unittest
from sold_object_category_support import source_object
from audit804_semantics import review
from product_description_support import render_description,numeric_facts,retained_text

class CategoryAccuracyRecovery(unittest.TestCase):
 def test_corroborated_product_overrides_bad_merchant_metadata(self):
  cases=[('Miss Rose 2 in 1 Eyebrow & Eyeliner Pencil','A dual-purpose pencil for brows and eyeliner.','Lipstick','Lips > Lipstick','Eyebrow & Eyeliner Pencils'),
   ('RHD EYESHADOW MAGICAL DAZZLING','Magical Dazzling Eye Shadow Palette.','Face Serum','','Eyeshadow Palettes'),
   ('Girls Patent Lace-Up Boots','Patent boots. Upper: polyurethane. Sole: rubber. Metallic studs.','','Girls > Shoes > Sneakers','Boots'),
   ('Women 2 Pcs Suit','Shirt+Trouser. Matching trouser. Cotton lawn.','Shirts','','Clothing Sets')]
  for name,body,kind,path,expected in cases:
   with self.subTest(name=name):
    self.assertEqual(source_object(name,body,kind,path)[0],expected)
    self.assertEqual(review(name,body,expected),[])
 def test_components_and_styling_do_not_replace_the_whole_object(self):
  for title,body,label in [('Boys Shacket','Cotton shacket, pair with jeans.','Shackets'),('Wide Leg Sweatpants','Sweatpants paired with a hoodie.','Sweatpants'),('Baby Moisturizer Soap','Baby soap with moisturizing ingredients.','Baby Soaps')]:
   self.assertEqual(source_object(title,body)[0],label)
   self.assertEqual(review(title,body,label),[])
 def test_formatted_component_fields_preserve_optional_exclusions(self):
  body='✦ Fabric & Fit\n• Cut: Short Shirt\n• Dupatta: Not Included\n• Trouser: Zuri Shalwar Included'
  self.assertEqual(review('TROPICAL',body,'Clothing Sets'),[])
  self.assertNotEqual(review('TROPICAL',body.replace('Zuri Shalwar Included','Not Included'),'Clothing Sets'),[])
 def test_nested_numbered_lists_are_stable_and_keep_measurements(self):
  body='1. Easy to cut 300cm paper.\n2. Multiple themes.\n3. Paper material.\n\nFabric & Fit\n• Warm Tips.\n• 1. Colours vary.\n• 2. Allow size errors.\n• 3. 1mm=0.039inch.'
  first=render_description(retained_text(body),'Drawing Roll','Drawing Paper');second=render_description(first,'Drawing Roll','Drawing Paper')
  self.assertEqual(numeric_facts(body),numeric_facts(first));self.assertEqual(numeric_facts(first),numeric_facts(second));self.assertIn('300cm',second);self.assertIn('1mm=0.039inch',second)
 def test_actual_stationery_and_paint_contents_are_not_laptops_or_cosmetics(self):
  cases=[('Sanrio Gift Set With Mini Fan','A lined pages notebook. Sticky Note. Set of 4 gel pen. Mini fan.','Stationery Gift Sets'),('Egg Shell Crafts Gift Set With Paints','Easter painted eggs x5. Paint Brush x2. Coloring Card x8.','Painting & Craft Sets')]
  for title,body,label in cases:
   self.assertEqual(source_object(title,body)[0],label);self.assertEqual(review(title,body,label),[])
 def test_explicit_face_palette_is_not_a_single_blusher(self):
  title='Cheek Blush and Highlighter Palette';body='Palette contains blush and highlighter.'
  self.assertEqual(source_object(title,body)[0],'Face Palettes');self.assertEqual(review(title,body,'Face Palettes'),[])
 def test_other_product_mentions_do_not_override_remover_or_skincare(self):
  self.assertNotEqual((source_object('Makeup Remover','This remover removes lipstick and mascara.') or [None])[0],'Lipsticks')
  self.assertNotEqual((source_object('Face Cream','Mix this cream with lipstick.') or [None])[0],'Lipsticks')
 def test_toy_character_and_supplied_controls_do_not_become_computer_devices(self):
  cases=[('360 Rotate Remote Control Robot Dog with Light And Sound','Remote control with buttons.','Robot Toys'),('Minnie Mouse Heart Sunglasses','Heart shaped sunglasses.','Sunglasses'),('Push Pop It - Mickey Mouse','Silicone bubble popping toy.','Fidget Toys'),('32-Key Magic Phone With LCD Drawing Board','Draw using a stylus.','Drawing Boards'),('Snail LED Desk Lamp','USB powered, compatible with a laptop.','Desk Lamps')]
  for title,body,label in cases:
   with self.subTest(title=title):self.assertEqual(source_object(title,body)[0],label);self.assertEqual(review(title,body,label),[])
 def test_printed_design_and_costume_jewellery_are_not_toys_or_costumes(self):
  self.assertNotEqual((source_object('Piano Print T-Shirt','Cotton shirt with a piano print.','shirt') or [None])[0],'Pianos')
  self.assertNotEqual((source_object('T-Shirt with a Piano Print','Cotton shirt.','shirt') or [None])[0],'Pianos')
  self.assertNotEqual((source_object('Costume Jewellery Necklace Set','Necklace with matching earrings.') or [None])[0],'Costumes')
 def test_wrong_bundle_copy_is_incomplete_but_comparisons_are_allowed(self):
  from product_description_support import completeness_issues
  self.assertTrue(completeness_issues('Xperience the Honey Glow Hair Trio! This luxurious set offers three products.','Hair Oil 20ml'))
  self.assertFalse(completeness_issues('Hair oil for damaged hair. If you tried the hair mask, this oil is a follow-up treatment.','Hair Oil 70ml'))
  self.assertFalse(completeness_issues('Xperience the Honey Glow Hair Trio! This luxurious set offers three products.','Honey Glow Hair Trio'))
 def test_supplied_necklace_or_controller_does_not_replace_play_set_or_vehicle(self):
  for title,body,label in [('Ride On Car','Ride-on vehicle supplied with a remote controller.','Ride-On Vehicles'),('Fashion Beauty Set','A toy collection. Set contents: crown, necklace, brush, comb.','Beauty Play Sets')]:
   self.assertEqual(source_object(title,body)[0],label);self.assertEqual(review(title,body,label),[])
