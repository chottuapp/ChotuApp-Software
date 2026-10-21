"""Publish bounded credential-free cloud progress; never claim local process visibility."""
import base64,datetime,json,os,re,subprocess,sys,tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from source_research import publish
REPO='chottuapp/ChotuApp-Software'
def gh(*args):
 r=subprocess.run(['gh',*args],capture_output=True,text=True,timeout=180)
 if r.returncode:raise RuntimeError('GitHub '+args[0]+' unavailable')
 return r.stdout

def phone_connection(reports):
 phone=next((row for row in reports if row.get('execution')=='Android app'),None)
 if phone is None:return {'status':'not_connected_or_no_report','status_confirmed':False,'message':'No Android heartbeat received. Connect GitHub in app Settings and start or resume fetching.'}
 if not phone.get('status_confirmed'):return {'status':'heartbeat_stale','status_confirmed':False,'observed_utc':phone.get('observed_utc'),'message':'Phone heartbeat is stale; running or stopped cannot be confirmed.'}
 return {'status':'connected','status_confirmed':True,'worker_active':phone.get('worker_active'),'worker_status':phone.get('status'),'observed_utc':phone.get('observed_utc'),'progress_age_seconds':phone.get('progress_age_seconds'),'message':'Recent phone report received; heartbeat does not itself prove product progress.'}

def select_runs(runs,campaign=None):
 lanes={}
 for r in reversed(runs):
  title=r.get('displayTitle','')
  if title.startswith('Cloud group '):lanes[str(r['databaseId'])]=title.removeprefix('Cloud group ')
  elif title.startswith('Automatic continuation of '):lanes[str(r['databaseId'])]=lanes.get(title.split()[-1],title)
 selected=[];seen=set()
 for r in runs:
  lane=lanes.get(str(r['databaseId']),r.get('displayTitle',''))
  if campaign and not lane.startswith('audit804-'+campaign+'-'):continue
  if lane in seen:continue
  seen.add(lane)
  if r['status']!='completed' or campaign or lane.startswith(('fresh26-39450710625-','solo-laam','solo-sapphire')):
   selected.append(dict(r,lane=lane))
 return selected[:20]

def parse_snapshot(text):
 result={};updated=None
 for line in text.splitlines():
  if line.startswith('Updated (UTC): '):updated=line.split(': ',1)[1]
  m=re.fullmatch(r'([^:]+): (done|running|pending|failed|blocked|source_paused)',line.strip())
  if m:result[m[1]]=m[2]
 return updated,result

def main():
 now=datetime.datetime.now(datetime.timezone.utc)
 runs=json.loads(gh('run','list','--repo',REPO,'--workflow','cloud-fetch.yml','--limit','100','--json','databaseId,displayTitle,status,conclusion,updatedAt,url'))
 report={'run_id':os.environ['GITHUB_RUN_ID'],'checked_utc':now.isoformat(),'active_queued':sum(r['status']!='completed' for r in runs),'runs':[],'fresh_stores':{},'local_khaadi':'Not visible to cloud monitoring; no local activity claimed'}
 policy=json.loads((Path(__file__).parent/'drive-sync-release.json').read_text());campaign=policy.get('dispatcher') if policy.get('audit804_enabled') else None
 for run in select_runs(runs,campaign):
  item=dict(run)
  with tempfile.TemporaryDirectory() as tmp:
   try:
    gh('run','download',str(run['databaseId']),'--repo',REPO,'--name','chotuapp-live-logs','--dir',tmp)
    paths=list(Path(tmp).rglob('store-status.txt'))
    if len(paths)!=1:raise ValueError('Snapshot unavailable')
    text=paths[0].read_text(encoding='utf-8',errors='replace')[:65536];updated,stores=parse_snapshot(text)
    item.update(snapshot=text,snapshot_utc=updated,stores=stores)
    if updated:
     item['snapshot_age_seconds']=max(0,round((now-datetime.datetime.fromisoformat(updated)).total_seconds()))
     item['snapshot_stale']=item['snapshot_age_seconds']>600
    if 'LAAM' in stores and run['status']!='completed':
     from diagnostics import redact
     for filename in ('console-tail.txt','fetch-log.txt'):
      logs=list(Path(tmp).rglob(filename))
      if logs:item[filename]=[redact(line) for line in logs[0].read_text(encoding='utf-8',errors='replace').splitlines()[-70:]]
    if run['lane'].startswith('fresh26-39450710625-') or campaign and run['lane'].startswith('audit804-'+campaign+'-'):
     current_stores={store:status for store,status in stores.items() if store not in report['fresh_stores']}
     item['stores']=current_stores
     report['fresh_stores'].update(current_stores)
   except (RuntimeError,OSError,ValueError):item['snapshot_unavailable']=True
  if run.get('conclusion')=='failure':
   try:
    lines=gh('run','view',str(run['databaseId']),'--repo',REPO,'--log-failed').splitlines();indices=set()
    for index,line in enumerate(lines):
     if re.search(r'EXCEPTION|RuntimeError:|ValueError:|ADAPTER ERROR|SOURCE BLOCKED|##\[error\]',line):indices.update(range(max(0,index-5),min(len(lines),index+3)))
    from diagnostics import redact
    item['failure_details']=[redact(lines[i]) for i in sorted(indices)][-80:]
   except RuntimeError:item['failure_details_unavailable']=True
  report['runs'].append(item)
 try:
  response=json.loads(gh('api','repos/'+REPO+'/contents/latest.json?ref=drive-sync-reports'))
  drive=json.loads(base64.b64decode(response['content']))
  report['drive']={'sync_status':drive.get('sync_status'),'sync_error':drive.get('sync_error'),'last_scan_utc':drive.get('last_scan_utc'),'held':drive.get('held',{}),'verified_files':len(drive.get('uploaded',{})),'original_uploads':drive.get('original_uploads',{}),'verified_utc':drive.get('verified_utc'),'folders':{k:len(v) for k,v in drive.get('daily_uploads',{}).items()},'latest_move':drive.get('moves',[])[-1:]}
 except (RuntimeError,ValueError,KeyError):report['drive']={'status':'unavailable; not claimed verified'}
 local_reports=[]
 for filename in ('khaadi.json','khaadi-android.json'):
  try:
   response=json.loads(gh('api','repos/'+REPO+'/contents/local/'+filename+'?ref=local-run-status'))
   local=json.loads(base64.b64decode(response['content']));age=(datetime.datetime.now(datetime.timezone.utc)-datetime.datetime.fromisoformat(local['observed_utc'])).total_seconds()
   local['report_age_seconds']=max(0,round(age));local['status_confirmed']=0<=age<=180
   if age>180:local['status']='unknown_stale_heartbeat'
   local_reports.append(local)
  except (RuntimeError,ValueError,KeyError):pass
 if local_reports:
  report['local_khaadi']=max(local_reports,key=lambda row:datetime.datetime.fromisoformat(row['observed_utc']))
  report['khaadi_devices']=local_reports
 report['phone_heartbeat']=phone_connection(local_reports)
 report['monitoring']={'phone_heartbeat_seconds':30,'phone_stale_after_seconds':180,'cloud_schedule_minutes':5,'note':'Scheduled cloud checks can be delayed. Query local-run-status directly for latest phone heartbeat.'}
 report['fresh_completed']=sum(v=='done' for v in report['fresh_stores'].values())
 publish(report,branch='runner-status-reports')
 print('Active/queued:',report['active_queued'],'| fresh done:',report['fresh_completed'],'| cloud checked:',report['checked_utc'])
if __name__=='__main__':main()
