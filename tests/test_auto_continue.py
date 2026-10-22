import sys,unittest,json,os,tempfile
from unittest.mock import patch
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'cloud'))
from auto_continue import eligible,main
class ContinueTests(unittest.TestCase):
 def setUp(self):
  self.run={'id':38970499270,'event':'workflow_dispatch','head_branch':'main','head_repository':{'full_name':'owner/repo'},'conclusion':'failure'}
  self.summary={'status':'incomplete','checkpoint':'saved','stores':[{'status':'pending'}]}
 def test_existing_authorized_run_uses_budget_message(self):
  self.assertTrue(eligible(self.run,'owner/repo',self.summary,'Cloud time budget reached; saving unfinished work.',True))
 def test_manual_stop_no_checkpoint_and_source_failure_do_not_chain(self):
  for checkpoint,console in [(False,'Cloud time budget reached; saving unfinished work.'),(True,'Stopped on request'),(True,'Source blocked')]:self.assertFalse(eligible(self.run,'owner/repo',self.summary,console,checkpoint))
 def test_child_does_not_chain_unless_explicitly_authorized(self):
  self.run['id']=123;self.summary['stop_reason']='time_budget';self.summary['auto_continue_once']=False
  self.assertFalse(eligible(self.run,'owner/repo',self.summary,'',True));self.summary['auto_continue_once']=True;self.assertTrue(eligible(self.run,'owner/repo',self.summary,'',True))
 def test_completed_cancelled_and_forks_do_not_chain(self):
  self.summary['auto_continue_once']=True;self.summary['stop_reason']='time_budget'
  self.summary['status']='complete';self.assertFalse(eligible(self.run,'owner/repo',self.summary,'',True));self.summary['status']='incomplete'
  self.run['conclusion']='cancelled';self.assertFalse(eligible(self.run,'owner/repo',self.summary,'',True));self.run['conclusion']='failure'
  self.run['head_repository']['full_name']='fork/repo';self.assertFalse(eligible(self.run,'owner/repo',self.summary,'',True))
 def test_dispatch_is_bounded_and_duplicate_is_skipped(self):
  for duplicate in (False,True):
   with tempfile.TemporaryDirectory() as tmp:
    event=Path(tmp)/'event.json';event.write_text(json.dumps({'workflow_run':self.run}));calls=[]
    def fake(*args):
     calls.append(args)
     if args[0]=='api':return json.dumps({'artifacts':[{'name':'chotuapp-checkpoint','expired':False}]})
     if args[:2]==('run','download'):
      folder=Path(args[args.index('--dir')+1]);folder.mkdir()
      summary=dict(self.summary,stop_reason='time_budget');(folder/'run-summary.json').write_text(json.dumps(summary));return ''
     if args[:2]==('run','list'):return json.dumps([{'displayTitle':'Automatic continuation of 38970499270'}] if duplicate else [])
     return ''
    with patch.dict(os.environ,{'GITHUB_EVENT_PATH':str(event),'GITHUB_REPOSITORY':'owner/repo'}),patch('sys.argv',['auto_continue.py']),patch('auto_continue.gh',side_effect=fake):main()
    dispatched=[c for c in calls if c[:2]==('workflow','run')]
    self.assertEqual(len(dispatched),0 if duplicate else 1)
    if dispatched:
     self.assertIn('auto_continue_once=false',dispatched[0]);self.assertIn('minutes=300',dispatched[0]);self.assertIn('resume_run_id=38970499270',dispatched[0])
if __name__=='__main__':unittest.main()

class CheckpointIntervalTests(unittest.TestCase):
 def test_short_interval_survives_continuations_with_validated_defaults(self):
  from auto_continue import run_minutes
  self.assertEqual(run_minutes({'continuation_minutes':90}),90)
  for value in (0,10,301,'bad',None):self.assertEqual(run_minutes({'continuation_minutes':value}),300)
  self.assertEqual(run_minutes({}),300)
