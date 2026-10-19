import json,sys,threading,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import requests
import czone_source_support as c
import fast_fetch_support as fast
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'cloud'))
import auto_continue as auto
class RetryTests(unittest.TestCase):
 def response(self,status,body=b'good',retry=None):
  r=requests.Response();r.status_code=status;r._content=body;r.url=c.BASE+'/product'
  if retry:r.headers['Retry-After']=retry
  return r
 def globals(self,session):return {'S':session,'_chotu_tls':SimpleNamespace(),'_chotu_wait':lambda:None,'_chotu_backoff':lambda *a:None}
 def test_transient_500_recovers_without_skipping_product(self):
  session=SimpleNamespace(get=lambda *a,**k:next(sequence));sequence=iter([self.response(500),self.response(200)])
  self.assertEqual(c.fetch_page(self.globals(session),session,c.BASE+'/product').content,b'good')
 def test_persistent_page_does_not_prevent_other_products_from_being_retained(self):
  calls={}
  def get(url,**kwargs):
   calls[url]=calls.get(url,0)+1
   return self.response(500 if url.endswith('/bad') and calls[url]<=3 else 200)
  g=self.globals(SimpleNamespace(get=get));rows=list(c.parallel_pages(g,[c.BASE+'/bad',c.BASE+'/good'],lambda s:None))
  self.assertEqual([u for u,b in rows],[c.BASE+'/good',c.BASE+'/bad']);self.assertEqual(calls[c.BASE+'/bad'],4)
 def test_unresolved_server_error_is_bounded_and_pauses_incomplete_store(self):
  calls=[];session=SimpleNamespace(get=lambda url,**k:(calls.append(url) or self.response(500)))
  with self.assertRaisesRegex(RuntimeError,'SOURCE PAUSED'):
   list(c.parallel_pages(self.globals(session),[c.BASE+'/bad'],lambda s:None))
  self.assertEqual(len(calls),6)
 def test_rate_limit_does_not_retry_while_source_is_blocked(self):
  calls=[];session=SimpleNamespace(get=lambda url,**k:(calls.append(url) or self.response(429,retry='180')))
  with self.assertRaisesRegex(RuntimeError,'SOURCE PAUSED'):c.fetch_page(self.globals(session),session,c.BASE+'/bad')
  self.assertEqual(len(calls),1)
 def test_long_upstream_retry_after_does_not_get_shortened(self):
  session=SimpleNamespace(get=lambda *a,**k:self.response(500,retry='3600'))
  with self.assertRaisesRegex(RuntimeError,'3600s'):c.fetch_page(self.globals(session),session,c.BASE+'/bad')
class ParallelRetryTests(unittest.TestCase):
 def test_parallel_workers_finish_healthy_pages_before_deferred_retry(self):
  with tempfile.TemporaryDirectory() as temp:
   lock=threading.Lock();calls={};tls=threading.local();tls.saved_api_path=Path(temp)/'api.sqlite3';tls.fast_gate=SimpleNamespace(recovery_not_before=0)
   class Session:
    def __init__(self):self.headers={}
    def close(self):pass
    def get(self,url,**kwargs):
     with lock:calls[url]=calls.get(url,0)+1;count=calls[url]
     r=requests.Response();r.status_code=500 if url.endswith('/bad') and count<=3 else 200;r._content=b'checked';r.url=url;return r
   g={'S':Session(),'requests':SimpleNamespace(Session=Session),'_chotu_tls':tls,'_chotu_wait':lambda:None,'_chotu_backoff':lambda *a:None}
   result=list(c.parallel_pages(g,[c.BASE+'/bad',c.BASE+'/good1',c.BASE+'/good2'],lambda s:None))
   self.assertEqual({url for url,body in result},{c.BASE+'/bad',c.BASE+'/good1',c.BASE+'/good2'});self.assertEqual(result[-1][0],c.BASE+'/bad');self.assertEqual(calls[c.BASE+'/bad'],4)
class StrictPreloadTests(unittest.TestCase):
 def test_strict_mode_never_queries_unlinked_legacy_collections(self):
  tls=threading.local();tls.website_category_navigation=[{'category':'Skin'}];tls.saved_api_path=Path('/tmp/unused.sqlite3');tls.fast_gate=SimpleNamespace(limited=False);tls.fast_products=[]
  class App:
   def __init__(self,root):pass
  calls=[]
  def forbidden(url):calls.append(url);raise AssertionError('Legacy endpoint must not be called')
  session=SimpleNamespace();g={'requests':SimpleNamespace(Session=lambda:session),'App':App,'S':session,'_chotu_tls':tls,'_chotu_wait':lambda:None,'_chotu_open_checkpoint':lambda *a:None,'_chotu_close_checkpoint':lambda *a:None,'discover':lambda *a:([],True),'collections':lambda *a:{123:['Exact menu category']},'_chotu_backoff':lambda *a:None,'get_json':forbidden,'_chotu_debug_request':lambda *a:None,'_chotu_debug_response':lambda *a,**k:None,'_chotu_debug':lambda *a:None,'_chotu_debug_stage':lambda *a:None}
  fast.enable_fast_fetch(g);self.assertEqual(g['collections']('https://store.example',lambda s:None),{123:['Exact menu category']});self.assertEqual(calls,[])
class ContinuationDispatchTests(unittest.TestCase):
 def test_current_job_can_dispatch_checkpoint_continuation_with_duplicate_guard(self):
  run={'id':123,'head_sha':'a'*40,'event':'workflow_dispatch','head_branch':'main','head_repository':{'full_name':'o/r'},'conclusion':None}
  summary={'checkpoint':'saved','status':'incomplete','stop_reason':'time_budget','auto_continue_limit':6,'continuation_index':0,'stores':[{'status':'pending'}]}
  for duplicate in (False,True):
   calls=[]
   def gh(*args):
    calls.append(args)
    if args[0]=='api':return json.dumps({'artifacts':[{'name':'chotuapp-checkpoint','expired':False}]})
    if args[:2]==('run','list'):return json.dumps([{'displayTitle':'Automatic continuation of 123'}] if duplicate else [])
    return ''
   with patch.dict(auto.os.environ,{'GITHUB_REPOSITORY':'o/r'}),patch.object(sys,'argv',['auto','--current-run']),patch.object(auto,'current_run_context',return_value=(run,summary)),patch.object(auto,'gh',side_effect=gh):auto.main()
   self.assertEqual(any(c[:2]==('workflow','run') for c in calls),not duplicate)
 def test_incomplete_packaging_does_not_dispatch(self):
  with tempfile.TemporaryDirectory() as temp:
   p=Path(temp);(p/'fetch-phase.json').write_text(json.dumps({'phase':'checkpoint'}))
   with patch.dict(auto.os.environ,{'GITHUB_RUN_ID':'123','GITHUB_EVENT_NAME':'workflow_dispatch','CHOTUAPP_CLOUD_DATA':temp}),patch.object(auto,'gh') as gh:
    self.assertEqual(auto.current_run_context(),(None,None));gh.assert_not_called()
if __name__=='__main__':unittest.main()
