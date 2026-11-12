import json,unittest
from additional_completed_sources import approved_runs,REPO
class AdditionalSourcesTests(unittest.TestCase):
 def setUp(self):
  self.config={'stores':['ChotuApp Groceries'],'additional_completed_sources':[{'store':'ChotuApp Groceries','run_id':'123'}]};self.sites={'ChotuApp Groceries':{'url':'https://www.naheed.pk'}}
  self.run=dict(id=123,head_branch='main',path='.github/workflows/cloud-fetch.yml',event='workflow_dispatch',status='completed',conclusion='success',head_repository={'full_name':REPO},display_title='Automatic continuation of 122',head_sha='a'*40)
 def test_exact_successful_additive_source_routes_to_audit(self):
  rows=approved_runs(self.config,self.sites,lambda *a:json.dumps(self.run));self.assertEqual(rows[0]['additional_store'],'ChotuApp Groceries');self.assertEqual(rows[0]['databaseId'],123)
 def test_untrusted_failed_or_running_sources_are_rejected(self):
  for key,value in [('head_branch','other'),('conclusion','failure'),('status','in_progress'),('path','.github/workflows/other.yml'),('head_repository',{'full_name':'other/repo'})]:
   with self.subTest(key=key),self.assertRaises(ValueError):approved_runs(self.config,self.sites,lambda *a:json.dumps(dict(self.run,**{key:value})))
 def test_targeted_other_store_does_not_fetch_additional_artifact(self):
  self.assertEqual(approved_runs(self.config,self.sites,lambda *a:self.fail('Unexpected source API read'),{'Other'}),[])
 def test_unregistered_store_is_rejected(self):
  self.config['stores']=[]
  with self.assertRaises(ValueError):approved_runs(self.config,self.sites,lambda *a:json.dumps(self.run))

 def test_reviewed_grocery_finalizer_is_allowed_only_when_explicitly_configured(self):
  self.config['additional_completed_sources'][0]['workflow']='.github/workflows/cloud-grocery-complete.yml';self.run['path']='.github/workflows/cloud-grocery-complete.yml'
  self.assertEqual(approved_runs(self.config,self.sites,lambda *a:json.dumps(self.run))[0]['additional_store'],'ChotuApp Groceries')
 def test_arbitrary_custom_source_workflow_remains_rejected(self):
  self.config['additional_completed_sources'][0]['workflow']='.github/workflows/other.yml'
  with self.assertRaises(ValueError):approved_runs(self.config,self.sites,lambda *a:json.dumps(self.run))

 def test_registered_generation_is_preserved_for_separate_fresh_delivery_gate(self):
  self.config['additional_completed_sources'][0]['refresh_generation']='current'
  result=approved_runs(self.config,self.sites,lambda *a:json.dumps(self.run))
  self.assertEqual(result[0]['additional_refresh_generation'],'current')
