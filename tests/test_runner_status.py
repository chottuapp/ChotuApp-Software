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

class EarlyStatusTests(unittest.TestCase):
 def test_live_status_is_published_before_slow_snapshot_collection(self):
  import copy,json,os
  from pathlib import Path
  from unittest.mock import patch
  import runner_status
  campaign=json.loads((Path(runner_status.__file__).parent/'drive-sync-release.json').read_text())['dispatcher'];events=[]
  run={'databaseId':1,'displayTitle':'Cloud group audit804-'+campaign+'-1','status':'in_progress','conclusion':''}
  def gh(*args):
   if args[:2]==('run','list'):return json.dumps([run])
   raise RuntimeError('No optional report')
  def publish(report,**kwargs):events.append(('publish',copy.deepcopy(report)))
  def inspect(run,now):
   self.assertEqual(events[0][0],'publish');self.assertTrue(events[0][1]['runs'][0]['snapshot_pending']);return dict(run,stores={'A':'running'})
  with patch.dict(os.environ,{'GITHUB_RUN_ID':'1'}),patch.object(runner_status,'gh',gh),patch.object(runner_status,'publish',publish),patch.object(runner_status,'inspect_run',inspect):runner_status.main()
  self.assertEqual(events[-1][1]['fresh_stores'],{'A':'running'});self.assertEqual(events[-1][1]['active_queued'],1)

class OverviewTests(unittest.TestCase):
 def test_export_correction_delivery_and_stale_progress_are_distinct(self):
  from runner_status import store_overview
  report={'runs':[{'databaseId':1,'status':'in_progress','stores':{'A':'done','B':'done','C':'running'},'snapshot_stale':True}]}
  drive={'audit804_results':{'A':{'campaign_id':'new','status':'hold','findings_count':1,'findings':[{'issues':['Needs review']}] }},'uploaded':{'B':{'campaign_id':'new','audit804':{'status':'pass'},'verified_utc':'now'}}}
  result=store_overview(report,drive,'new');self.assertEqual(result['A']['state'],'correction_queue');self.assertEqual(result['B']['state'],'drive_verified');self.assertEqual(result['C']['state'],'status_unconfirmed_stale_snapshot')
