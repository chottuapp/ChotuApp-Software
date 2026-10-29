import unittest
from xcessories_purpose_support import classify
from audit804_semantics import review
class SoldObjectTests(unittest.TestCase):
 def kind(self,name,description='Source product specifications and care.'):return classify(dict(name=name,description=description))
 def test_accessory_does_not_become_compatible_device(self):
  self.assertEqual(self.kind('Apple iPhone 18 Pro Clear Case with MagSafe')[0],'Phone Cases')
  self.assertEqual(self.kind('Silicone Adjustable Strap for Google Fitbit Air')[0],'Watch Straps')
  self.assertEqual(self.kind('Samsung Galaxy Watch 8 Protective Case')[0],'Watch Cases')
 def test_charging_case_in_microphone_set_is_not_phone_case(self):
  self.assertEqual(self.kind('DJI Mic Mini 2 (2 TX + 1 Universal Receiver RX + Charging Case)')[0],'Wireless Microphone Sets')
 def test_watch_with_included_strap_remains_watch(self):
  self.assertEqual(self.kind('Aurafit ELLA 4 AM35 Amoled Smartwatch with Dual Strap')[0],'Smartwatches')
 def test_card_reader_not_memory_card(self):
  self.assertEqual(self.kind('HOCO UA25 Card Reader Type-C to SD + TF')[0],'Memory Card Readers')
 def test_ambiguous_model_has_no_invented_purpose(self):
  self.assertIsNone(self.kind('Mystery Z-900 Black','Black finish. Material not specified.'))
 def test_model_requires_explicit_source_purpose(self):
  self.assertIsNone(self.kind('DJI Osmo Mobile 8P','Source description unavailable.'))
  self.assertEqual(self.kind('DJI Osmo Mobile 8P','Mobile stabilizer with 3-axis stabilization.')[0],'Phone Gimbals')
 def test_independent_review_checks_type_against_source(self):
  self.assertEqual(review('Apple iPhone 18 Pro Clear Case with MagSafe','A protective phone case.','Phone Cases'),[])
  self.assertNotEqual(review('Apple iPhone 18 Pro Clear Case with MagSafe','A protective phone case.','Earbuds'),[])

 def test_ipad_accessories_before_tablet_model_match(self):
  self.assertEqual(self.kind('JOYROOM Active Capacitive Stylus Pen for iPad')[0],'Stylus Pens')
  self.assertEqual(self.kind('Youksh iPad Tempered Glass Protector For iPad Air 11')[0],'Tablet Screen Protectors')
  self.assertEqual(self.kind('Choetech Wireless Keyboard For IPad Pro 12.9')[0],'Keyboards')
