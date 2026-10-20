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

def select_runs(runs):
 lanes={}
 for r in reversed(runs):
  title=r.get('displayTitle','')
  if title.startswith('Cloud group '):lanes[str(r['databaseId'])]=title.removeprefix('Cloud group ')
  elif title.startswith('Automatic continuation of '):lanes[str(r['databaseId'])]=lanes.get(title.split()[-1],title)
 selected=[];seen=set()
 for r in runs:
  lane=lanes.get(str(r['databaseId']),r.get('displayTitle',''))
  if lane in seen:continue
  seen.add(lane)
  if r['status']!='completed' or lane.startswith(('fresh26-39450710625-','solo-laam','solo-sapphire')):
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
 for run in select_runs(runs):
  item=dict(run)
  with tempfile.TemporaryDirectory() as tmp:
   try:
    gh('run','download',str(run['databaseId']),'--repo',REPO,'--name','chotuapp-live-logs','--dir',tmp)
    paths=list(Path(tmp).rglob('store-status.txt'))
    if len(paths)!=1:raise ValueError('Snapshot unavailable')
    text=paths[0].read_text(encoding='utf-8',errors='replace')[:65536];updated,stores=parse_snapshot(text)
    item.update(snapshot=text,snapshot_utc=updated,stores=stores)
    if updated:
     item['snapshot_age_seconds']=round((now-datetime.datetime.fromisoformat(updated)).total_seconds())
     item['snapshot_stale']=item['snapshot_age_seconds']>600
    if run['lane'].startswith('fresh26-39450710625-'):report['fresh_stores'].update(stores)
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
  report['drive']={'verified_files':len(drive.get('uploaded',{})),'verified_utc':drive.get('verified_utc'),'folders':{k:len(v) for k,v in drive.get('daily_uploads',{}).items()},'latest_move':drive.get('moves',[])[-1:]}
 except (RuntimeError,ValueError,KeyError):report['drive']={'status':'unavailable; not claimed verified'}
 report['fresh_completed']=sum(v=='done' for v in report['fresh_stores'].values())
 publish(report,branch='runner-status-reports')
 print('Active/queued:',report['active_queued'],'| fresh done:',report['fresh_completed'],'| cloud checked:',report['checked_utc'])
if __name__=='__main__':main()
