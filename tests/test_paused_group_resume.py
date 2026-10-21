import copy,json,unittest
from pathlib import Path
from paused_group_resume import targets
class PausedGroupTests(unittest.TestCase):
 def request(self):return json.loads((Path(__file__).resolve().parents[1]/'cloud/paused-group-request.json').read_text())
 def test_distinct_campaign_lanes_keep_source_identity(self):
  selected=targets(self.request());self.assertEqual(len(selected),2);self.assertNotEqual(selected[0][1],selected[1][1]);self.assertTrue(all(group.startswith('audit804-fresh804-') for _,group in selected))
 def test_other_stores_or_parent_rejected(self):
  r=self.request();r['stores'][0]['name']='Other'
  with self.assertRaises(ValueError):targets(r)
  r=self.request();r['parent_group']='old-unrelated'
  with self.assertRaises(ValueError):targets(r)
