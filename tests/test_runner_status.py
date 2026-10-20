import unittest,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'cloud')]
from runner_status import select_runs,parse_snapshot
class StatusTests(unittest.TestCase):
 def test_newest_continuation_wins_over_parent_old_failure(self):
  runs=[{'databaseId':3,'displayTitle':'Automatic continuation of 2','status':'in_progress'},{'databaseId':2,'displayTitle':'Automatic continuation of 1','status':'completed'},{'databaseId':1,'displayTitle':'Cloud group solo-laam','status':'completed'}]
  selected=select_runs(runs);self.assertEqual(len(selected),1);self.assertEqual(selected[0]['databaseId'],3);self.assertEqual(selected[0]['lane'],'solo-laam')
 def test_snapshot_states_are_not_confused_with_stage_text(self):
  updated,stores=parse_snapshot('Updated (UTC): 2026-10-20T18:00:00+00:00\nLAAM: running\n  Stage: Idle\nSapphire: failed')
  self.assertEqual(stores,{'LAAM':'running','Sapphire':'failed'});self.assertTrue(updated)
