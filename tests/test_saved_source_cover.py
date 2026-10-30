import json,tempfile,unittest,shutil
from pathlib import Path
from unittest.mock import patch
from openpyxl import Workbook
from audit804_source_refresh import saved_input_cover,capture_saved_cover
class SavedCoverTests(unittest.TestCase):
 def test_only_exact_verified_held_row_can_supply_cover(self):
  with tempfile.TemporaryDirectory() as tmp:
   source=Path(tmp)/'source.xlsx';book=Workbook();book.active.title='Products';book.active.append(['product_id','name','source_url','description','scraped_image_url (cover, auto)']);book.active.append(['P1','Exact product','https://store.example/products/one','Original source facts','https://cdn.shopify.com/one.jpg']);book.save(source)
   def restore(marker,out,store,campaign):shutil.copy2(source,out);return out
   item=dict(store='Bata',product_id='P1',name='Exact product',source_url='https://store.example/products/one',held_input='valid',campaign_id=json.loads(Path('cloud/audit804-release.json').read_text())['campaign_id'])
   with patch('audit804_queue.restore',side_effect=restore):
    url,proof=saved_input_cover(item);self.assertEqual(url,'https://cdn.shopify.com/one.jpg');self.assertTrue(proof['saved_input_verified']);self.assertEqual(len(proof['input_workbook_sha256']),64)
    for update in ({'name':'Different product'},{'source_url':'https://foreign.example/one'},{'product_id':'P2'},{'campaign_id':'old'}):
     with self.assertRaises(ValueError):saved_input_cover(dict(item,**update))
 def test_failed_checksum_does_not_allow_unverified_cover(self):
  item=dict(campaign_id=json.loads(Path('cloud/audit804-release.json').read_text())['campaign_id'],store='Bata',held_input='valid')
  with patch('audit804_queue.restore',side_effect=ValueError('Held workbook changed')):
   with self.assertRaisesRegex(ValueError,'Held workbook changed'):saved_input_cover(item)
 def test_redirect_off_image_cdn_is_rejected(self):
  from types import SimpleNamespace
  response=SimpleNamespace(url='https://foreign.example/image.jpg',content=b'image',headers={'Content-Type':'image/jpeg'},raise_for_status=lambda:None)
  session=SimpleNamespace(get=lambda *a,**k:response)
  with patch('audit804_source_refresh.saved_input_cover',return_value=('https://cdn.shopify.com/image.jpg',{})):
   with self.assertRaisesRegex(ValueError,'redirected'):capture_saved_cover({},session)
