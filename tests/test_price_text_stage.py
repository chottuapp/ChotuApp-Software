import importlib.util,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import requests
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'cloud'))
from diagnostics import Collector
spec=importlib.util.spec_from_file_location('price_text_main',ROOT/'main.py');main=importlib.util.module_from_spec(spec);spec.loader.exec_module(main)
class PriceStageTests(unittest.TestCase):
 def test_space_after_rupee_label_parses_without_changing_exported_price(self):
  for text in ['Rs. 593.40','Rs 593.40','Rs.593.40','PKR 593.40']:
   response=requests.Response();response.status_code=200;response._content=('<span class="price-item--sale">'+text+'</span>').encode();response.encoding='utf-8'
   with tempfile.TemporaryDirectory() as tmp,patch.object(main.requests,'Session') as session,patch.object(main,'_chotu_backoff'):
    session.return_value.get.return_value=response
    row={'source_url':'https://store.example/products/test','base_price (PKR)':690,'sale_price (PKR, agar discount ho)':593.40}
    before=dict(row);file=Path(tmp)/'audit.csv';main.storefront_price_audit([row],file,lambda x:None)
    self.assertIn('EXACT_DISPLAY_MATCH',file.read_text());self.assertEqual(row,before)
 def test_new_build_stage_clears_old_prefetch_eta(self):
  with tempfile.TemporaryDirectory() as tmp:
   c=Collector(Path(tmp)/'telemetry.json');c.observe('[Store] FAST FETCH: product prices and pages 4800/4807 tasks processed; deferred=0')
   self.assertIn('task_progress',c.stores['Store'])
   c.observe('[Store] [00:38:01] STAGE: Building Excel rows')
   self.assertNotIn('task_progress',c.stores['Store']);self.assertEqual(c.stores['Store']['current_stage'],'Building Excel rows')
if __name__=='__main__':unittest.main()
