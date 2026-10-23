import os,sys,sqlite3,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'cloud'))
from continuation_policy import integer,progress_token,summary_fields
from auto_continue import eligible
class PolicyTests(unittest.TestCase):
 def test_chain_caps_stalls_and_terminal_failures(self):
  run={'id':123,'event':'workflow_dispatch','head_branch':'main','head_repository':{'full_name':'o/r'},'conclusion':'failure'}
  s={'status':'incomplete','checkpoint':'saved','stop_reason':'time_budget','auto_continue_limit':4,'continuation_index':3,'stores':[{'status':'pending'}]}
  self.assertTrue(eligible(run,'o/r',s,'',True))
  for changes in ({'continuation_index':4},{'stalled_runs':2},{'auto_continue_limit':49},{'stop_reason':'manual_stop'},{'stores':[{'status':'failed'}]}):
   self.assertFalse(eligible(run,'o/r',dict(s,**changes),'',True),changes)
  s.update(stop_reason='source_cooldown',stores=[{'status':'source_paused','retry_after_epoch':10**12}]);self.assertFalse(eligible(run,'o/r',s,'',True))
 def test_progress_uses_durable_responses_and_stall_counter(self):
  with tempfile.TemporaryDirectory() as tmp:
   state={'id':'a','sites':[{'status':'pending'}]};first=progress_token(state,tmp)
   path=Path(tmp)/'a'/'0';path.mkdir(parents=True)
   with sqlite3.connect(path/'api.sqlite3') as db:db.execute('CREATE TABLE responses (value TEXT)');db.execute("INSERT INTO responses VALUES ('saved')")
   second=progress_token(state,tmp);self.assertNotEqual(first,second)
   with patch.dict(os.environ,{'CLOUD_PREVIOUS_PROGRESS':second,'CLOUD_STALLED_RUNS':'1','CLOUD_AUTO_CONTINUE_LIMIT':'4','CLOUD_CONTINUATION_INDEX':'2'}):
    s=summary_fields(state,tmp);self.assertEqual(s['stalled_runs'],2);self.assertEqual(s['continuation_index'],2)
 def test_invalid_counters(self):
  for value in ('-1','49','oops',None):self.assertEqual(integer(value),0)
if __name__=='__main__':unittest.main()

class LocalFollowTests(unittest.TestCase):
 def test_local_follow_obeys_budget_and_manual_stop(self):
  from types import SimpleNamespace
  from cloud_sync_windows import continuation_allowed
  import json
  with tempfile.TemporaryDirectory() as tmp:
   sync=SimpleNamespace(folder=Path(tmp),run='123');p=sync.folder/'run-summary.json'
   summary={'checkpoint':'saved','status':'incomplete','auto_continue_limit':4,'continuation_index':2,'stop_reason':'time_budget'}
   p.write_text(json.dumps(summary));self.assertTrue(continuation_allowed(sync))
   for changes in ({'continuation_index':4},{'stalled_runs':2},{'stop_reason':'stop_requested'}):
    p.write_text(json.dumps(dict(summary,**changes)));self.assertFalse(continuation_allowed(sync))
