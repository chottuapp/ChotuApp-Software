import json,unittest
from pathlib import Path
from group_fetch import groups
class FreshTests(unittest.TestCase):
 def test_all_29_cloud_stores_once_at_most_three_per_runner(self):
  root=Path(__file__).resolve().parents[1];sites=json.loads((root/'cloud/fetch-update-release.json').read_text())['fresh_stores'];cloud=list(sites);plan=groups(cloud)
  self.assertEqual(len(plan),10);self.assertEqual(sum(map(len,plan)),29);self.assertTrue(all(len(g)<=3 for g in plan));self.assertEqual(len({s['name'] for g in plan for s in g}),29);self.assertIn('LAAM',{s['name'] for g in plan for s in g})
