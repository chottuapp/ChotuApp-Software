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
  self.assertEqual(len(selected),len([s for s in sites if s['name'] not in {'LAAM','Khaadi','Bachaa Party','Gift4U','Xcessories Hub'}]));self.assertNotIn('Khaadi',{s['name'] for s in selected})
  self.assertEqual(len(groups(selected)),(len(selected)+2)//3);self.assertTrue(all(len(group)<=3 for group in groups(selected)))

 def test_expanded_registry_solo_plan_preserves_completed_and_excludes_paused(self):
  from fresh804_dispatch import selected_sites,planned_groups
  root=Path(__file__).resolve().parents[1]
  registry=json.loads((root/'cloud/fetch-update-release.json').read_text())['fresh_stores']
  request=json.loads((root/'cloud/audit804-release.json').read_text())
  sites=selected_sites(registry,request);self.assertEqual(len(sites),sum(r.get('enabled',True) is not False and r['name'] not in set(request['excluded_stores'])|{'Gift4U','Xcessories Hub','LAAM','Khaadi','Bachaa Party'} for r in registry))
  remaining=len(sites)-len([v for v in sites if v['name'] in set(request.get('completed_stores',[]))|set(request.get('skip_fresh_stores',[]))]);size=request['maximum_stores_per_runner'];plan=planned_groups(sites,request);self.assertEqual(len(plan),(remaining+size-1)//size);self.assertTrue(all(1<=len(g)<=size for g in plan))
  self.assertTrue(({'Stylo','Bata','Aerosoft Studio','Servis','Ndure'}-set(request.get('completed_stores',[]))-set(request.get('skip_fresh_stores',[])))<={site['name'] for g in plan for site in g})

 def test_two_store_plan_does_not_drop_or_repeat_odd_last_store(self):
  from fresh804_dispatch import planned_groups
  sites=[{'name':str(i)} for i in range(5)]
  plan=planned_groups(sites,{'maximum_stores_per_runner':2})
  self.assertEqual([len(g) for g in plan],[2,2,1]);self.assertEqual([s for g in plan for s in g],sites)
