import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'cloud'))
from runner_identity import validate_runner_sources
class RunnerIdentityTests(unittest.TestCase):
 def state(self,*hosts):return {'sites':[{'name':h,'url':'https://'+h} for h in hosts]}
 def test_solo_laam_rejects_the_actual_wrong_parent(self):
  with self.assertRaisesRegex(ValueError,'RUNNER CHECKPOINT MISMATCH'):validate_runner_sources(self.state('www.gulahmedshop.com','stylo.pk'),'solo-laam')
 def test_store_label_is_not_identity_proof(self):
  state=self.state('stylo.pk');state['sites'][0]['name']='LAAM'
  with self.assertRaises(ValueError):validate_runner_sources(state,'solo-laam')
 def test_verified_single_source_and_split_lanes_are_accepted(self):
  for host,lane in [('laam.com','solo-laam'),('laam.com','split-123-laam'),('pk.sapphireonline.pk','solo-sapphire'),('pk.khaadi.com','solo-khaadi')]:validate_runner_sources(self.state(host),lane)
 def test_legacy_opaque_group_identity_is_not_guessed(self):
  validate_runner_sources(self.state('stylo.pk','www.gulahmedshop.com'),'batch-123-1')
