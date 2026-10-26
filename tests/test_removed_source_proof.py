import hashlib,json,tempfile,unittest
from datetime import datetime,timezone,timedelta
from pathlib import Path
from unittest.mock import patch
from owner_product_exclusions import source_removed_rules
class RemovedSourceTests(unittest.TestCase):
 def test_only_exact_current_workbook_and_double_removed_response_are_accepted(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);source=root/'book';source.write_bytes(b'exact workbook');evidence=root/'proof.json'
   proof=dict(store='Bata',product_id='P1',source_url='https://www.bata.com.pk/products/p1',input_workbook_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),page_status=404,product_status=404,page_sha256='a'*64,product_sha256='b'*64,absent_current_public_catalog=True,checked_utc=datetime.now(timezone.utc).isoformat())
   def check(p):
    evidence.write_text(json.dumps({'products':[p]}))
    with patch('owner_product_exclusions.REMOVED_EVIDENCE',evidence):return source_removed_rules(source,'Bata')
   self.assertEqual(check(proof),{'P1':proof['source_url']})
   for changes in [{'page_status':200},{'product_status':503},{'input_workbook_sha256':'c'*64},{'absent_current_public_catalog':False},{'checked_utc':(datetime.now(timezone.utc)-timedelta(days=2)).isoformat()}]:self.assertEqual(check(dict(proof,**changes)),{})
