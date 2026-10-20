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
