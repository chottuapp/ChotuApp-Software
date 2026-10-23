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

class WorkbookReviewRegressionTests(unittest.TestCase):
 def test_all_row_audit_preserves_note_heading_lines(self):
  row={'name':'Lady Prive','description':'Top\nCitrus, Coffee\nHeart\nRose\nBase\nVanilla','Category':'Perfumes & Fragrances'}
  self.assertEqual(issues_for(row),[])
 def test_source_vendor_type_label_is_not_rejected_as_a_brand(self):
  row={'name':'Beige Low Cut Unisex Socks','description':'Beige low cut unisex socks. Colour: Beige.','Category':'Socks','brand':'Socks'}
  self.assertEqual(issues_for(row),[])
  row.update(name='Opaque collection',description='An opaque collection without any product type.',Category='Vendor Brand',brand='Vendor Brand')
  self.assertIn('Brand name used as product Category',issues_for(row))

class FabricEvidenceTests(unittest.TestCase):
 def test_measured_fabric_cut_is_supported_without_marketing_label(self):
  row={'name':'Moonlit','description':'Length: 4.25 Meters\nWidth: 56 inches\nFabric: Cotton','Category':'Unstitched Fabric'}
  self.assertEqual(issues_for(row),[])
  row['description']='Cotton fabric for a beautiful look.'
  self.assertTrue(issues_for(row))
 def test_verified_breadcrumb_and_length_support_unstitched_suit(self):
  row={'name':'Premium Cotton Suit','description':'Shirt & Trouser 4.5M. Fabric: Cotton.','Category':'Unstitched Suits','website_category_status':'verified_product_breadcrumb','website_category_path':"Man > Men's Unstitched"}
  self.assertEqual(issues_for(row),[])
  row['website_category_status']='unverified'
  self.assertTrue(issues_for(row))

class OriginalStorePurposeTests(unittest.TestCase):
 def test_garment_and_fragrance_names_have_specific_purpose(self):
  self.assertEqual(infer('Embroidered Bedford Peshwas','Regular Fit Peshwas')[0],'Peshwas Dresses')
  self.assertEqual(infer('Printed Cambric Angrakha','Regular Fit Angrakha')[0],'Angrakhas')
  self.assertEqual(infer('Gift set','This set contains Fall For Her 100ml and Fall For Him 100ml, a union of fragrance.')[0],'Fragrance Sets')
 def test_fabric_length_and_contents_are_independent_evidence(self):
  self.assertEqual(review('Premium Suit','Shirt & Trouser 4.5M. Fabric: Cotton.','Suit Fabric Sets'),[])
  self.assertEqual(review('Cotton Suit','Kameez collar neckline. Shalwar included.','Kameez Shalwar Sets'),[])
  self.assertIsNone(review('Opaque Suit','No contents supplied','Suit Fabric Sets'))

class CompleteDescriptionsTests(unittest.TestCase):
 def test_complete_skin_description_is_not_relabeled_as_concerns(self):
  row={'name':'Gentle Cleanser','description':'A gentle cleanser. Ingredients: Oat extract. Directions: Rinse thoroughly.'}
  self.assertEqual(description(row,'Skin Factor',set()),(row['description'],None))
