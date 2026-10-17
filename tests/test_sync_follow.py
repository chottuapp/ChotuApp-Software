import json,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from cloud_sync_windows import continuation_allowed,next_continuation
class FollowTests(unittest.TestCase):
 def test_wait_only_for_authorized_budget_completion(self):
  with tempfile.TemporaryDirectory() as tmp:
   folder=Path(tmp);sync=SimpleNamespace(folder=folder,run='38970499270')
   for reason,expected in [('time_budget',True),('stop_requested',False),('completed_or_source_failure',False)]:
    (folder/'run-summary.json').write_text(json.dumps({'status':'incomplete','checkpoint':'saved','stop_reason':reason}));self.assertEqual(continuation_allowed(sync),expected)
   (folder/'run-summary.json').write_text(json.dumps({'status':'incomplete','checkpoint':'not saved','stop_reason':'time_budget'}));self.assertFalse(continuation_allowed(sync))
 def test_follows_only_matching_numeric_child(self):
  sync=SimpleNamespace(repo='owner/repo',run='123',call=lambda args:json.dumps([{'displayTitle':'Automatic continuation of 456','databaseId':1},{'displayTitle':'Automatic continuation of 123','databaseId':789}]))
  self.assertEqual(next_continuation(sync),'789')
if __name__=='__main__':unittest.main()
