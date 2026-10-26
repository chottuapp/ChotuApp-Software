import re,unittest
from description_readability import format_description,issues
class ReadabilityTests(unittest.TestCase):
 def test_long_description_is_split_without_losing_a_word_or_number(self):
  body=' '.join(['This cotton shirt has a regular fit and a printed front with 3 buttons.']*15)
  after=format_description(body)
  self.assertIn('\n\n',after);self.assertEqual(re.findall(r'\S+',body),re.findall(r'\S+',after));self.assertTrue(issues(body));self.assertFalse(issues(after))
 def test_lists_measurements_and_warnings_stay_intact(self):
  body='Details:\n- Cotton 80%, polyester 20%.\n- Size: 51x66+23cm.\n\nCare:\nDo not bleach.'
  self.assertEqual(format_description(body),body)
