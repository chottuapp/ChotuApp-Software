import json,os,subprocess,unittest
from unittest.mock import patch
import fresh804_dispatch as dispatcher
class DispatchReporting(unittest.TestCase):
 def test_report_failure_does_not_stop_fetch_dispatch_or_duplicate_existing_lane(self):
  config=json.loads((dispatcher.ROOT/'cloud/audit804-release.json').read_text());title='Cloud group '+dispatcher.lane_prefix(config)+'1';calls=[]
  def gh(*args):
   if args[:2]==('run','list'):return json.dumps([{'databaseId':1,'displayTitle':title,'status':'in_progress'}])
   calls.append(args);return ''
  sites=[{'name':'A','url':'https://a.example'},{'name':'B','url':'https://b.example'},{'name':'C','url':'https://c.example'}]
  with patch.dict(os.environ,{'GITHUB_RUN_ID':'123'}),patch.object(dispatcher,'selected_sites',return_value=sites),patch.object(dispatcher,'gh',side_effect=gh),patch.object(dispatcher,'publish',side_effect=subprocess.CalledProcessError(1,['git','push'])):
   dispatcher.main()
  self.assertEqual(len(calls),1);self.assertIn('runner_group='+dispatcher.lane_prefix(config)+'2',calls[0])
