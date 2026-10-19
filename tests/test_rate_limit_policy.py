import unittest
from fast_fetch_support import source_policy,RequestGate
class PolicyTests(unittest.TestCase):
 def test_observed_limited_hosts_start_with_one_worker(self):
  for host in ['rawayat.com.pk','rivaj-uk.com','www.junaidjamshed.com','tawakkalfabrics.co']:
   self.assertEqual(source_policy(host),(1.0,1))
  for host in ['vincecare.com','saeedghani.pk','pk.hemaniherbals.com','bonanzasatrangi.com','www.gulahmedshop.com','stylo.pk']:
   self.assertEqual(source_policy(host),(2.5,1))
  for host in ('outfitters.com.pk','www.zellbury.com'):self.assertEqual(source_policy(host),(1.5,1))
 def test_cautious_floor_does_not_erase_existing_slowdown(self):
  import tempfile,json
  from pathlib import Path
  with tempfile.TemporaryDirectory() as tmp:
   path=Path(tmp)/'state.json';path.write_text(json.dumps({'min_spacing':4.5,'recovery_not_before_epoch':9999999999}))
   gate=RequestGate(lambda:None,lambda x:None,source_policy('rivaj-uk.com')[0],path)
   self.assertEqual(gate.interval,4.5)
 def test_new_limited_hosts_raise_old_fast_profiles_without_erasing_cooldown(self):
  import tempfile,json,time
  from pathlib import Path
  with tempfile.TemporaryDirectory() as tmp:
   for host in ('gulahmedshop.com','stylo.pk'):
    path=Path(tmp)/host;deadline=time.time()+240
    path.write_text(json.dumps({'min_spacing':0.45,'retry_after_epoch':deadline,'recovery_not_before_epoch':deadline+1800}))
    gate=RequestGate(lambda:None,lambda x:None,source_policy(host)[0],path)
    self.assertEqual(gate.interval,2.5);self.assertTrue(gate.limited)
    self.assertGreater(gate.cooldown-time.monotonic(),230)
    gate.response(type('Response',(),{'status_code':200})())
    self.assertTrue(gate.limited);self.assertEqual(gate.interval,2.5)
if __name__=='__main__':unittest.main()
