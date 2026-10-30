"""One owner-requested checkpoint retry; never replace active or completed work."""
import json,os,subprocess,tempfile
from pathlib import Path
from datetime import datetime,timezone
from fresh804_dispatch import selected_sites,planned_groups,lane_prefix,chain_ids
from source_research import publish
ROOT=Path(__file__).resolve().parents[1];REPO='chottuapp/ChotuApp-Software'
def gh(*args):return subprocess.run(['gh',*args],capture_output=True,text=True,check=True,timeout=180).stdout

def recovery_plan(request,policy,registry,runs,run,summary,artifacts):
 if request.get('campaign_id')!=policy['campaign_id'] or request.get('refresh_generation')!=policy['refresh_generation']:raise ValueError('Recovery generation mismatch')
 rid=str(request['source_run']);group=request['runner_group'];wanted=request['stores']
 if not rid.isdigit() or not wanted or len(wanted)!=len(set(wanted)):raise ValueError('Unique approved recovery stores required')
 groups=planned_groups(selected_sites(registry,policy),policy)
 expected=next((sites for i,sites in enumerate(groups,1) if lane_prefix(policy)+str(i)==group),None)
 if expected is None or not set(wanted)<={s['name'] for s in expected}:raise ValueError('Recovery outside approved enabled source group')
 if str(run.get('id'))!=rid or run.get('event')!='workflow_dispatch' or run.get('head_branch')!='main' or run.get('head_repository',{}).get('full_name')!=REPO or run.get('display_title')!='Cloud group '+group:raise ValueError('Untrusted source run identity')
 if run.get('status')!='completed':return None
 owned=chain_ids(runs,{rid})
 if any(str(r['databaseId']) in owned-{rid} or r.get('displayTitle')=='Cloud group '+group and (r['status']!='completed' or int(r['databaseId'])>int(rid)) for r in runs):return None
 if run.get('conclusion') in ('success','cancelled') or summary.get('status')=='complete' or summary.get('stop_reason')=='stop_requested':return None
 if summary.get('runner_group')!=group or {s.get('name') for s in summary.get('stores',[])}!={s['name'] for s in expected}:raise ValueError('Saved checkpoint source group mismatch')
 if summary.get('checkpoint')!='saved' or not any(a.get('name')=='chotuapp-checkpoint' and not a.get('expired') for a in artifacts):raise ValueError('No intact available saved checkpoint')
 states={s['name']:s.get('status') for s in summary['stores']}
 if any(states[n] not in ('failed','blocked','source_paused','pending') for n in wanted):return None
 return [s for s in expected if s['name'] in wanted]

def main():
 request=json.loads((ROOT/'cloud/pending-recovery-request.json').read_text());policy=json.loads((ROOT/'cloud/audit804-release.json').read_text());registry=json.loads((ROOT/'cloud/fetch-update-release.json').read_text())['fresh_stores'];rid=str(request['source_run'])
 report={'run_id':os.environ['GITHUB_RUN_ID'],'checked_utc':datetime.now(timezone.utc).isoformat(),'source_run':rid,'status':'checking','stores':request['stores']}
 def save():publish(report,branch='pending-recovery-reports')
 save()
 runs=json.loads(gh('run','list','--repo',REPO,'--workflow','cloud-fetch.yml','--limit','100','--json','databaseId,displayTitle,status,conclusion'))
 run=json.loads(gh('api','repos/'+REPO+'/actions/runs/'+rid))
 if run.get('status')!='completed':report['status']='active_source_preserved';save();return
 artifacts=json.loads(gh('api','repos/'+REPO+'/actions/runs/'+rid+'/artifacts'))['artifacts']
 with tempfile.TemporaryDirectory() as tmp:
  gh('run','download',rid,'--repo',REPO,'--name','chotuapp-excel-files','--dir',tmp)
  summaries=list(Path(tmp).rglob('run-summary.json'))
  if len(summaries)!=1:raise ValueError('Unique saved run summary required')
  summary=json.loads(summaries[0].read_text())
 sites=recovery_plan(request,policy,registry,runs,run,summary,artifacts)
 if not sites:report['status']='existing_continuation_or_completed_work_preserved';save();return
 gh('workflow','run','cloud-fetch.yml','--repo',REPO,'--ref','main','-f','resume_run_id='+rid,'-f','partition_resume=true','-f','runner_group='+request['runner_group'],'-f','stores='+json.dumps(sites,separators=(',',':')),'-f','minutes=300','-f','save_checkpoint=true','-f','continuation_parent='+rid,'-f','auto_continue_limit=0','-f','auto_continue_once=false')
 report.update(status='one_checkpoint_resume_requested',completed_stores_preserved=[s['name'] for s in summary['stores'] if s['status']=='done'],checked_utc=datetime.now(timezone.utc).isoformat());save()
if __name__=='__main__':main()
