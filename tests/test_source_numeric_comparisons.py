import unittest
from audit804 import plain,tokens,issues_for
from audit804_semantics import text
from hold804_repairs import category,description
class SourceComparisonTests(unittest.TestCase):
 def test_numeric_inequalities_are_not_html(self):
  raw='Distortion <0.1%; 984FT transmission at 2.4GHz; 48kHz / 24bit; SNR >90dB.'
  for normalized in (plain(raw),text(raw)):
   for fact in ('0.1','984','2.4','48','24','90'):self.assertIn(fact,normalized)
  self.assertEqual(tokens(raw),tokens('<p>'+raw+'</p>'))
 def test_real_missing_numeric_fact_still_fails(self):
  source=dict(name='Wireless Microphone',description='Microphone sampling rate 48kHz and SNR >90dB.')
  output=dict(source,description='Wireless microphone with sampling rate 48kHz.',Category='Microphones')
  self.assertIn('Description lost source numeric facts',issues_for(output,source))
 def test_makeup_blender_and_bedding_are_specific_objects(self):
  self.assertEqual(category(dict(name='SILICONE BLENDER',description='A silicon makeup sponge.'),'Junaid Jamshed')[0],'Makeup Sponges')
  self.assertEqual(category(dict(name='Dyed Duvet Cover',description='1 Quilt Cover and 2 Pillowcases.'),'Gul Ahmed')[0],'Duvet Cover Sets')
 def test_sparse_towel_preserves_size_without_invented_composition(self):
  row=dict(name='Bath Sheet - 2508',description='LUXURY - 100x150cm - Bath Sheet')
  fixed,reason=description(row,'Zellbury');self.assertIn(row['description'],fixed);self.assertNotIn('cotton',fixed.lower());self.assertTrue(reason)
