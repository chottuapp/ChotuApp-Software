import unittest
from fast_fetch_support import source_policy

class WorkerPolicyTests(unittest.TestCase):
 def test_overlapping_requests_preserve_host_spacing(self):
  for host,spacing in [('zellbury.com',1.5),('outfitters.com.pk',1.5),('junaidjamshed.com',1.0),('rawayat.com.pk',1.0)]:
   self.assertEqual(source_policy(host),(spacing,2))
 def test_recently_limited_sources_remain_single_worker(self):
  for host in ['stylo.pk','gulahmedshop.com','bonanzasatrangi.com']:
   self.assertEqual(source_policy(host),(2.5,1))
