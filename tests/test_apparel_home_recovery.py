import unittest
from hold804_repairs import category,description
from audit804 import issues_for
class ApparelHomeRecoveryTests(unittest.TestCase):
 def check(self,store,name,body,label):
  row={'name':name,'description':body,'source_url':'https://example.invalid/products/item'}
  result=category(row,store);self.assertEqual(result[0],label)
  corrected=dict(row,Category=label)
  self.assertEqual(issues_for(corrected),[])
  self.assertEqual(description(row,store)[0],body)
 def test_unstitched_fabric_is_not_a_skin_gift_bundle(self):
  self.check('Gul Ahmed','Mega Super Unstitched Fabric Blended with Gift Box','Premium blended unstitched fabric. 4.5 MTR suit width 55 in with gift box.','Unstitched Fabric')
 def test_table_linen_set_keeps_each_component_and_measurement(self):
  self.check('Gul Ahmed','AW23 Checks Placemat and Runner Set','Set includes 1 table runner 36x161 cm, 4 placemats 34x47 cm and 4 napkins 45x45 cm.','Table Linen Sets')
 def test_towel_set_does_not_become_clothing(self):
  self.check('Gul Ahmed','Blue Zero Twist 4pc Set','Zero Twist Towel. Each pack contains 4 face towels, 30x30 cm.','Towel Sets')
 def test_clothing_styling_advice_does_not_change_tank_top_to_jeans(self):
  self.check('Stylo','White Solid Tank Top LC0043','A sleeveless tank top with lace trim. Layer under a jacket or wear with jeans.','Tank Tops')
 def test_writing_tablet_is_not_its_stylus_accessory(self):
  self.check('Stylo','LCD Panel For Kids T7002118','An LCD writing tablet supplied with a stylus for drawing and writing.','LCD Writing Tablets')
 def test_pretend_doctor_set_keeps_all_contents(self):
  self.check('Stylo','Doctor Set For Kids T7009512','Toy medical set with 1 stethoscope, glasses, thermometer, syringe and prescription pad for pretend play.','Toy Doctor Sets')
 def test_undefined_item_is_not_assigned_from_store_brand(self):
  self.assertIsNone(category({'name':'Unidentified Collection 123','description':'Unknown material.'},'Gul Ahmed'))

 def test_wallet_keychain_pack_does_not_require_or_invent_a_belt(self):
  self.check('Stylo','Gift Pack For Men P7409902','A leather gift set comprising a wallet and matching keychain. Includes: Wallet, Keychain.','Mens Accessory Gift Sets')
