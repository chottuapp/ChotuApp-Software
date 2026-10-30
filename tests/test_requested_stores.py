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
  result,_=self.probe([self.response('/robots.txt',text='User-agent: *\nAllow: /'),self.response('',text='Shopify storefront'),self.response('/products.json',{'products':[dict(id=1,handle='x',variants=[dict(id=2)])]})])
  self.assertEqual(result['status'],'supported');self.assertEqual(result['provider'],'shopify')
 def test_woo_requires_existing_adapter_registration(self):
  result,_=self.probe([self.response('/robots.txt',text='User-agent: *\nAllow: /'),self.response('',text='Shopify storefront'),self.response('/products.json',status=404),self.response('/wp-json/wc/store/v1/products',[dict(id=1,prices=dict(currency_code='PKR'))])])
  self.assertEqual(result['status'],'adapter_registration_required')
 def test_denied_source_is_not_retried_through_other_endpoint(self):
  result,session=self.probe([self.response('/robots.txt',text='User-agent: *\nAllow: /'),self.response('',text='Shopify storefront'),self.response('/products.json',status=403)])
  self.assertEqual(result['status'],'source_blocked');self.assertEqual(session.get.call_count,3)
 def test_robots_disallow_stops_before_catalog_request(self):
  result,session=self.probe([self.response('/robots.txt',text='User-agent: *\nDisallow: /')])
  self.assertEqual(result['status'],'source_blocked');self.assertEqual(session.get.call_count,1)


class ApprovedWooOffersTests(unittest.TestCase):
 def test_observed_house_tools_and_g7_currency_scales(self):
  from decimal import Decimal
  from woocommerce_source_support import offer,HOSTS
  self.assertTrue({'houseoftools.com.pk','gsevenleather.com'}<=HOSTS)
  for scale,regular,sale,want_regular,want_sale in [(2,'29705000','26734500','297050','267345'),(0,'14999','14999','14999','14999')]:
   p=dict(prices=dict(currency_code='PKR',currency_minor_unit=scale,price=sale,regular_price=regular),is_in_stock=True,is_purchasable=True)
   actual=offer(p);self.assertEqual(actual,(Decimal(want_regular),Decimal(want_sale),True))

class HomepageProviderTests(unittest.TestCase):
 response=ProviderProbeTests.response
 probe=ProviderProbeTests.probe
 def test_verified_wordpress_homepage_uses_its_native_store_api(self):
  result,session=self.probe([self.response('/robots.txt',text='User-agent: *\nAllow: /'),self.response('',text='<script src="/wp-content/plugins/woocommerce/shop.js"></script>'),self.response('/wp-json/wc/store/v1/products',[dict(id=1,prices=dict(currency_code='PKR'))])])
  self.assertEqual(result['provider'],'woocommerce');self.assertEqual(result['homepage_platform_hint'],'wordpress')
  self.assertFalse(any('products.json' in call.args[0] for call in session.get.call_args_list))

class RequestedResumeTests(unittest.TestCase):
 setUp=RequestedStoreTests.setUp
 def fixtures(self):
  lane='audit804-'+self.request['campaign_id']+'-'+self.request['refresh_generation']+'-'+self.request['request_id']+'-2-SE10058'
  run=dict(id=123,event='workflow_dispatch',head_branch='main',head_repository=dict(full_name='chottuapp/ChotuApp-Software'),display_title='Cloud group '+lane,status='completed',conclusion='failure')
  summary=dict(runner_group=lane,stores=[dict(name='Paklap')],status='incomplete',checkpoint='saved',stop_reason='source_failure',auto_continue_limit=48,continuation_index=0)
  return run,summary,[dict(name='chotuapp-checkpoint',expired=False)]
 def test_only_exact_failed_checkpoint_can_resume_once(self):
  from requested_stores import resume_allowed
  run,summary,artifacts=self.fixtures()
  self.assertTrue(resume_allowed(self.request,'Paklap','123',[],run,summary,artifacts))
  runs=[dict(databaseId=124,displayTitle='Automatic continuation of 123',status='in_progress')]
  self.assertFalse(resume_allowed(self.request,'Paklap','123',runs,run,summary,artifacts))
  with self.assertRaises(ValueError):resume_allowed(self.request,'Paklap','123',[],run,summary,[])
  summary['stores']=[dict(name='Other Store')]
  with self.assertRaises(ValueError):resume_allowed(self.request,'Paklap','123',[],run,summary,artifacts)
 def test_success_manual_stop_and_active_parent_are_preserved(self):
  from requested_stores import resume_allowed
  run,summary,artifacts=self.fixtures()
  for change in ({'status':'in_progress'},{'conclusion':'success'}):self.assertFalse(resume_allowed(self.request,'Paklap','123',[],dict(run,**change),summary,artifacts))
  self.assertFalse(resume_allowed(self.request,'Paklap','123',[],run,dict(summary,stop_reason='stop_requested'),artifacts))

if __name__=='__main__':unittest.main()
