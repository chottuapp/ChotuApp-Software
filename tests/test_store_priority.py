import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'cloud'))
from runtime import prioritize_stores
class PriorityTests(unittest.TestCase):
 def test_small_first_unknown_stable_and_inputs_preserved(self):
  sites=[{'name':n,'url':'https://example.com'} for n in ['LAAM','Stylo','Zero Lifestyle','Skin Factor','Islamabad Tea']]
  result=prioritize_stores(sites)
  self.assertEqual([s['name'] for s in result],['Skin Factor','Islamabad Tea','Stylo','LAAM','Zero Lifestyle'])
  self.assertEqual(sites[0]['name'],'LAAM')
  self.assertEqual({id(s) for s in sites},{id(s) for s in result})
