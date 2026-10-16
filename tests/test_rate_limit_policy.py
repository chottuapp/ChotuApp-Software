import unittest
from fast_fetch_support import source_policy,RequestGate
class PolicyTests(unittest.TestCase):
 def test_observed_limited_hosts_start_with_one_worker(self):
  for host in ['rawayat.com.pk','rivaj-uk.com','www.junaidjamshed.com','tawakkalfabrics.co']:
   self.assertEqual(source_policy(host),(1.0,1))
  self.assertEqual(source_policy('vincecare.com'),(.25,5))
 def test_cautious_floor_does_not_erase_existing_slowdown(self):
  import tempfile,json
  from pathlib import Path
  with tempfile.TemporaryDirectory() as tmp:
   path=Path(tmp)/'state.json';path.write_text(json.dumps({'min_spacing':4.5,'recovery_not_before_epoch':9999999999}))
   gate=RequestGate(lambda:None,lambda x:None,source_policy('rivaj-uk.com')[0],path)
   self.assertEqual(gate.interval,4.5)
if __name__=='__main__':unittest.main()
