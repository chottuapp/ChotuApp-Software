import unittest,importlib.util,datetime
from pathlib import Path
s=importlib.util.spec_from_file_location('health_tool',Path(__file__).resolve().parents[1]/'catalog-tools/live_status.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class LiveStatusTests(unittest.TestCase):
 def test_missing_or_stale_phone_never_confirms_running(self):
  now=datetime.datetime.now(datetime.timezone.utc)
  self.assertFalse(m.phone_state({'unavailable':True},now)['status_confirmed'])
  report=m.phone_state({'observed_utc':(now-datetime.timedelta(seconds=500)).isoformat(),'status':'running'},now)
  self.assertEqual(report['status'],'unknown_stale_heartbeat');self.assertFalse(report['status_confirmed'])
 def test_recent_terminal_report_is_connected_not_running(self):
  now=datetime.datetime.now(datetime.timezone.utc);r=m.phone_state({'observed_utc':now.isoformat(),'status':'stopped','worker_active':False},now)
  self.assertTrue(r['status_confirmed']);self.assertFalse(r['worker_active'])
