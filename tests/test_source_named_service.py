import unittest
from unittest.mock import patch
from hold804_repairs import category,description
from audit804 import issues_for
from audit804_semantics import review

class SourceNamedServiceTests(unittest.TestCase):
 def row(self):return dict(name='TEST-STICHING SERVICE',description='TEST-STICHING SERVICE',product_id='CP2f95fef50699',source_url='https://www.beyondeast.com/products/test-stiching-service')
 def test_exact_public_service_retains_test_qualification_without_fulfilment_claims(self):
  row=self.row()
  with patch('hold804_repairs.public_facts',return_value=dict(public_title=row['name'])):
   fixed,reason=description(row,'Beyond East');label=category(row,'Beyond East')[0]
  self.assertEqual(label,'Stitching Services');self.assertEqual(fixed,'A test listing for a stitching service.');self.assertTrue(reason)
  self.assertEqual(issues_for(dict(row,description=fixed,Category=label),row),[])
  self.assertNotRegex(fixed,r'(?i)custom size|fabric|delivery|warranty|tailored|ready.to.wear')
 def test_missing_public_identity_cannot_clear_hold(self):
  with patch('hold804_repairs.public_facts',return_value=None):
   row=self.row();self.assertEqual(description(row,'Beyond East'),(row['description'],None));self.assertIsNone(category(row,'Beyond East'))
 def test_auditor_rejects_removing_test_label_or_reclassifying_other_objects(self):
  self.assertNotEqual(review('TEST-STICHING SERVICE','A listing for a stitching service.','Stitching Services'),[])
  self.assertNotEqual(review('Stitching Machine','A sewing machine with accessories.','Stitching Services'),[])
if __name__=='__main__':unittest.main()
