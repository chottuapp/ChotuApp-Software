"""Collect bounded, redacted original-lane failures using Actions' existing token."""
import json,os,subprocess,re
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
 code,out,err=call('run','view',rid,'--repo',REPO,'--log-failed');lines=(out or err).splitlines();selected=set()
 for i,line in enumerate(lines):
  if re.search(r'EXCEPTION|Traceback|Error:|RuntimeError|FAILED:|##\[error\]|SOURCE PAUSED|ADAPTER ERROR',line):selected.update(range(max(0,i-12),min(len(lines),i+16)))
 item['failed_log_tail']=[redact(lines[i]) for i in sorted(selected)[:320]] or [redact(line) for line in lines[-80:]]
 report['failures'].append(item)
publish(report,branch='laam-repair-reports');print(json.dumps(report,indent=2))
