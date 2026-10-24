import unittest
from datetime import datetime,timezone,timedelta
from audit804_automation import validated_facts,request_from_holds
class AutomationTests(unittest.TestCase):
 def setUp(self):
  self.now=datetime(2026,10,23,tzinfo=timezone.utc);self.sites={'A':{'url':'https://shop.example'}}
  self.row={'store':'A','product_id':'CP1','name':'Blue Shirt','source_url':'https://shop.example/products/blue-shirt','product':{'handle':'blue-shirt','title':'Blue Shirt','type':'Shirts','description':'<p>Blue cotton shirt.</p>','price':123,'secret':'not copied'}}
 def report(self,row=None):return {'run_id':'1','checked_utc':self.now.isoformat(),'results':[row or self.row]}
 def test_only_primary_facts_are_copied(self):
  fact=validated_facts(self.report(),self.sites,self.now)[0]
  self.assertEqual(fact['description'],'Blue cotton shirt.');self.assertNotIn('price',fact);self.assertNotIn('secret',fact)
 def test_changed_identity_and_foreign_host_never_supply_facts(self):
  import copy
  for field,value in [('handle','other'),('title','Other Shirt')]:
   row=copy.deepcopy(self.row);row['product'][field]=value;self.assertEqual(validated_facts(self.report(row),self.sites,self.now),[])
  for url in ['https://foreign.example/products/blue-shirt','http://shop.example/products/blue-shirt','https://user:pass@shop.example/products/blue-shirt','https://shop.example/products/blue-shirt?token=secret']:
   row=copy.deepcopy(self.row);row['source_url']=url;self.assertEqual(validated_facts(self.report(row),self.sites,self.now),[])
 def test_stale_and_future_evidence_is_rejected(self):
  for offset in [timedelta(days=-2),timedelta(hours=1)]:
   report=self.report();report['checked_utc']=(self.now+offset).isoformat()
   with self.assertRaises(ValueError):validated_facts(report,self.sites,self.now)
 def test_rotation_is_bounded_and_includes_only_held_sources(self):
  state={'audit804_results':{'A':{'status':'hold','findings':[dict(product_id=str(i),name='Blue Shirt',source_url='https://shop.example/products/blue-shirt') for i in range(5)]},'B':{'status':'pass','findings':[]}}}
  first=request_from_holds(state,self.sites,limit=2);second=request_from_holds(state,self.sites,first,limit=2)
  self.assertEqual([r['product_id'] for r in first['products']],['0','1']);self.assertEqual([r['product_id'] for r in second['products']],['2','3'])
 def test_unchanged_facts_do_not_change_retry_key_and_cache_survives_batches(self):
  import tempfile,json,copy
  from pathlib import Path
  from audit804_automation import refresh
  now=datetime.now(timezone.utc);report=self.report();report['checked_utc']=now.isoformat()
  with tempfile.TemporaryDirectory() as folder:
   (Path(folder)/'cloud').mkdir()
   first,count,cache=refresh(folder,lambda *args:json.dumps(report),self.sites)
   report['checked_utc']=(now+timedelta(seconds=1)).isoformat();report['run_id']='2'
   second,count,cache=refresh(folder,lambda *args:json.dumps(report),self.sites,cache)
   self.assertEqual(first,second)
   report['results']=[]
   third,count,cache=refresh(folder,lambda *args:json.dumps(report),self.sites,cache)
   self.assertEqual(second,third);self.assertEqual(count,1)
 def test_hold_creates_recovery_work_not_a_fake_pass(self):
  from audit804_automation import recovery_plan
  report={'status':'hold','findings':[{'issues':['Category blank or unresolved']}]}
  plan=recovery_plan(report,now=self.now)
  self.assertTrue(plan['unfinished']);self.assertIn('Rerun independent all-row audit',plan['actions']);self.assertEqual(report['status'],'hold')
  self.assertFalse(recovery_plan({'status':'pass'},now=self.now)['unfinished'])
 def test_no_hold_does_not_start_fetching(self):self.assertEqual(request_from_holds({},self.sites)['products'],[])
