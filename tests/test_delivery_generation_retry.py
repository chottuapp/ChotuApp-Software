import unittest
from audit804_delivery import retry_prior_verified_delivery
class PriorDeliveryTests(unittest.TestCase):
 def fixture(self):return dict(status='hold',audit_status='pass',delivery_status='blocked',findings_count=0,held_input='inputs/exact/manifest.json',error='Drive copy failed; category=storage_quota; upload not marked verified',refresh_generation='old')
 def test_exact_saved_audit_pass_delivery_can_retry_after_generation_change(self):
  self.assertTrue(retry_prior_verified_delivery(self.fixture(),{'refresh_generation':'old'},'new'))
 def test_fresh_verified_upload_is_never_replaced_by_old_source(self):
  self.assertFalse(retry_prior_verified_delivery(self.fixture(),{'refresh_generation':'new'},'new'))
 def test_incomplete_or_ambiguous_source_cannot_use_delivery_retry(self):
  for key,value in [('audit_status','incomplete'),('findings_count',1),('held_input',None),('error','Source identity failed'),('delivery_status','pending')]:
   r=self.fixture();r[key]=value;self.assertFalse(retry_prior_verified_delivery(r,{},'new'))

 def test_legacy_stylo_upload_failure_reenters_full_audit_only_for_exact_receipt(self):
  report=dict(status='hold',held_input='inputs/exact/manifest.json',error='Drive copyto failed; upload not marked verified',source_sha256='exact')
  receipt=dict(refresh_generation='old',source_sha256='exact',audit804={'status':'pass'})
  self.assertTrue(retry_prior_verified_delivery(report,receipt,'new'))
  for changed in (dict(receipt,source_sha256='newer'),dict(receipt,refresh_generation='new'),dict(receipt,audit804={'status':'hold'})):
   self.assertFalse(retry_prior_verified_delivery(report,changed,'new'))
  self.assertFalse(retry_prior_verified_delivery(dict(report,findings=[{'issues':['unresolved']}]),receipt,'new'))
