import json,unittest
from pathlib import Path
from group_fetch import groups
class FreshTests(unittest.TestCase):
 def test_all_29_cloud_stores_once_at_most_three_per_runner(self):
  root=Path(__file__).resolve().parents[1];sites=json.loads((root/'cloud/fetch-update-release.json').read_text())['fresh_stores'];sites=sites[:29];cloud=list(sites);plan=groups(cloud)
  self.assertEqual(len(plan),(len(sites)+2)//3);self.assertEqual(sum(map(len,plan)),len(sites));self.assertTrue(all(len(g)<=3 for g in plan));self.assertEqual(len({s['name'] for g in plan for s in g}),len(sites));self.assertIn('LAAM',{s['name'] for g in plan for s in g})

 def test_new_batch_excludes_khaadi_and_keeps_three_store_limit(self):
  from fresh804_dispatch import selected_sites
  sites=json.loads((Path(__file__).resolve().parents[1]/'cloud/fetch-update-release.json').read_text())['fresh_stores'][:29]
  selected=selected_sites(sites,{'excluded_stores':['Khaadi'],'khaadi_fresh_enabled':False})
  self.assertEqual(len(selected),len(sites)-1);self.assertNotIn('Khaadi',{s['name'] for s in selected})
  self.assertEqual(len(groups(selected)),(len(selected)+2)//3);self.assertTrue(all(len(group)<=3 for group in groups(selected)))

 def test_expanded_registry_solo_plan_preserves_completed_and_excludes_paused(self):
  from fresh804_dispatch import selected_sites,planned_groups
  root=Path(__file__).resolve().parents[1]
  registry=json.loads((root/'cloud/fetch-update-release.json').read_text())['fresh_stores']
  request=json.loads((root/'cloud/audit804-release.json').read_text())
  sites=selected_sites(registry,request);self.assertEqual(len(sites),31)
  plan=planned_groups(sites,request);self.assertEqual(len(plan),len(sites)-len([v for v in sites if v['name'] in request.get('completed_stores',[])]));self.assertTrue(all(len(g)==1 for g in plan))
  self.assertTrue({'Stylo','Bata','Aerosoft Studio','Servis','Ndure'}<={g[0]['name'] for g in plan})
