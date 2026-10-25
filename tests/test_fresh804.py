import json,unittest
from pathlib import Path
from group_fetch import groups
class FreshTests(unittest.TestCase):
 def test_all_29_cloud_stores_once_at_most_three_per_runner(self):
  root=Path(__file__).resolve().parents[1];sites=json.loads((root/'cloud/fetch-update-release.json').read_text())['fresh_stores'];cloud=list(sites);plan=groups(cloud)
  self.assertEqual(len(plan),10);self.assertEqual(sum(map(len,plan)),29);self.assertTrue(all(len(g)<=3 for g in plan));self.assertEqual(len({s['name'] for g in plan for s in g}),29);self.assertIn('LAAM',{s['name'] for g in plan for s in g})

 def test_new_batch_excludes_khaadi_and_keeps_three_store_limit(self):
  from fresh804_dispatch import selected_sites
  sites=json.loads((Path(__file__).resolve().parents[1]/'cloud/fetch-update-release.json').read_text())['fresh_stores']
  selected=selected_sites(sites,{'excluded_stores':['Khaadi'],'khaadi_fresh_enabled':False})
  self.assertEqual(len(selected),28);self.assertNotIn('Khaadi',{s['name'] for s in selected})
  self.assertEqual(len(groups(selected)),10);self.assertTrue(all(len(group)<=3 for group in groups(selected)))
