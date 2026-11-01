"""Exercise the actual Actions entrypoint without test-runner import paths."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ContinuationEntrypointTests(unittest.TestCase):
 def test_complete_fetch_exits_successfully_without_dispatch_or_pythonpath(self):
  with tempfile.TemporaryDirectory() as tmp:
   folder=Path(tmp);data=folder/'data';(data/'ANAS_DATA_FETCH').mkdir(parents=True)
   (data/'fetch-phase.json').write_text(json.dumps(dict(phase='finished',checkpoint='saved')))
   (data/'ANAS_DATA_FETCH'/'run-summary.json').write_text(json.dumps(dict(status='complete',checkpoint='saved',stores=[dict(name='Habitt',url='https://habitt.com',status='done')],auto_continue_limit=4)))
   run=dict(id=123,event='workflow_dispatch',head_branch='main',head_repository=dict(full_name='owner/repo'),head_sha='abc',conclusion=None)
   fake=folder/'gh'
   fake.write_text('#!'+sys.executable+'\nimport json,sys\n'
    +'if sys.argv[1]!="api": raise SystemExit("Unexpected dispatch")\n'
    +'print(json.dumps('+repr(dict(artifacts=[dict(name='chotuapp-checkpoint',expired=False)]))+' if "artifacts" in sys.argv[2] else '+repr(run)+'))\n')
   fake.chmod(0o700)
   env=dict(os.environ,GITHUB_RUN_ID='123',GITHUB_REPOSITORY='owner/repo',GITHUB_EVENT_NAME='workflow_dispatch',GITHUB_SHA='abc',CHOTUAPP_CLOUD_DATA=str(data),PATH=str(folder)+os.pathsep+os.environ['PATH'])
   env.pop('PYTHONPATH',None)
   result=subprocess.run([sys.executable,str(ROOT/'cloud/auto_continue.py'),'--current-run'],cwd=folder,env=env,capture_output=True,text=True,timeout=20)
   self.assertEqual(result.returncode,0,result.stderr)
   self.assertIn('No continuation:',result.stdout)
