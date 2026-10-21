"""Split an explicitly authorized saved group without restarting completed stores."""
import datetime,json,os,subprocess,tempfile,time
from pathlib import Path
from source_research import publish
from diagnostics import redact
from runner_status import select_runs
REPO='chottuapp/ChotuApp-Software'
def gh(*args):return subprocess.run(['gh',*args],capture_output=True,text=True,check=True,timeout=180).stdout

def targets(request):
 campaign=request['campaign_id'];parent=request['parent_group']
 if not parent.startswith('audit804-'+campaign+'-') or not str(request['parent_run']).isdigit():raise ValueError('Current campaign identity required')
 if request['stores']!=[{'name':'LAAM','url':'https://laam.com'},{'name':'Sapphire','url':'https://sapphireonline.pk'}]:raise ValueError('Only reviewed saved LAAM/Sapphire split authorized')
 return [(site,parent+'-'+site['name'].lower()) for site in request['stores']]

def main():
 request=json.loads((Path(__file__).parent/'paused-group-request.json').read_text());selected=targets(request)
 report={'run_id':os.environ['GITHUB_RUN_ID'],'checked_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'phase':'inspecting_saved_group','sources':[]}
 def save():publish(report,branch='laam-repair-reports')
 save()
 def runs():return json.loads(gh('run','list','--repo',REPO,'--workflow','cloud-fetch.yml','--limit','100','--json','databaseId,displayTitle,status,conclusion'))
 current=runs();lanes=select_runs(current,request['campaign_id']);existing={r['lane']:r for r in lanes}
 # Any existing split lane (including its continuation) makes repeat dispatch a no-op.
 pending=[(site,group) for site,group in selected if group not in existing]
 for site,group in selected:
  if group in existing:report['sources'].append({'name':site['name'],'status':'already_dispatched','run':existing[group]})
 if not pending:report['phase']='already_dispatched';save();return
 parent=next((r for r in lanes if r['lane']==request['parent_group']),None)
 if parent is None:raise ValueError('Requested parent group not found')
 rid=str(parent['databaseId'])
 if int(rid)<int(request['parent_run']):raise ValueError('Parent predates requested checkpoint')
 with tempfile.TemporaryDirectory() as tmp:
  gh('run','download',rid,'--repo',REPO,'--name','chotuapp-live-logs','--dir',tmp)
  for name in ('store-status.txt','console-tail.txt','fetch-log.txt'):
   paths=list(Path(tmp).rglob(name))
   if paths:
    lines=paths[0].read_text(errors='replace').splitlines();report[name]=[redact(line) for line in lines if name=='store-status.txt' or 'LAAM' in line or 'SOURCE PAUSED' in line][-90:]
 save()
 if parent['status']!='completed':
  gh('workflow','run','cloud-stop.yml','--repo',REPO,'--ref','main','-f','run_id='+rid)
  report.update(phase='waiting_for_checkpoint',parent=rid);save();deadline=time.monotonic()+480
  while time.monotonic()<deadline:
   state=json.loads(gh('run','view',rid,'--repo',REPO,'--json','status,conclusion'))
   if state['status']=='completed':break
   time.sleep(15)
  else:raise RuntimeError('Checkpoint stop not finished; no competing runners started')
 artifacts=json.loads(gh('api','repos/'+REPO+'/actions/runs/'+rid+'/artifacts?per_page=100'))['artifacts']
 if not any(a['name']=='chotuapp-checkpoint' and not a.get('expired') for a in artifacts):raise RuntimeError('Verified checkpoint absent; no from-zero restart allowed')
 # Parent may have dispatched a continuation while ending: stop rather than overlap it.
 current=runs()
 if any(r['status']!='completed' and (r['displayTitle']=='Automatic continuation of '+rid or r['displayTitle']=='Cloud group '+request['parent_group']) for r in current):raise RuntimeError('Parent lane still active; refusing competing saved workers')
 report.update(phase='resuming_saved_work',checkpoint_parent=rid);save()
 for site,group in pending:
  recent=runs()
  if any(r['displayTitle']=='Cloud group '+group for r in recent):continue
  gh('workflow','run','cloud-fetch.yml','--repo',REPO,'--ref','main','-f','resume_run_id='+rid,'-f','partition_resume=true','-f','runner_group='+group,'-f','stores='+site['name']+' | '+site['url'],'-f','minutes=300','-f','save_checkpoint=true','-f','auto_continue_limit=6','-f','auto_continue_once=false')
  record={'name':site['name'],'status':'resume_requested','group':group,'parent':rid};report['sources'].append(record);save()
  for _ in range(8):
   found=next((r for r in runs() if r['displayTitle']=='Cloud group '+group),None)
   if found:record['run']=found;break
   time.sleep(3)
 report['phase']='dispatched';save()
if __name__=='__main__':main()
