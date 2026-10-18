import contextlib,io,json,os,sys,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'cloud'))
import fetch_update_release as release
class ReleaseTests(unittest.TestCase):
 def invoke(self,validation,result=None):
  reports=[]
  with patch.dict(os.environ,{'GITHUB_RUN_ID':'123456','GITHUB_SHA':'a'*40}),patch.object(sys,'argv',['release','--validation',validation]),patch.object(release,'publish',side_effect=lambda report,branch:reports.append((report,branch))),patch.object(release.subprocess,'run',return_value=result) as command,contextlib.redirect_stdout(io.StringIO()):
   if validation!='success' or result.returncode:
    with self.assertRaises(SystemExit):release.main()
   else:release.main()
  return reports,command
 def test_failed_validation_never_resumes_a_fetch(self):
  reports,command=self.invoke('failure');command.assert_not_called();self.assertEqual(reports[0][0]['dispatch'],'not_requested')
 def test_success_dispatches_exact_checkpoint_with_bounded_continuation(self):
  reports,command=self.invoke('success',SimpleNamespace(returncode=0,stdout='https://github.com/chottuapp/ChotuApp-Software/actions/runs/987654',stderr=''))
  args=command.call_args.args[0];self.assertTrue(any(x.startswith('stores=') and 'Zero Lifestyle' in x for x in args));self.assertFalse(any(x.startswith('resume_run_id=') for x in args));self.assertIn('auto_continue_limit=6',args);self.assertEqual(reports[0][0]['fetch_run_id'],'987654');self.assertEqual(reports[0][1],'fetch-update-reports')
 def test_cli_error_is_not_published_as_arbitrary_output(self):
  reports,_=self.invoke('success',SimpleNamespace(returncode=1,stdout='',stderr='private credential value'));self.assertNotIn('private credential',json.dumps(reports));self.assertEqual(reports[0][0]['dispatch'],'failed')
if __name__=='__main__':unittest.main()
