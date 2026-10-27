import tempfile,time,unittest
from pathlib import Path
from unittest.mock import patch
import requests
from fast_fetch_support import source_policy,RequestGate
class StyloSpeedTests(unittest.TestCase):
 def test_overlap_is_bounded_and_other_limited_sources_keep_policy(self):
  self.assertEqual(source_policy('www.stylo.pk'),(1.5,2))
  self.assertEqual(source_policy('gulahmedshop.com'),(2.5,1))
 def test_new_stylo_profile_warms_up_before_lower_floor(self):
  gate=RequestGate(lambda:None,lambda x:None,baseline=1.5,initial_interval=2.5)
  ok=requests.Response();ok.status_code=200
  self.assertEqual(gate.interval,2.5)
  for _ in range(19):gate.response(ok)
  self.assertEqual(gate.interval,2.5)
  gate.response(ok);self.assertEqual(gate.interval,1.875)
  for _ in range(20):gate.response(ok)
  self.assertEqual(gate.interval,1.5)
 def test_throttle_persists_and_healthy_response_does_not_erase_hold(self):
  with tempfile.TemporaryDirectory() as tmp:
   path=Path(tmp)/'stylo.json';g=RequestGate(lambda:None,lambda x:None,1.5,path,initial_interval=2.5)
   r=requests.Response();r.status_code=429;r.headers['Retry-After']='120';g.response(r)
   spacing=g.interval;ok=requests.Response();ok.status_code=200
   for _ in range(40):g.response(ok)
   self.assertEqual(g.interval,spacing)
   restored=RequestGate(lambda:None,lambda x:None,1.5,path)
   self.assertTrue(restored.limited);self.assertGreater(restored.recovery_not_before,time.time())
   with self.assertRaisesRegex(RuntimeError,'SOURCE PAUSED'):restored.wait()
