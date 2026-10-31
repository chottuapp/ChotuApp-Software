import json,unittest,copy
from pathlib import Path
from recover_pending_fetches import recovery_plan,REPO
class PendingRecoveryTests(unittest.TestCase):
 def setUp(self):
  root=Path(__file__).resolve().parents[1];self.policy=json.loads((root/'cloud/audit804-release.json').read_text());self.registry=json.loads((root/'cloud/fetch-update-release.json').read_text())['fresh_stores'];group='audit804-'+self.policy['campaign_id']+'-'+self.policy['refresh_generation']+'-23'
  self.request=dict(campaign_id=self.policy['campaign_id'],refresh_generation=self.policy['refresh_generation'],source_run='41039565023',runner_group=group,stores=['Liberty Books']);self.runs=[dict(databaseId=41039565023,displayTitle='Cloud group '+group,status='completed')];self.run=dict(id=41039565023,event='workflow_dispatch',head_branch='main',head_repository={'full_name':REPO},display_title='Cloud group '+group,status='completed',conclusion='failure');self.summary=dict(runner_group=group,status='incomplete',checkpoint='saved',stop_reason='completed_or_source_failure',stores=[dict(name='ChenOne',status='done'),dict(name='Liberty Books',status='failed')]);self.artifacts=[dict(name='chotuapp-checkpoint',expired=False)]
 def plan(self,**updates):
  args=dict(request=self.request,policy=self.policy,registry=self.registry,runs=self.runs,run=self.run,summary=self.summary,artifacts=self.artifacts);args.update(updates);return recovery_plan(**args)
 def test_only_failed_source_is_selected_and_completed_partner_is_preserved(self):self.assertEqual([s['name'] for s in self.plan()],['Liberty Books'])
 def test_existing_continuation_active_or_complete_never_duplicates(self):
  for status in ('in_progress','queued','completed'):
   self.assertIsNone(self.plan(runs=self.runs+[dict(databaseId=2,displayTitle='Automatic continuation of 41039565023',status=status)]))
 def test_newer_separately_completed_lane_is_not_replaced(self):
  newer=dict(databaseId=41039565024,displayTitle=self.runs[0]['displayTitle'],status='completed')
  self.assertIsNone(self.plan(runs=[newer]+self.runs))
 def test_disabled_foreign_and_wrong_generation_sources_are_rejected(self):
  for update in ({'stores':['LAAM']},{'stores':['ChenOne','Liberty Books','Bata']},{'refresh_generation':'old'}):
   with self.assertRaises(ValueError):self.plan(request=dict(self.request,**update))
 def test_missing_expired_or_wrong_checkpoint_cannot_start_fresh(self):
  for artifacts in ([],[dict(name='chotuapp-checkpoint',expired=True)]):
   with self.assertRaises(ValueError):self.plan(artifacts=artifacts)
  with self.assertRaises(ValueError):self.plan(summary=dict(self.summary,runner_group='another-group'))
 def test_manual_stop_or_completed_target_is_retained(self):
  self.assertIsNone(self.plan(summary=dict(self.summary,stop_reason='stop_requested')))
  summary=copy.deepcopy(self.summary);summary['stores'][1]['status']='done';self.assertIsNone(self.plan(summary=summary))
 def test_untrusted_run_is_rejected(self):
  with self.assertRaises(ValueError):self.plan(run=dict(self.run,head_branch='other'))

class AncestorRecoveryTests(PendingRecoveryTests):
 def ancestor(self,**updates):
  from recover_pending_fetches import ancestor_recovery_plan
  args=dict(request=self.request,policy=self.policy,registry=self.registry,runs=self.runs+[dict(databaseId=2,displayTitle='Automatic continuation of 41039565023',status='completed')],run=self.run,summary=self.summary,artifacts=self.artifacts,checkpoint_id='41039565023',latest_summary=self.summary);args.update(updates);return ancestor_recovery_plan(**args)
 def test_intact_ancestor_recovers_only_failed_store(self):self.assertEqual([s['name'] for s in self.ancestor()],['Liberty Books'])
 def test_foreign_checkpoint_or_latest_summary_is_rejected(self):
  with self.assertRaises(ValueError):self.ancestor(checkpoint_id='999')
  with self.assertRaises(ValueError):self.ancestor(latest_summary=dict(self.summary,runner_group='foreign'))
 def test_active_chain_and_manual_stop_stay_untouched(self):
  self.assertIsNone(self.ancestor(runs=self.runs+[dict(databaseId=2,displayTitle='Automatic continuation of 41039565023',status='in_progress')]))
  self.assertIsNone(self.ancestor(latest_summary=dict(self.summary,stop_reason='stop_requested')))

class RecoveryPublicationTests(unittest.TestCase):
 def test_recovery_report_branch_is_supported_by_publisher(self):
  from unittest.mock import patch
  from types import SimpleNamespace
  import source_research
  with patch.object(source_research.subprocess,'run',return_value=SimpleNamespace(stdout=b'a'*40)) as run:
   source_research._publish_once({'run_id':'1','status':'checking'},'pending-recovery-reports')
  self.assertTrue(any(call.args[0][:2]==['git','push'] for call in run.call_args_list))

class AdditiveLaneRecoveryTests(unittest.TestCase):
 def test_current_requested_pair_and_code_are_verified_without_relabelling_pauses(self):
  root=Path(__file__).resolve().parents[1];policy=json.loads((root/'cloud/audit804-release.json').read_text());registry=json.loads((root/'cloud/fetch-update-release.json').read_text())['fresh_stores']
  group='audit804-'+policy['campaign_id']+'-'+policy['refresh_generation']+'-requested20261031-2-SE10058'
  request=dict(campaign_id=policy['campaign_id'],refresh_generation=policy['refresh_generation'],source_run='77',runner_group=group,stores=['Paklap'])
  run=dict(id=77,event='workflow_dispatch',head_branch='main',head_repository={'full_name':REPO},display_title='Cloud group '+group,status='completed',conclusion='failure')
  summary=dict(runner_group=group,status='incomplete',checkpoint='saved',stores=[dict(name='Paklap',status='failed')])
  artifacts=[dict(name='chotuapp-checkpoint',expired=False)]
  self.assertEqual([s['name'] for s in recovery_plan(request,policy,registry,[],run,summary,artifacts)],['Paklap'])
  for suffix in ['requested20261031-1-SE10058','requested20261031-2-SE10057','requested20261031-2-SE10058-SE10058']:
   wrong=group.split('requested')[0]+suffix
   with self.subTest(group=wrong),self.assertRaises(ValueError):recovery_plan(dict(request,runner_group=wrong),policy,registry,[],dict(run,display_title='Cloud group '+wrong),dict(summary,runner_group=wrong),artifacts)
