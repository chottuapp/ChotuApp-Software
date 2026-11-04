import unittest
from catalogue_object_rules import classify,audit
from audit804_semantics import review
class SourceGarmentRecovery(unittest.TestCase):
 def test_explicit_contents_recover_whole_outfit_not_one_component(self):
  cases=[('Street Stomper Set','A shirt layered under a cream knit vest, paired with matching jogger pants.'),('Cocoa Pup Knit Set','A knit cardigan paired with matching ribbed trousers.'),('Floral Chic','A two-piece outfit with a shirt and comfortable plazo.'),('Mustard Glam','FABRIC: ORGANZA\nDUPATA: NET\nGHARARA: 4yrd EMB'),('Range One','Fabric: cotton\n* \u2060 Dupatta: net\n* \u2060 Trouser: silk')]
  for name,body in cases:
   row={'name':name,'description':body}
   for store in ['Nayab Fashion','Babysaurus','Deflexxi']:
    with self.subTest(name=name,store=store):
     self.assertEqual(classify(row,store)[0],'Clothing Sets');self.assertEqual(review(name,body,'Clothing Sets'),[])
 def test_clear_source_names_do_not_become_cosmetics_or_an_accessory(self):
  for name,label in [('Bunny Cable Knit Romper','Rompers'),('Caramel Frill Tracksuit','Tracksuits')]:
   self.assertEqual(classify({'name':name,'description':'Source garment details.'},'Babysaurus')[0],label);self.assertEqual(review(name,'Source garment details.',label),[])
  self.assertTrue(review('3 Piece Shirt Trouser Outfit','This outfit includes shirt, trousers and dupatta.','Shirts'))
 def test_merchant_unstitched_fact_is_purpose_evidence_not_a_guessed_garment_shape(self):
  source={'name':'Royal Range','description':'Fabric: chiffon; length 60 inches.','source_url':'https://nayabfashion.com.pk/product/royal/','analysis_note':'Public WooCommerce Store API taxonomy: best sellers > Explore Shop > unstitched > Video Product; API order is not verified website display order.'}
  label=classify(source,'Nayab Fashion');self.assertEqual(label[0],'Unstitched Fabric');self.assertEqual(audit(dict(source,Category=label[0]),source),[])
  self.assertIsNone(audit(dict(source,Category=label[0]),dict(source,analysis_note='')))
  self.assertIsNone(classify(dict(source,analysis_note='Best sellers'), 'Nayab Fashion'))
  self.assertIsNone(classify(dict(source,description='Fully stitched silk outfit.'),'Nayab Fashion'))
 def test_size_charts_and_store_name_alone_do_not_prove_a_set(self):
  row={'name':'Single shirt','description':'SIZE CHART Shirt\nSIZE CHART Trouser\nOne shirt only.'}
  value=classify(row,'Deflexxi');self.assertTrue(value is None or value[0]!='Clothing Sets')
  self.assertIsNone(classify({'name':'Royal Plum','description':'New arrival, premium quality.'},'Nayab Fashion'))
 def test_excluded_component_cannot_be_promoted_into_a_supplied_set(self):
  row={'name':'Range One','description':'Shirt: cotton\nTrouser: silk, not included.'}
  value=classify(row,'Nayab Fashion');self.assertTrue(value is None or value[0]!='Clothing Sets');self.assertNotEqual(review(row['name'],row['description'],'Clothing Sets'),[])
 def test_child_party_set_and_matching_bottoms_keep_the_complete_outfit(self):
  for name,body in [('Party Parade 3 Piece Set','A festive three-piece party set. Your little one can dress up for weddings.'),('Luxe Glory','A 2-piece suit features a shirt and matching bottoms.')]:
   value=classify({'name':name,'description':body},'Babysaurus');self.assertEqual(value[0],'Clothing Sets');self.assertEqual(review(name,body,value[0]),[])
