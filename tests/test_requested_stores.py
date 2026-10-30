import copy,json,unittest
from pathlib import Path
from requested_stores import validate,dispatch_plan,root_lane,ROOT

class RequestedStoreTests(unittest.TestCase):
 def setUp(self):
  read=lambda n:json.loads((ROOT/'cloud'/n).read_text())
  self.request=read('requested-stores.json');self.registry=read('fetch-update-release.json')['fresh_stores'];self.codes=read('confirmed-shop-codes.json');self.policy=read('audit804-release.json')
 def test_exact_ten_codes_unique_names_and_hosts(self):
  stores=validate(self.request,self.registry,self.codes,self.policy)
  self.assertEqual(len(stores),10);self.assertEqual([s['shop_code'] for s in stores],['SE100'+str(n) for n in range(55,65)])
  self.assertEqual(sum(s['name']=='Limelight' for s in self.registry),1);self.assertEqual(sum(s['name']=='Alkaram Studio' for s in self.registry),1)
  self.assertEqual(len(set(self.codes.values())),len(self.codes))
 def test_invalid_source_code_and_paused_names_refused(self):
  for change in ({'url':'https://other.example'},{'shop_code':'SE10014'},{'name':'Khaadi'}):
   request=copy.deepcopy(self.request);request['stores'][0].update(change)
   with self.assertRaises(ValueError):validate(request,self.registry,self.codes,self.policy)
 def test_paired_plan_dispatches_only_requested_supported_stores(self):
  ready={s['name'] for s in self.request['stores']};plan,_,_=dispatch_plan(self.request,[],ready)
  self.assertEqual(len(plan),5);self.assertTrue(all(len(g['stores'])==2 for g in plan))
  self.assertEqual({s['name'] for g in plan for s in g['stores']},ready)
 def test_active_original_lane_and_continuation_are_preserved(self):
  lane=next(k for k,v in self.request['existing_lanes'].items() if 'Limelight' in v)
  runs=[dict(databaseId=1,displayTitle='Cloud group '+lane,status='completed'),dict(databaseId=2,displayTitle='Automatic continuation of 1',status='in_progress')]
  plan,active,_=dispatch_plan(self.request,runs,{'Limelight','Alkaram Studio','Gift4U'})
  self.assertIn('Limelight',active);self.assertNotIn('Limelight',{s['name'] for g in plan for s in g['stores']});self.assertEqual(root_lane(runs[1],runs),lane)
 def test_rerun_and_later_adapter_registration_do_not_duplicate(self):
  plan,_,_=dispatch_plan(self.request,[],{'Limelight'})
  runs=[dict(databaseId=1,displayTitle='Cloud group '+plan[0]['runner_group'],status='completed')]
  next_plan,_,launched=dispatch_plan(self.request,runs,{'Limelight','Alkaram Studio'})
  self.assertEqual(launched,{'Limelight'});self.assertEqual([s['name'] for g in next_plan for s in g['stores']],['Alkaram Studio'])
  self.assertNotEqual(plan[0]['runner_group'],next_plan[0]['runner_group'])
 def test_no_supported_provider_means_no_fetch(self):
  self.assertEqual(dispatch_plan(self.request,[],set())[0],[])
if __name__=='__main__':unittest.main()

class ProviderProbeTests(unittest.TestCase):
 def response(self,path,data=None,status=200,text=''):
  from unittest.mock import Mock
  r=Mock(status_code=status,ok=status<400,text=text,content=text.encode(),url='https://gift4u.pk'+path)
  r.json.return_value=data
  if status>=400:
   import requests
   r.raise_for_status.side_effect=requests.HTTPError('HTTP '+str(status))
  return r
 def probe(self,responses):
  from unittest.mock import patch,Mock
  from requested_stores import probe
  session=Mock();session.headers={};session.get.side_effect=responses
  with patch('requested_stores.requests.Session',return_value=session),patch('requested_stores.time.sleep'):
   return probe(dict(name='Gift4U',url='https://gift4u.pk')),session
 def test_valid_shopify_source_is_supported(self):
  result,_=self.probe([self.response('/robots.txt',text='User-agent: *\nAllow: /'),self.response('/products.json',{'products':[dict(id=1,handle='x',variants=[dict(id=2)])]})])
  self.assertEqual(result['status'],'supported');self.assertEqual(result['provider'],'shopify')
 def test_woo_requires_existing_adapter_registration(self):
  result,_=self.probe([self.response('/robots.txt',text='User-agent: *\nAllow: /'),self.response('/products.json',status=404),self.response('/wp-json/wc/store/v1/products',[dict(id=1,prices=dict(currency_code='PKR'))])])
  self.assertEqual(result['status'],'adapter_registration_required')
 def test_denied_source_is_not_retried_through_other_endpoint(self):
  result,session=self.probe([self.response('/robots.txt',text='User-agent: *\nAllow: /'),self.response('/products.json',status=403)])
  self.assertEqual(result['status'],'source_blocked');self.assertEqual(session.get.call_count,2)
 def test_robots_disallow_stops_before_catalog_request(self):
  result,session=self.probe([self.response('/robots.txt',text='User-agent: *\nDisallow: /')])
  self.assertEqual(result['status'],'source_blocked');self.assertEqual(session.get.call_count,1)
