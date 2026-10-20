"""Read transfer status without changing files or credentials."""
import os,json,subprocess,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from source_research import publish
from diagnostics import redact
repo='chottuapp/ChotuApp-Software';rid='39476735167'
r=subprocess.run(['gh','run','view',rid,'--repo',repo,'--json','status,conclusion,jobs'],capture_output=True,text=True,timeout=120)
report={'run_id':os.environ['GITHUB_RUN_ID'],'source_run':rid,'result':json.loads(r.stdout) if r.returncode==0 else redact(r.stderr)}
if isinstance(report['result'],dict) and report['result'].get('status')=='completed':
 r=subprocess.run(['gh','run','view',rid,'--repo',repo,'--log-failed'],capture_output=True,text=True,timeout=120)
 report['failed_log']=[redact(s) for s in (r.stdout or r.stderr).splitlines()][-60:]
publish(report,branch='fetch-update-reports')
