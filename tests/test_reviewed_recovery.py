import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'cloud'))
import recover_reviewed_fetches as recovery
class ReviewedRecoveryTests(unittest.TestCase):
 def setUp(self):
  self.run={'id':1,'status':'completed','conclusion':'failure','event':'workflow_dispatch','head_branch':'main','head_repository':{'full_name':recovery.REPO},'head_sha':'old'}
  self.summary={'runner_group':'solo-sapphire','status':'incomplete','checkpoint':'saved','auto_continue_limit':6,'continuation_index':0,'stores':[{'name':'Sapphire','status':'failed'}],'stop_reason':'source_failure'}
 def test_new_tested_release_can_retry_saved_parser_failure_once(self):
  self.assertTrue(recovery.may_recover(self.run,self.summary,'new'));self.assertFalse(recovery.may_recover(self.run,self.summary,'old'))
 def test_manual_stops_success_missing_checkpoint_and_exhausted_budget_do_not_restart(self):
  for key,value in [('stop_reason','stop_requested'),('stop_reason','time_budget'),('stop_reason','source_cooldown'),('status','complete'),('checkpoint','missing'),('continuation_index',6),('stalled_runs',2)]:
   with self.subTest(key=key):self.assertFalse(recovery.may_recover(self.run,dict(self.summary,**{key:value}),'new'))
  for conclusion in ('success','cancelled'):self.assertFalse(recovery.may_recover(dict(self.run,conclusion=conclusion),self.summary,'new'))
  self.assertFalse(recovery.may_recover(self.run,self.summary,'new',False))
 def test_fork_or_untrusted_branch_is_never_recovered(self):
  for changes in ({'head_branch':'other'},{'event':'pull_request'},{'head_repository':{'full_name':'other/repo'}}):self.assertFalse(recovery.may_recover(dict(self.run,**changes),self.summary,'new'))
 def test_active_or_already_completed_data_is_untouched(self):
  self.assertFalse(recovery.may_recover(dict(self.run,status='in_progress'),self.summary,'new'))
  self.assertFalse(recovery.may_recover(self.run,dict(self.summary,stores=[{'status':'done'}]),'new'))
 def test_chain_follows_only_authorized_root(self):
  runs=[{'databaseId':3,'displayTitle':'Automatic continuation of 2'},{'databaseId':9,'displayTitle':'Automatic continuation of 8'},{'databaseId':2,'displayTitle':'Automatic continuation of 1'},{'databaseId':1,'displayTitle':'Cloud group solo-laam'}]
  self.assertEqual([r['databaseId'] for r in recovery.descendants(runs,1)],[3,2,1])

class TransportRecoveryTests(unittest.TestCase):
 def test_saved_ancestor_can_recover_host_loss_but_not_manual_stop_or_empty_chain(self):
  s={'checkpoint':'saved','status':'incomplete','stop_reason':'time_budget','auto_continue_limit':48,'continuation_index':6,'stalled_runs':0}
  self.assertTrue(recovery.transport_recoverable(s,['300','200']))
  for change in ({'checkpoint':'missing'},{'status':'complete'},{'stop_reason':'stop_requested'},{'stalled_runs':2},{'continuation_index':48}):
   self.assertFalse(recovery.transport_recoverable(dict(s,**change),['300','200']))
  self.assertFalse(recovery.transport_recoverable(s,['400','300','200','100']))
 def test_parser_failure_is_not_a_host_interruption(self):
  from unittest.mock import patch
  import json
  with patch.object(recovery,'gh',return_value=json.dumps({'jobs':[{'conclusion':'failure','check_run_url':'https://api.github.com/repos/'+recovery.REPO+'/check-runs/1'}]})) as call:
   call.side_effect=[json.dumps({'jobs':[{'conclusion':'failure','check_run_url':'https://api.github.com/repos/'+recovery.REPO+'/check-runs/1'}]}),json.dumps([{'message':'Process completed with exit code 2.'}])]
   self.assertFalse(recovery.host_interrupted({'id':1,'conclusion':'failure'}))
 def test_verified_runner_loss_can_recover_without_guessing_parser_success(self):
  from unittest.mock import patch
  import json
  with patch.object(recovery,'gh',side_effect=[json.dumps({'jobs':[{'conclusion':'failure','check_run_url':'https://api.github.com/repos/'+recovery.REPO+'/check-runs/1'}]}),json.dumps([{'message':'The hosted runner lost communication with the server.'}])]):
   self.assertTrue(recovery.host_interrupted({'id':1,'conclusion':'failure'}))

class ReviewedSourceRevisionTests(unittest.TestCase):
 def test_unrelated_commits_do_not_repeat_identical_parser_failures(self):
  import hashlib,json,tempfile
  from unittest.mock import patch
  from pathlib import Path
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);content=b'current source';(root/'main.py').write_bytes(content);(root/'laam_source_support.py').write_bytes(content)
   blob=hashlib.sha1(b'blob '+str(len(content)).encode()+b'\0'+content).hexdigest()
   with patch.object(recovery,'gh',return_value=json.dumps({'sha':blob})):
    self.assertFalse(recovery.reviewed_adapter_changed({'head_sha':'a'*40},{'name':'LAAM'},root))
   with patch.object(recovery,'gh',return_value=json.dumps({'sha':'different'})):
    self.assertTrue(recovery.reviewed_adapter_changed({'head_sha':'a'*40},{'name':'LAAM'},root))
