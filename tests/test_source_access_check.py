import unittest
from types import SimpleNamespace
from unittest.mock import Mock
from source_access_check import check

class PublicAccessTests(unittest.TestCase):
 def test_new_store_api_must_confirm_product_schema(self):
  for name,url in [('Nayab Fashion','https://nayabfashion.com.pk')]:
   s=Mock();s.headers={};s.get.side_effect=[SimpleNamespace(status_code=200,text='User-agent: *\nAllow: /'),SimpleNamespace(status_code=200,json=lambda:[{'id':123}])]
   self.assertEqual(check(dict(name=name,url=url),s)['status'],'public_api_readable')
   self.assertEqual(s.get.call_args.args[0],url+'/wp-json/wc/store/v1/products?per_page=100&page=1')
 def test_czone_probes_only_normal_catalog_and_preserves_denial(self):
  s=Mock();s.headers={};s.get.side_effect=[SimpleNamespace(status_code=200,text='User-agent: *\nAllow: /'),SimpleNamespace(status_code=403,text='Forbidden',headers={},json=Mock(side_effect=ValueError))]
  result=check(dict(name='Computer Zone',url='https://www.czone.com.pk'),s)
  self.assertEqual(result['status'],'source_denied');self.assertEqual(s.get.call_count,2);self.assertEqual(s.get.call_args.args[0],'https://www.czone.com.pk/products')
 def test_denial_is_classified_without_retry_or_body_publication(self):
  s=Mock();s.headers={};s.get.side_effect=[SimpleNamespace(status_code=200,text='User-agent: *\nAllow: /'),SimpleNamespace(status_code=403,text='<title>Just a moment</title>private body',headers={'cf-mitigated':'challenge'},json=Mock(side_effect=ValueError))]
  result=check(dict(name='Nayab Fashion',url='https://nayabfashion.com.pk'),s)
  self.assertEqual(result['status'],'source_denied');self.assertEqual(result['denial_kind'],'cloudflare_challenge');self.assertEqual(s.get.call_count,2);self.assertNotIn('private',str(result))
 def test_owner_paused_source_never_makes_requests(self):
  s=Mock();self.assertEqual(check(dict(name='Gift4U',url='https://gift4u.pk'),s)['status'],'owner_paused');s.get.assert_not_called()
 def test_robots_disallowed_api_never_gets_probed(self):
  s=Mock();s.headers={};s.get.return_value=SimpleNamespace(status_code=200,text='User-agent: *\nDisallow: /wp-json/')
  self.assertEqual(check(dict(name='Nayab Fashion',url='https://nayabfashion.com.pk'),s)['status'],'robots_disallowed');self.assertEqual(s.get.call_count,1)
