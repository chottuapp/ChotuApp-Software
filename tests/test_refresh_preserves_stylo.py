import unittest
from fresh804_dispatch import chain_ids,lane_prefix,planned_groups
from audit804_delivery import refresh_source_ids
class RefreshTests(unittest.TestCase):
 def runs(self):
  return [{'databaseId':1,'displayTitle':'Cloud group audit804-old-solo-5'},
          {'databaseId':2,'displayTitle':'Automatic continuation of 1'},
          {'databaseId':3,'displayTitle':'Automatic continuation of 2'},
          {'databaseId':4,'displayTitle':'Cloud group audit804-old-refresh20261027-abcd1234-solo-1'},
          {'databaseId':5,'displayTitle':'Automatic continuation of 4'},
          {'databaseId':6,'displayTitle':'Cloud group audit804-old-solo-1'}]
 def test_preserved_stylo_chain_never_enters_stop_selection(self):
  runs=self.runs();owned=chain_ids(runs,{'4'});preserved=chain_ids(runs,{'2'})
  self.assertEqual(preserved,{'2','3'})
  self.assertEqual({str(r['databaseId']) for r in runs if str(r['databaseId']) not in owned|preserved},{'1','6'})
 def test_fresh_plan_excludes_stylo_and_reserves_unique_lanes(self):
  request={'campaign_id':'old','runner_plan':'solo','refresh_generation':'refresh20261027-abcd1234','skip_fresh_stores':['Stylo'],'maximum_stores_per_runner':1}
  self.assertEqual(lane_prefix(request),'audit804-old-refresh20261027-abcd1234-solo-')
  self.assertEqual(planned_groups([{'name':'Stylo'},{'name':'Bata'},{'name':'Hello Maali'}],request),[[{'name':'Bata'}],[{'name':'Hello Maali'}]])
 def test_delivery_accepts_new_generation_and_current_stylo_not_old_other_files(self):
  fresh,carry=refresh_source_ids(self.runs(),'refresh20261027-abcd1234','old',['2'])
  self.assertEqual(fresh,{'4','5'});self.assertEqual(carry,{'2','3'})
  self.assertNotIn('6',fresh|carry)
