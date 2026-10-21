import unittest
from audit804 import issues_for
from audit804_semantics import review
from reviewed804_repairs import description,product_content,numbers
from subcategory_inference_support import infer
class SemanticAuditTests(unittest.TestCase):
 def test_clothing_colour_is_not_cosmetics_and_components_not_whole_outfit(self):
  row={'name':'Avel 3 pc','Category':'Ready-to-Wear Outfits','description':'A 3-piece stitched ensemble with blush pink embroidery. PRODUCT DETAIL RTW - 3 PC Shirt: raw silk Trouser: cotton Dupatta: organza.'}
  self.assertFalse(issues_for(row));row['Category']='Blushers';self.assertTrue(issues_for(row));row['Category']='Trousers';self.assertTrue(issues_for(row))
 def test_stitching_and_single_piece_are_not_guessed(self):
  self.assertEqual(infer('Sirelle','PRODUCT DETAIL\nRTW - 1 PC\nShirt : Lawn\nColor : Beige')[0],'Shirts')
  self.assertEqual(infer('D-2168','3 Piece Stiched Collection. Stitched Shirt, Dupatta and Trouser.')[0],'Ready-to-Wear Outfits')
  self.assertTrue(issues_for({'name':'Unstitched suit','description':'An unstitched shirt and dupatta in cotton fabric.','Category':'Ready-to-Wear Outfits'}))
 def test_plain_scent_ingredient_is_not_perfume_evidence(self):
  self.assertIsNone(review('Pearl Earrings','Care: avoid perfume and water.','Perfumes & Fragrances'))
  self.assertFalse(issues_for({'name':'Chand','description':'Notes Top: Bergamot Middle: Jasmine Base: Musk. Size: 100 ml','Category':'Perfumes & Fragrances'}))
 def test_reviews_removed_only_from_known_product_footer(self):
  raw={'name':'Cotton Outfit','source_url':'https://www.shopmodest.pk/products/a','description':'Fabric Cotton. Weight 200g. Size chart 12 | 14\nFour bulk inquiry contact us at +92 555\nBased on 100 reviews\nProduct Options:\nSize: S, M'}
  result,why=description(raw,'Shop Modest',set());self.assertIn('Size chart 12 | 14',result);self.assertIn('Size: S, M',result);self.assertNotIn('+92',result);self.assertNotIn('100 reviews',result);self.assertTrue(why)
  self.assertTrue(numbers(product_content(raw))<=numbers(result));raw['source_url']='https://unrelated.example/products/a';self.assertIn('+92',product_content(raw))
 def test_copied_product_prose_drops_no_unique_numeric_specs(self):
  row={'name':'Leonie - 3 pc','description':'OUTFIT DESCRIPTION\nAzura is a refined 3-piece outfit.\nPRODUCT DETAIL\nRTW - 3 PC\nShirt: Silk 1.20m\nTrouser: Cotton 2.5m'}
  result,why=description(row,'Seran',{'azura','leonie'});self.assertNotIn('Azura',result);self.assertIn('1.20m',result);self.assertTrue(why)
  row['description']=row['description'].replace('3-piece outfit','3-piece outfit with 99 buttons');result,why=description(row,'Seran',{'azura','leonie'});self.assertEqual(result,row['description']);self.assertIsNone(why)
 def test_spice_identity_repair_retains_observed_weight_only(self):
  row={'name':'Ginger Powder','source_url':'https://shop.fardafoods.com/products/ginger-powder','description':'Discover FARDA Turmeric Powder from turmeric roots. Weight: 50gm'}
  result,why=description(row,'Farda Foods',set());self.assertIn('Ginger Powder',result);self.assertNotIn('turmeric',result.lower());self.assertEqual(numbers(result),{'50'});self.assertTrue(why)
 def test_sku_evidence_is_explicit_not_unrelated_brand(self):
  self.assertEqual(review('Noirelle','Velvet textile 2.65 meters.','Shawls','SHAWL-VELVET25-02'),[])
  self.assertIsNone(review('Noirelle','Velvet textile 2.65 meters.','Shawls','OTHER-02'))
 def test_wrong_technology_type_is_still_rejected(self):
  self.assertTrue(review('CPU Liquid Cooler','CPU cooler with fan.','Processors'))
  self.assertTrue(review('Stylus Pen for iPad','A stylus for writing.','Tablets'))

 def test_supported_word_does_not_clear_wrong_application_area(self):
  self.assertTrue(review('Lipstick Face Kit','A face kit containing rich lipstick shades.','Skin Care Bundles'))
  self.assertTrue(review('Baby Moisturizer','Moisturizer for soft baby skin.','Face Moisturisers & Creams'))
  self.assertTrue(review('Growth Boost','An intensive hair growth serum for the scalp.','Face Serums'))

 def test_jewellery_care_is_not_sold_perfume(self):
  row={'name':'Bindiya Kanta-27 (Black)','description':'Bindiya Kanta. Standard size. Jewellery Care: Keep away from water perfume and chemicals. Packed in 1 gift box.','Category':'Forehead Jewellery'}
  self.assertFalse(issues_for(row))
  row['Category']='Perfumes & Fragrances';self.assertTrue(issues_for(row))
 def test_named_removal_and_lipstick_capsules_override_incidental_words(self):
  self.assertEqual(infer('18 Colors Capsule Lipstick Set','Mini capsule lipsticks.')[0],'Lip Sets')
  self.assertEqual(infer('Hair Removal Spray','Removes unwanted hair without razors.')[0],'Hair Removal Sprays')
  self.assertEqual(infer('Milky Wax Cream','Strip hair removal system.')[0],'Depilatory Waxes')
  self.assertEqual(infer('Spiral Hair Ties (Pack of 2)','')[0],'Hair Ties & Scrunchies')
