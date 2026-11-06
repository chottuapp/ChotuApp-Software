import copy,json,unittest
from pathlib import Path
from new_store_fetch import validate,plan,ROOT
class NewStoreFetchTests(unittest.TestCase):
 def setUp(self):
  self.request=json.loads((ROOT/'cloud/new-store-fetch-request.json').read_text());self.stores=validate(self.request)
  self.observations=[dict(name=s['name'],status='supported',provider='shopify') for s in self.stores]
 def test_eight_exact_sources_export_no_invented_codes(self):
  self.assertEqual(len(self.stores),8)
  groups,already=plan(self.request,self.stores,self.observations,[])
  self.assertEqual(len(groups),4);self.assertFalse(already)
  self.assertTrue(all('shop_code' not in s for g in groups for s in g['stores']))
 def test_reruns_and_continuations_cannot_duplicate_existing_stores(self):
  groups,_=plan(self.request,self.stores,self.observations,[])
  runs=[dict(databaseId=1,displayTitle='Cloud group '+groups[0]['runner_group'],status='completed'),dict(databaseId=2,displayTitle='Automatic continuation of 1',status='in_progress'),dict(databaseId=3,displayTitle='Cloud group unrelated-existing-run',status='in_progress')]
  remaining,already=plan(self.request,self.stores,self.observations,runs)
  self.assertEqual(already,{'Toyzone','Toynix'});self.assertEqual(len(remaining),3)
 def test_only_supported_exact_sources_start_and_later_registration_is_additive(self):
  observations=copy.deepcopy(self.observations);observations[1]['status']='source_blocked'
  first,_=plan(self.request,self.stores,observations,[])
  runs=[dict(databaseId=1,displayTitle='Cloud group '+first[0]['runner_group'],status='completed')]
  remaining,_=plan(self.request,self.stores,self.observations,runs)
  self.assertEqual(remaining[0]['stores'],[self.stores[1]])
 def test_bad_source_duplicate_and_invented_code_rejected(self):
  for change in ({'shop_code':'SE123'},{'url':'https://localhost/'},{'name':'Axis PK'},{'url':'https://www.toyzone.pk/private'}):
   r=copy.deepcopy(self.request);r['stores'][0].update(change)
   with self.assertRaises(ValueError):validate(r)

 def test_public_next_json_stream_handles_split_product_records_without_execution(self):
  from new_store_fetch import public_next_product_state
  payload='5:'+json.dumps(['$', 'Component', None, {'product':{'id':'p1','name':'Shirt','retailPrice':2000,'password':'private'},'variants':[{'id':'v1','stockOnHand':3,'stockReserved':1}]}])+'\n'
  scripts=''.join('<script>self.__next_f.push('+json.dumps([1,chunk])+')</script>' for chunk in (payload[:40],payload[40:]))
  result=public_next_product_state(scripts)
  product=next(p for p in result['hydration_products'] if p['id']=='p1')
  self.assertEqual(product['retailPrice'],2000);self.assertNotIn('password',json.dumps(result));self.assertEqual(result['product_contexts'][0]['variants'][0]['stockOnHand'],3)
