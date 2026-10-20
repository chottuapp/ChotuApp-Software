import sys,unittest,subprocess
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'cloud'))
import source_research
class PublishTests(unittest.TestCase):
 def test_transient_git_push_is_retried_with_same_report(self):
  with patch.object(source_research,'_publish_once',side_effect=[subprocess.CalledProcessError(1,['git','push']),None]) as send,patch.object(source_research.time,'sleep'):
   source_research.publish({'run_id':'1'},'drive-sync-reports')
   self.assertEqual(send.call_count,2)
 def test_permanent_git_failure_is_bounded(self):
  with patch.object(source_research,'_publish_once',side_effect=subprocess.CalledProcessError(1,['git','push'])) as send,patch.object(source_research.time,'sleep'):
   with self.assertRaises(subprocess.CalledProcessError):source_research.publish({'run_id':'1'})
   self.assertEqual(send.call_count,3)
