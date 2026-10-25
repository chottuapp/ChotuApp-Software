import json,tempfile,unittest,zipfile
from pathlib import Path
from unittest.mock import patch
import hold804_repairs
from cli import checkpoint
class RecoveryCacheTests(unittest.TestCase):
 def test_automatic_empty_facts_do_not_replace_reviewed_bundle(self):
  reviewed={'store':'Bonanza Satrangi','product_id':'p','source_url':'https://bonanzasatrangi.com/products/p','public_title':'Offer','description':'Verified bundle contents','reviewed_bundle':{'status':'active'}}
  automatic=dict(reviewed,description='',reviewed_bundle=None)
  hold804_repairs.public_index.cache_clear()
  try:
   with patch.object(Path,'exists',return_value=True),patch.object(Path,'read_text',side_effect=[json.dumps({'products':[reviewed]}),json.dumps({'products':[automatic]})]):
    self.assertEqual(hold804_repairs.public_index()[('Bonanza Satrangi','p',reviewed['source_url'])]['description'],'Verified bundle contents')
  finally:hold804_repairs.public_index.cache_clear()
 def test_checkpoint_retains_parsed_progress_and_excludes_redundant_pages(self):
  from laam_source_support import ParsedProductCache
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);data=root/'data';folder=data/'saved_runs'/'run'/'0';folder.mkdir(parents=True)
   cache=ParsedProductCache(folder/'laam-parsed.sqlite3');cache.put('https://laam.com/products/x',{'_source_url':'https://laam.com/products/x','variants':[]});cache.close()
   (folder/'pages.sqlite3').write_bytes(b'redundant raw html')
   checkpoint(data,root/'checkpoint.zip')
   with zipfile.ZipFile(root/'checkpoint.zip') as z:
    self.assertIn('saved_runs/run/0/laam-parsed.sqlite3',z.namelist());self.assertNotIn('saved_runs/run/0/pages.sqlite3',z.namelist())
   self.assertTrue((folder/'pages.sqlite3').exists())
 def test_checkpoint_keeps_raw_pages_when_no_valid_parsed_cache(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);data=root/'data';folder=data/'saved_runs'/'run'/'0';folder.mkdir(parents=True);(folder/'pages.sqlite3').write_bytes(b'only saved work')
   checkpoint(data,root/'checkpoint.zip')
   with zipfile.ZipFile(root/'checkpoint.zip') as z:self.assertIn('saved_runs/run/0/pages.sqlite3',z.namelist())
