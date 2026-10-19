import sys,tempfile,threading,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'cloud'))
from runtime import requeue_updated_group
from resume_support import RunStore
from parallel_store_support import StoreScheduler
class QueuedRetryTests(unittest.TestCase):
 def test_group_release_retry_preserves_failure_and_does_not_repeat(self):
  state={'sites':[{'status':'blocked','software_revision':'a'*16,'detail':'SOURCE BLOCKED: old parser'}, {'status':'blocked','software_revision':'b'*16}, {'status':'done','software_revision':'a'*16}, {'status':'source_paused','software_revision':'a'*16}]}
  self.assertEqual(requeue_updated_group(state,'b'*16,''),0)
  self.assertEqual(requeue_updated_group(state,'b'*16,'batch-1'),1);self.assertEqual(state['sites'][0]['status'],'pending');self.assertEqual(state['sites'][0]['previous_detail'],'SOURCE BLOCKED: old parser');self.assertEqual(requeue_updated_group(state,'b'*16,'batch-1'),0)
  self.assertEqual([s['status'] for s in state['sites'][1:]],['blocked','done','source_paused'])
  state['sites'][0]['status']='blocked';self.assertEqual(requeue_updated_group(state,'b'*16,'batch-1'),0)
 def test_scheduled_manual_retry_is_pending_before_worker_starts(self):
  with tempfile.TemporaryDirectory() as tmp:
   store=RunStore(Path(tmp)/'saved');state={'id':'abc','status':'incomplete','sites':[{'name':'Shop','url':'https://shop.example','status':'blocked','detail':'Old failure','output':None}]};store.save(state)
   scheduler=StoreScheduler(Path(tmp)/'main.py',store,state,tmp,threading.Event(),lambda _:None,skip_terminal=False)
   self.assertEqual(scheduler.ready,[0]);self.assertEqual(store.load()['sites'][0]['status'],'pending');self.assertEqual(store.load()['sites'][0]['previous_detail'],'Old failure')
 def test_terminal_guard_is_preserved_without_an_update(self):
  with tempfile.TemporaryDirectory() as tmp:
   store=RunStore(Path(tmp)/'saved');state={'id':'abc','status':'incomplete','sites':[{'name':'Shop','url':'https://shop.example','status':'blocked','detail':'Access restriction','output':None}]};store.save(state)
   scheduler=StoreScheduler(Path(tmp)/'main.py',store,state,tmp,threading.Event(),lambda _:None,skip_terminal=True)
   self.assertEqual(scheduler.ready,[]);self.assertEqual(store.load()['sites'][0]['status'],'blocked')

 def test_three_store_cloud_capacity_keeps_default_and_bounds(self):
  with tempfile.TemporaryDirectory() as tmp:
   store=RunStore(Path(tmp)/'saved');state={'id':'abc','status':'incomplete','sites':[{'name':str(i),'url':'https://s'+str(i)+'.example','status':'pending','output':None} for i in range(3)]};store.save(state)
   def build(**kw):return StoreScheduler(Path(tmp)/'main.py',store,state,tmp,threading.Event(),lambda _:None,**kw)
   self.assertEqual(build().max_processes,2)
   self.assertEqual(build(max_processes=3).max_processes,3)
   self.assertEqual(build(max_processes=99).max_processes,3)
