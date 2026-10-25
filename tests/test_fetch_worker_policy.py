import unittest
from fast_fetch_support import source_policy

class WorkerPolicyTests(unittest.TestCase):
 def test_overlapping_requests_preserve_host_spacing(self):
  for host,spacing in [('zellbury.com',1.5),('outfitters.com.pk',1.5),('junaidjamshed.com',1.0),('rawayat.com.pk',1.0)]:
   self.assertEqual(source_policy(host),(spacing,2))
 def test_recently_limited_sources_remain_single_worker(self):
  for host in ['stylo.pk','gulahmedshop.com','bonanzasatrangi.com']:
   self.assertEqual(source_policy(host),(2.5,1))

 def test_current_campaign_uses_longer_segments_only(self):
  import json
  from pathlib import Path
  from auto_continue import run_minutes
  request=json.loads((Path(__file__).resolve().parents[1]/'cloud/audit804-release.json').read_text())
  self.assertEqual(run_minutes({'runner_group':'audit804-'+request['campaign_id']+'-1','continuation_minutes':90}),300)
  self.assertEqual(run_minutes({'runner_group':'unrelated','continuation_minutes':90}),90)
