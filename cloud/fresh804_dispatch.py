"""Explicit one-time fresh restart: save/stop prior fetches, then at most three stores per runner."""
import json,os,subprocess,time
from pathlib import Path
from datetime import datetime,timezone
from group_fetch import groups
from fetch_update_release import stop_previous
from source_research import publish
ROOT=Path(__file__).resolve().parents[1];REPO='chottuapp/ChotuApp-Software'
def gh(*args):return subprocess.run(['gh',*args],capture_output=True,text=True,check=True,timeout=90).stdout

def main():
 request=json.loads((ROOT/'cloud/audit804-release.json').read_text());campaign=request['campaign_id'];prefix='Cloud group audit804-'+campaign+'-'
 registry=json.loads((ROOT/'cloud/fetch-update-release.json').read_text())['fresh_stores']
 sites=[row for row in registry if row['name']!='Khaadi']
 if len(sites)!=28:raise ValueError('Exactly 28 approved cloud stores required; Khaadi uses its phone worker')
 if request.get('maximum_stores_per_runner')!=3 or request.get('destination_folder')!='ChotuApp 19-10-2026 11-36AM':raise ValueError('Unexpected requested fresh policy')
 report={'run_id':os.environ['GITHUB_RUN_ID'],'campaign_id':campaign,'checked_utc':datetime.now(timezone.utc).isoformat(),'groups':[],'phone':{'store':'Khaadi','status':'waiting_for_updated_app_open','fresh_campaign_id':campaign},'stopped':[]}
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
 for index,stores in enumerate(groups(sites),1):
  lane='audit804-'+campaign+'-'+str(index);title='Cloud group '+lane
  item={'runner_group':lane,'stores':stores,'status':'already_dispatched' if any(run['displayTitle']==title for run in existing) else 'pending'};report['groups'].append(item)
  if item['status']=='pending':
   gh('workflow','run','cloud-fetch.yml','--repo',REPO,'--ref','main','-f','stores='+json.dumps(stores,separators=(',',':')),'-f','runner_group='+lane,'-f','minutes=300','-f','save_checkpoint=true','-f','auto_continue_limit=6','-f','auto_continue_once=false')
   item['status']='dispatched'
  publish(report,branch='fetch-update-reports')
 report['dispatch']='complete';report['checked_utc']=datetime.now(timezone.utc).isoformat();publish(report,branch='fetch-update-reports');print('Fresh dispatch complete:',len(report['groups']),'runners, maximum three stores each; Khaadi phone fresh pending app open.')
if __name__=='__main__':main()
