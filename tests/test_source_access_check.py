import unittest
from types import SimpleNamespace
from unittest.mock import Mock
from source_access_check import check

class PublicAccessTests(unittest.TestCase):
 def test_denial_is_classified_without_retry_or_body_publication(self):
  s=Mock();s.headers={};s.get.side_effect=[SimpleNamespace(status_code=200,text='User-agent: *\nAllow: /'),SimpleNamespace(status_code=403,text='<title>Just a moment</title>private body',headers={'cf-mitigated':'challenge'},json=Mock(side_effect=ValueError))]
  result=check(dict(name='Gift4U',url='https://gift4u.pk'),s)
  self.assertEqual(result['status'],'source_denied');self.assertEqual(result['denial_kind'],'cloudflare_challenge');self.assertEqual(s.get.call_count,2);self.assertNotIn('private',str(result))
 def test_owner_paused_source_never_makes_requests(self):
  s=Mock();self.assertEqual(check(dict(name='LAAM',url='https://laam.com'),s)['status'],'owner_paused');s.get.assert_not_called()
 def test_robots_disallowed_api_never_gets_probed(self):
  s=Mock();s.headers={};s.get.return_value=SimpleNamespace(status_code=200,text='User-agent: *\nDisallow: /wp-json/')
  self.assertEqual(check(dict(name='Gift4U',url='https://gift4u.pk'),s)['status'],'robots_disallowed');self.assertEqual(s.get.call_count,1)
