"""Explicit one-time fresh restart: save/stop prior fetches, then at most three stores per runner."""
import json,os,subprocess,time
from pathlib import Path
from datetime import datetime,timezone
from group_fetch import groups
from fetch_update_release import stop_previous
from source_research import publish
ROOT=Path(__file__).resolve().parents[1];REPO='chottuapp/ChotuApp-Software'
def gh(*args):return subprocess.run(['gh',*args],capture_output=True,text=True,check=True,timeout=90).stdout

def selected_sites(registry,request):
 if not 1<=len(registry)<=40 or len({row['name'] for row in registry})!=len(registry):raise ValueError('Unique approved registry stores required')
 excluded=set(request.get('excluded_stores',[]))
 if request.get('khaadi_fresh_enabled') is False:excluded.add('Khaadi')
 if not excluded<={row['name'] for row in registry}:raise ValueError('Unknown excluded store')
 sites=[row for row in registry if row['name'] not in excluded]
 if not sites:raise ValueError('No stores selected for fresh fetching')
 return sites

def planned_groups(sites,request):
 remaining=[site for site in sites if site['name'] not in request.get('completed_stores',[])]
 if request.get('maximum_stores_per_runner')==1:return [[site] for site in remaining]
 return groups(remaining) if remaining else []

def main():
 request=json.loads((ROOT/'cloud/audit804-release.json').read_text());campaign=request['campaign_id'];prefix='Cloud group audit804-'+campaign+('-solo-' if request.get('runner_plan')=='solo' else '-')
 registry=json.loads((ROOT/'cloud/fetch-update-release.json').read_text())['fresh_stores']
 sites=selected_sites(registry,request)
 if request.get('maximum_stores_per_runner') not in (1,3) or request.get('destination_folder')!='ChotuApp 19-10-2026 11-36AM':raise ValueError('Unexpected requested fresh policy')
 report={'run_id':os.environ['GITHUB_RUN_ID'],'campaign_id':campaign,'checked_utc':datetime.now(timezone.utc).isoformat(),'groups':[],'phone':{'store':'Khaadi','status':'cloud_fresh_attempt_requested_no_phone_required' if any(site['name']=='Khaadi' for site in sites) else 'excluded_by_owner_request','fresh_campaign_id':campaign},'stopped':[]}
 publish(report,branch='fetch-update-reports')
 # Block old auto-continuation roots, including already running jobs that use old source code.
 def runs():return json.loads(gh('run','list','--repo',REPO,'--workflow','cloud-fetch.yml','--limit','100','--json','databaseId,displayTitle,status'))
 for _ in range(3):
  current=runs();owned={str(run['databaseId']) for run in current if run.get('displayTitle','').startswith(prefix)}
  for _parent in current:
   more={str(run['databaseId']) for run in current if run.get('displayTitle','').startswith('Automatic continuation of ') and run['displayTitle'].split()[-1] in owned}
   if more<=owned:break
   owned.update(more)
  active=[run for run in current if run['status']!='completed' and str(run['databaseId']) not in owned]
  if not active:break
  for run in active:
   stop_previous(str(run['databaseId']));report['stopped'].append(str(run['databaseId']));publish(report,branch='fetch-update-reports')
 else:raise RuntimeError('Old fetching still active; fresh dispatch withheld')
 existing=runs()
 plan=planned_groups(sites,request)
 for index,stores in enumerate(plan,1):
  lane='audit804-'+campaign+('-solo-' if request.get('runner_plan')=='solo' else '-')+str(index);title='Cloud group '+lane
  item={'runner_group':lane,'stores':stores,'status':'already_dispatched' if any(run['displayTitle']==title for run in existing) else 'pending'};report['groups'].append(item)
  if item['status']=='pending':
   resume=request.get('resume_sources',{}).get(stores[0]['name']) if len(stores)==1 else None
   extra=['-f','resume_run_id='+str(resume),'-f','partition_resume=true'] if resume else []
   gh('workflow','run','cloud-fetch.yml','--repo',REPO,'--ref','main','-f','stores='+json.dumps(stores,separators=(',',':')),'-f','runner_group='+lane,'-f','minutes='+str(request.get('fetch_segment_minutes',90)),'-f','save_checkpoint=true','-f','auto_continue_limit=48','-f','auto_continue_once=false',*extra)
   item['status']='dispatched'
  publish(report,branch='fetch-update-reports')
 report['dispatch']='complete';report['checked_utc']=datetime.now(timezone.utc).isoformat();publish(report,branch='fetch-update-reports');print('Fresh dispatch complete:',len(report['groups']),'runners, maximum three stores each; selected stores: '+str(len(sites))+'; source failures remain explicit.')
if __name__=='__main__':main()
