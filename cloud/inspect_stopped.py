"""Bounded credential-redacted failure evidence; no checkpoint extraction or worker mutation."""
import json,os,subprocess,tempfile,re
from pathlib import Path
from datetime import datetime,timezone
from diagnostics import redact
from source_research import publish
REPO='chottuapp/ChotuApp-Software'
def gh(*args):return subprocess.run(['gh',*args],capture_output=True,text=True,check=True,timeout=180).stdout
def evidence(text):
 lines=text.splitlines();indices=set()
 for i,line in enumerate(lines):
  if re.search(r'Traceback|(?:Error|Exception):|FAILED:|SOURCE PAUSED|SOURCE BLOCKED|exit code|No continuation:|RUN SUMMARY|Killed|out of memory',line,re.I):indices.update(range(max(0,i-7),min(len(lines),i+12)))
 return '\n'.join(redact(lines[i]) for i in sorted(indices))[-65000:]
def main():
 request=json.loads((Path(__file__).parent/'inspect-stopped-request.json').read_text());targets=request.get('run_ids') or [request['run_id']]
 if not 1<=len(targets)<=3 or not all(str(x).isdigit() for x in targets):raise ValueError('Bounded numeric targets required')
 result={'run_id':os.environ['GITHUB_RUN_ID'],'checked_utc':datetime.now(timezone.utc).isoformat(),'targets':[]}
 for rid in map(str,targets):
  record={'target':rid}
  try:
   record['state']=json.loads(gh('run','view',rid,'--repo',REPO,'--json','status,conclusion,jobs,headSha,displayTitle'))
   record['failed_log']=evidence(gh('run','view',rid,'--repo',REPO,'--log-failed'))
   artifacts=json.loads(gh('api','repos/'+REPO+'/actions/runs/'+rid+'/artifacts'))['artifacts']
   record['artifacts']=[{k:a.get(k) for k in ('name','id','expired','size_in_bytes')} for a in artifacts]
   if any(a['name']=='chotuapp-live-logs' and not a.get('expired') for a in artifacts):
    with tempfile.TemporaryDirectory() as folder:
     gh('run','download',rid,'--repo',REPO,'--name','chotuapp-live-logs','--dir',folder)
     for name in ('console-tail.txt','store-status.txt','fetch-log.txt'):
      files=list(Path(folder).rglob(name))
      if files:record[name]='\n'.join(redact(l) for l in files[0].read_text(errors='replace').splitlines()[-180:])[-26000:]
  except Exception as exc:record['diagnostic_error']=redact(str(exc))[:1000]
  result['targets'].append(record)
 publish(result,branch='stopped-fetch-reports')
if __name__=='__main__':main()
