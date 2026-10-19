import importlib.util,unittest
from pathlib import Path
from datetime import datetime,timezone,timedelta
P=Path(__file__).resolve().parents[1]/'catalog-tools/watch_all_runners_windows.py';spec=importlib.util.spec_from_file_location('all_report',P);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class CombinedReportTests(unittest.TestCase):
 def test_report_separates_runner_state_store_pause_and_snapshot_age(self):
  text='Updated (UTC): 2026-10-19T16:00:00+00:00\nSTORE STATUS\nZellbury: running\n  Stage: Product pages\n  product prices and pages: 20/100 tasks; sample age 5s\nStylo: source_paused\nKhaadi: blocked\nTea: done\n'
  now=datetime(2026,10,19,16,1,tzinfo=timezone.utc);run={'databaseId':1,'status':'in_progress','conclusion':'','displayTitle':'Group 1'}
  rendered,previous=m.render(run,text,now=now)
  self.assertIn('Group exports: 1/4',rendered);self.assertIn('Stylo: source_paused',rendered);self.assertIn('20/100',rendered);self.assertNotIn('OLD SNAPSHOT',rendered)
  later,_=m.render(run,text.replace('sample age 5s','sample age 65s'),previous,now+timedelta(minutes=16));self.assertIn('OLD SNAPSHOT',later);self.assertIn('does not prove a hang',later)
 def test_missing_or_invalid_timestamp_is_unknown(self):
  self.assertIsNone(m.report_age('nothing'));self.assertIsNone(m.report_age('Updated (UTC): invalid'))
 def test_no_store_snapshot_does_not_claim_a_hang(self):
  run={'databaseId':1,'status':'queued','displayTitle':'Group 1'};rendered,_=m.render(run,'')
  self.assertIn('setup/restore',rendered);self.assertNotIn('hung',rendered)
if __name__=='__main__':unittest.main()
