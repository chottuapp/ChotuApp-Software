import unittest,json,copy
from datetime import datetime,timezone,timedelta
from pathlib import Path
from unittest.mock import patch
from owner_product_exclusions import out_of_stock_rules
class LiveStockExclusionTests(unittest.TestCase):
 def setUp(self):
  self.record=json.loads(Path('cloud/audit804-stock-exclusions.json').read_text())['products'][0]
  self.record['checked_utc']=datetime.now(timezone.utc).isoformat()
 def rules(self,record):
  with patch('owner_product_exclusions.json.loads',return_value={'products':[record]}):return out_of_stock_rules('Gul Ahmed')
 def test_only_all_explicitly_unavailable_variants_qualify(self):
  self.assertIn(self.record['product_id'],self.rules(self.record))
  for value in [True,None]:
   changed=copy.deepcopy(self.record);changed['product']['variants'][0]['available']=value
   self.assertEqual(self.rules(changed),{})
 def test_expired_or_mismatched_endpoint_cannot_exclude(self):
  changed=copy.deepcopy(self.record);changed['checked_utc']=(datetime.now(timezone.utc)-timedelta(days=2)).isoformat();self.assertEqual(self.rules(changed),{})
  changed=copy.deepcopy(self.record);changed['endpoint']='https://other.example/item.js';self.assertEqual(self.rules(changed),{})
