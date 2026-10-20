import importlib.util,unittest
from pathlib import Path
spec=importlib.util.spec_from_file_location('store_progress',Path(__file__).resolve().parents[1]/'android/app/src/main/python/store_progress.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class ProgressTests(unittest.TestCase):
 def test_stage_is_not_overall_or_product_count(self):
  p=m.parse_progress('Stage: Website listing order\npublic product pages: 550/1000 tasks')
  self.assertEqual(p['stage_percent'],55);self.assertEqual(p['remaining_tasks'],450)
  self.assertIsNone(p['products_fetched']);self.assertIsNone(p['overall_percent'])
 def test_local_discovery(self):
  p=m.parse_progress('KHAADI LISTING PROGRESS: 150/600 categories; 550 distinct product URLs')
  self.assertEqual(p['product_urls_found'],550);self.assertEqual(p['stage_percent'],25)
 def test_store_boundaries(self):
  rows=m.rows({'runs':[{'databaseId':42,'stores':{'A':'running','B':'pending'},'snapshot':'A: running\n Stage: Prices\n product prices and pages: 5/10 tasks\nB: pending'}]})
  self.assertEqual(rows[0]['completed_tasks'],5);self.assertNotIn('completed_tasks',rows[1]);self.assertEqual(rows[0]['runner_id'],'42')
 def test_invalid_total_not_percentage(self):
  self.assertIsNone(m.parse_progress('building Excel rows: 11/10')['stage_percent'])
