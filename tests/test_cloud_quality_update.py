import json,sys,tempfile,time,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'cloud'))
from diagnostics import Collector
from live_snapshot import snapshot
from store_process_worker import copy_audits

class QualityUpdateTests(unittest.TestCase):
 def test_eta_uses_task_deltas_and_resets_at_new_stage(self):
  with tempfile.TemporaryDirectory() as tmp:
   c=Collector(Path(tmp)/'telemetry.json')
   with patch('diagnostics.time.time',return_value=1000):c.observe('[Store] FAST FETCH: product prices and pages 100/1000 tasks processed; deferred=0')
   self.assertIsNone(c.stores['Store']['task_progress']['eta_seconds'])
   with patch('diagnostics.time.time',return_value=1060):
    c.observe('[Store] HTTP END status=200 elapsed=0.2s')
    c.observe('[Store] FAST FETCH: product prices and pages 200/1000 tasks processed; deferred=0')
   self.assertEqual(c.stores['Store']['task_progress']['eta_seconds'],480)
   self.assertEqual(c.stores['Store']['last_success_epoch'],1060)
   c.observe('[Store] FAST FETCH: category responses 50/500 tasks processed; deferred=0')
   self.assertIsNone(c.stores['Store']['task_progress']['eta_seconds'])
 def test_audits_follow_done_workbook_into_live_snapshot(self):
  with tempfile.TemporaryDirectory() as tmp:
   data=Path(tmp);engine=data/'runtime'/'main.py';source=engine.parent/'audit_reports'/'Store';source.mkdir(parents=True)
   (source/'Store - PRICE AUDIT.csv').write_text('product_url,status\nhttps://example.com,MATCH\n')
   (source/'private.txt').write_text('not an audit');output=data/'ANAS_DATA_FETCH';output.mkdir()
   self.assertEqual(copy_audits(engine,output,'Store'),1)
   file=output/'Store.xlsx';file.write_bytes(b'verified fixture');stat=file.stat()
   state={'sites':[{'name':'Store','status':'done','output':{'path':str(file),'size':stat.st_size,'mtime_ns':stat.st_mtime_ns}}]}
   with patch('live_snapshot.saved_state',return_value=state):snapshot(data)
   self.assertEqual((data/'live-excel'/'audits'/'Store'/'Store - PRICE AUDIT.csv').read_text(),(source/'Store - PRICE AUDIT.csv').read_text())
   self.assertFalse((data/'live-excel'/'audits'/'Store'/'private.txt').exists())
 def test_status_marks_stale_eta_unavailable(self):
  with tempfile.TemporaryDirectory() as tmp:
   data=Path(tmp);(data/'telemetry.json').write_text(json.dumps({'stores':{'Store':{'task_progress':{'stage':'product prices and pages','done':100,'total':200,'updated_epoch':time.time()-1000,'eta_seconds':100}}}}))
   with patch('live_snapshot.saved_state',return_value={'sites':[{'name':'Store','status':'running'}]}):snapshot(data)
   text=(data/'live-diagnostics'/'store-status.txt').read_text();self.assertIn('100/200 tasks',text);self.assertIn('sample stale',text);self.assertNotIn('Approximate ETA',text)
if __name__=='__main__':unittest.main()
