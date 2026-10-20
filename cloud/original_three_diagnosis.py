"""Collect bounded, redacted original-lane failures using Actions' existing token."""
import json,os,subprocess
from diagnostics import redact
from source_research import publish
REPO='chottuapp/ChotuApp-Software'
def call(*args):
 r=subprocess.run(['gh',*args],capture_output=True,text=True,timeout=180)
 return r.returncode,r.stdout,r.stderr
report={'run_id':os.environ['GITHUB_RUN_ID'],'failures':[]}
for store,rid in [('LAAM','39410937297'),('Sapphire','39414516183')]:
 code,out,err=call('run','view',rid,'--repo',REPO,'--json','status,conclusion,jobs,headSha')
 item={'store':store,'source_run':rid,'run':json.loads(out) if not code else {'error':redact(err)}}
 code,out,err=call('run','view',rid,'--repo',REPO,'--log-failed');item['failed_log_tail']=[redact(line) for line in (out or err).splitlines()[-170:]]
 report['failures'].append(item)
publish(report,branch='laam-repair-reports');print(json.dumps(report,indent=2))
