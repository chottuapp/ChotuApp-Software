import datetime,json,os,subprocess
from source_research import publish
from diagnostics import redact
REPO='chottuapp/ChotuApp-Software'
def gh(*args):
 r=subprocess.run(['gh',*args],text=True,capture_output=True,timeout=180)
 if r.returncode:raise RuntimeError('Build diagnostic lookup unavailable')
 return r.stdout
runs=json.loads(gh('run','list','--repo',REPO,'--workflow','android-apk.yml','--limit','1','--json','databaseId,status,conclusion,headSha,url'))
report={'run_id':os.environ['GITHUB_RUN_ID'],'checked_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'build':runs[0] if runs else None}
if runs:
 rid=str(runs[0]['databaseId']);report['jobs']=json.loads(gh('api','repos/'+REPO+'/actions/runs/'+rid+'/jobs'))['jobs']
 if runs[0]['status']=='completed' and runs[0]['conclusion']=='failure':report['failure_logs']='\n'.join(redact(s) for s in gh('run','view',rid,'--repo',REPO,'--log-failed').splitlines()[-230:])
if runs and runs[0].get('conclusion')=='failure':
 report['signing_cache_diagnostics']={}
 for rid in ('39502748759',str(runs[0]['databaseId'])):
  try:
   lines=gh('run','view',rid,'--repo',REPO,'--log').splitlines();indices=set()
   for index,line in enumerate(lines):
    if any(word in line for word in ('debug.keystore','chotuapp-preview-signing','Cache not found','Cache saved with key','Cache restored successfully')):indices.update(range(max(0,index-2),min(len(lines),index+3)))
   report['signing_cache_diagnostics'][rid]=[redact(lines[i]) for i in sorted(indices)][-90:]
  except RuntimeError:pass
 try:report['signing_caches']=json.loads(gh('api','repos/'+REPO+'/actions/caches?key=chotuapp-preview-signing-v1&per_page=100'))
 except RuntimeError:pass
publish(report,branch='android-build-reports')
