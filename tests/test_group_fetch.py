import json,os,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'cloud'))
from group_fetch import groups
from partition_resume import partition
from resume_support import RunStore

class GroupFetchTests(unittest.TestCase):
 def sites(self,n):return [{'name':'Store '+str(i),'url':'https://store'+str(i)+'.example'} for i in range(n)]
 def test_twenty_nine_stores_split_into_six_disjoint_runners(self):
  sites=self.sites(29);plan=groups(sites)
  self.assertEqual([len(g) for g in plan],[5,5,5,5,5,4]);self.assertEqual([s for g in plan for s in g],sites)
 def test_completed_stores_are_not_dispatched_again(self):
  sites=self.sites(29);plan=groups(sites,[s['name'] for s in sites[:22]])
  self.assertEqual([len(g) for g in plan],[5,2]);self.assertEqual(groups(sites,[s['name'] for s in sites]),[])
 def test_alias_hosts_names_and_unknown_saved_store_are_rejected(self):
  for sites,done in [([{'name':'A','url':'https://example.com'},{'name':'B','url':'http://www.example.com'}],()),([{'name':'A','url':'https://one.example'},{'name':'a','url':'https://two.example'}],()),(self.sites(2),['Unknown'])]:
   with self.assertRaises(ValueError):groups(sites,done)
 def test_checkpoint_partition_preserves_selected_cache_bytes_and_template(self):
  with tempfile.TemporaryDirectory() as tmp:
   data=Path(tmp);store=RunStore(data/'saved_runs');old=store.root/'parent';old.mkdir();(old/'template.xlsx').write_bytes(b'custom template')
   sites=self.sites(5)
   for i,s in enumerate(sites):
    s.update(status='source_paused' if i==3 else 'pending',progress=i*10,output=None);folder=old/str(i);folder.mkdir();(folder/'api.sqlite3').write_bytes(('cached '+str(i)).encode())
   state={'id':'parent','template':'/old/runner/template.xlsx','sites':sites,'status':'incomplete'};store.save(state)
   selected=partition(data,[sites[3],sites[1]])
   self.assertEqual([s['name'] for s in selected['sites']],['Store 1','Store 3']);self.assertEqual(selected['sites'][1]['status'],'source_paused');self.assertEqual(selected['sites'][1]['progress'],30)
   folder=store.root/selected['id'];self.assertEqual((folder/'0/api.sqlite3').read_bytes(),b'cached 1');self.assertEqual((folder/'1/api.sqlite3').read_bytes(),b'cached 3');self.assertEqual((folder/'template.xlsx').read_bytes(),b'custom template');self.assertFalse(old.exists());self.assertEqual(store.load()['id'],selected['id'])
 def test_bad_partition_does_not_modify_parent(self):
  with tempfile.TemporaryDirectory() as tmp:
   data=Path(tmp);store=RunStore(data/'saved_runs');state={'id':'parent','sites':self.sites(2),'template':'old'};store.save(state)
   with self.assertRaises(ValueError):partition(data,self.sites(3))
   self.assertEqual(store.load(),state)
 def test_continuation_summary_carries_runner_identity(self):
  import auto_continue
  summary={'runner_group':'batch-123-2','auto_continue_limit':6,'continuation_index':0,'progress_token':'abc','stalled_runs':0}
  run={'id':77,'event':'workflow_dispatch','head_branch':'main','head_repository':{'full_name':'o/r'}};calls=[]
  def gh(*args):
   calls.append(args)
   if args[0]=='api':return json.dumps({'artifacts':[{'name':'chotuapp-checkpoint','expired':False}]})
   return '[]' if args[:2]==('run','list') else ''
  with patch.dict(os.environ,{'GITHUB_REPOSITORY':'o/r'}),patch('sys.argv',['auto_continue.py','--current-run']),patch.object(auto_continue,'current_run_context',return_value=(run,summary)),patch.object(auto_continue,'eligible',return_value=True),patch.object(auto_continue,'gh',side_effect=gh):auto_continue.main()
  command=next(c for c in calls if c[:2]==('workflow','run'));self.assertIn('runner_group=batch-123-2',command);self.assertIn('resume_run_id=77',command)
 def test_dispatch_creates_separate_workflows_without_duplicate_stores(self):
  import group_fetch
  calls=[]
  def gh(*args):
   calls.append(args);return '[]' if args[:2]==('run','list') else ''
  with tempfile.TemporaryDirectory() as tmp,patch.dict(os.environ,{'GITHUB_REPOSITORY':'o/r','GITHUB_RUN_ID':'999','CLOUD_STORES':json.dumps(self.sites(11)),'RESUME_RUN_ID':''}),patch.object(group_fetch,'gh',side_effect=gh):
   previous=Path.cwd()
   try:
    os.chdir(tmp);group_fetch.main();plan=json.loads(Path('fetch-group-plan.json').read_text())
   finally:os.chdir(previous)
  commands=[a for a in calls if a[:2]==('workflow','run')];self.assertEqual(len(commands),3)
  self.assertEqual([len(g['stores']) for g in plan['groups']],[5,5,1]);self.assertEqual(len({s['url'] for g in plan['groups'] for s in g['stores']}),11)
  for i,command in enumerate(commands,1):self.assertIn('runner_group=batch-999-'+str(i),command);self.assertIn('partition_resume=false',command)
 def test_live_legacy_run_blocks_group_dispatch(self):
  import group_fetch
  with patch.dict(os.environ,{'GITHUB_REPOSITORY':'o/r','GITHUB_RUN_ID':'999','RESUME_RUN_ID':''}),patch.object(group_fetch,'gh',return_value=json.dumps([{'displayTitle':'Cloud fetch by user','status':'in_progress','databaseId':55}])) as gh:
   with self.assertRaisesRegex(ValueError,'55'):group_fetch.main()
   self.assertEqual(gh.call_count,1)

class GroupRestoreIntegrationTests(unittest.TestCase):
 def test_prepare_partitions_restored_copy_and_keeps_parent_unchanged(self):
  from openpyxl import Workbook
  from cli import checkpoint
  from prepare_resume import prepare,prepared
  from resume_support import ResponseCache
  import requests
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);source=root/'parent';source.mkdir();template=source/'template.xlsx';book=Workbook();book.active.title='Products';book.active.append(['owner_custom_header']);book.save(template)
   store=RunStore(source/'saved_runs');sites=[{'name':'Store '+str(i),'url':'https://site'+str(i)+'.example'} for i in range(6)];state=store.fresh(sites,template)
   for i in range(6):
    folder=store.root/state['id']/str(i);folder.mkdir();cache=ResponseCache(folder/'pages.sqlite3');response=requests.Response();response.status_code=200;response.url=sites[i]['url'];response._content=('page '+str(i)).encode();cache.put(response.url,response);cache.close()
   archive=root/'checkpoint.zip';checkpoint(source,archive);destination=root/'restored'
   with patch.dict(os.environ,{'CLOUD_PARTITION_RESUME':'true','CLOUD_STORES':json.dumps([sites[2],sites[5]])}):prepare(archive,destination,'123')
   self.assertTrue(prepared(destination,'123'));selected=RunStore(destination/'saved_runs').load();self.assertEqual([s['name'] for s in selected['sites']],['Store 2','Store 5'])
   for new,old in enumerate((2,5)):
    cache=ResponseCache(destination/'saved_runs'/selected['id']/str(new)/'pages.sqlite3');self.assertEqual(cache.get(sites[old]['url']).content,('page '+str(old)).encode());cache.close()
   self.assertEqual(Path(selected['template']).read_bytes(),template.read_bytes());self.assertEqual(store.load()['id'],state['id']);self.assertTrue((store.root/state['id']/'0/pages.sqlite3').is_file())

class WindowsMigrationTests(unittest.TestCase):
 def test_helper_saves_active_run_before_requesting_groups(self):
  import importlib.util,subprocess
  path=Path(__file__).resolve().parents[1]/'catalog-tools/start_five_store_runners_windows.py';spec=importlib.util.spec_from_file_location('group_windows',path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);commands=[]
  def run(args,**kwargs):
   commands.append(args)
   if args[1:3]==['run','list']:out=json.dumps([{'databaseId':123,'displayTitle':'Cloud fetch by user','status':'in_progress'}])
   elif args[1:3]==['run','view']:out=json.dumps({'status':'completed','conclusion':'failure'})
   elif args[1]=='api':out=json.dumps({'artifacts':[{'name':'chotuapp-checkpoint'}]})
   else:out='https://github.com/o/r/actions/runs/456'
   return subprocess.CompletedProcess(args,0,stdout=out,stderr='')
  with patch('sys.argv',['migration']),patch.object(module.subprocess,'run',side_effect=run):module.main()
  workflows=[c[3] for c in commands if c[1:3]==['workflow','run']];self.assertEqual(workflows,['cloud-stop.yml','cloud-fetch-groups.yml']);self.assertIn('resume_run_id=123',commands[-1])
 def test_helper_does_not_restart_without_a_checkpoint(self):
  import importlib.util,subprocess
  path=Path(__file__).resolve().parents[1]/'catalog-tools/start_five_store_runners_windows.py';spec=importlib.util.spec_from_file_location('group_windows_bad',path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);commands=[]
  def run(args,**kwargs):
   commands.append(args)
   if args[1:3]==['run','list']:out=json.dumps([{'databaseId':123,'displayTitle':'Cloud fetch by user','status':'completed'}])
   elif args[1:3]==['run','view']:out=json.dumps({'status':'completed','conclusion':'failure'})
   else:out=json.dumps({'artifacts':[]})
   return subprocess.CompletedProcess(args,0,stdout=out,stderr='')
  with patch('sys.argv',['migration']),patch.object(module.subprocess,'run',side_effect=run),self.assertRaisesRegex(SystemExit,'No saved checkpoint'):module.main()
  self.assertFalse(any(c[1:3]==['workflow','run'] for c in commands))

if __name__=='__main__':unittest.main()
