import json,os,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'cloud'))
from remote_control import check_stop_request
class ControlTests(unittest.TestCase):
 def test_only_successful_matching_stop_is_accepted(self):
  with tempfile.TemporaryDirectory() as tmp,patch.dict(os.environ,{'GITHUB_RUN_ID':'123','GITHUB_REPOSITORY':'owner/repo','GH_TOKEN':'test'}):
   for title,conclusion,expected in [('Save and stop 456','success',False),('Save and stop 123','failure',False),('Save and stop 123','success',True)]:
    with patch('remote_control.subprocess.run') as run:
     run.return_value.stdout=json.dumps([{'displayTitle':title,'conclusion':conclusion}])
     self.assertEqual(check_stop_request(tmp),expected)
   self.assertTrue((Path(tmp)/'stop-request').exists())
 def test_missing_credentials_does_not_stop_work(self):
  with tempfile.TemporaryDirectory() as tmp,patch.dict(os.environ,{'GH_TOKEN':''}):self.assertFalse(check_stop_request(tmp))
if __name__=='__main__':unittest.main()
