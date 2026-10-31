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
 from locked_store_rules import owner_paused
 if any(owner_paused(name) for name in wanted):raise ValueError('Owner-paused source cannot resume')
 groups=planned_groups(selected_sites(registry,policy),policy)
 expected=next((sites for i,sites in enumerate(groups,1) if lane_prefix(policy)+str(i)==group),None)
 # New pauses must not relabel the source identity of an existing checkpoint.
 lanes=json.loads((ROOT/'cloud/requested-stores.json').read_text()).get('existing_lanes',{})
 if group in lanes:
  byname={s['name']:s for s in registry};expected=[byname[name] for name in lanes[group]]
 # Additive lanes retain their original pair position and exact shop-code suffix.
 # Do not derive their identity from a newly filtered/reordered active registry.
 if expected is None:
  additive=json.loads((ROOT/'cloud/requested-stores.json').read_text())
  prefix=lane_prefix(policy)+str(additive.get('request_id',''))+'-'
  if additive.get('campaign_id')==policy['campaign_id'] and additive.get('refresh_generation')==policy['refresh_generation'] and group.startswith(prefix):
   parts=group[len(prefix):].split('-')
   if len(parts) in (2,3) and parts[0].isdigit() and int(parts[0])>0:
    pair=additive['stores'][(int(parts[0])-1)*2:int(parts[0])*2];codes=parts[1:]
    selected=[site for site in pair if site.get('shop_code') in codes]
    registered={site['name']:site for site in registry}
    confirmed=json.loads((ROOT/'cloud/confirmed-shop-codes.json').read_text())
    if codes==[site.get('shop_code') for site in selected] and len(set(codes))==len(codes) and all(confirmed.get(site['name'])==site['shop_code'] and registered.get(site['name'],{}).get('url','').rstrip('/')==site['url'].rstrip('/') for site in selected):
     expected=[registered[site['name']] for site in selected]
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

def ancestor_recovery_plan(request,policy,registry,runs,run,summary,artifacts,checkpoint_id,latest_summary):
 owned=chain_ids(runs,{str(request['source_run'])})
 if str(checkpoint_id) not in owned:raise ValueError('Checkpoint outside approved continuation ancestry')
 if any(r['status']!='completed' and (str(r['databaseId']) in owned or r.get('displayTitle')=='Cloud group '+request['runner_group']) for r in runs):return None
 if any(str(r['databaseId']) not in owned and r.get('displayTitle')=='Cloud group '+request['runner_group'] and int(r['databaseId'])>int(request['source_run']) for r in runs):return None
 if latest_summary.get('runner_group')!=request['runner_group']:raise ValueError('Latest continuation source group mismatch')
 current={s['name']:s.get('status') for s in latest_summary.get('stores',[])}
 if not set(request['stores'])<=set(current):raise ValueError('Latest continuation lacks requested store identity')
 if latest_summary.get('status')=='complete' or latest_summary.get('stop_reason')=='stop_requested' or any(current[n] not in ('failed','blocked','source_paused','pending') for n in request['stores']):return None
 # The existing strict root/store/checkpoint checks still apply after the chain
 # checks above; only the specifically requested incomplete store is selected.
 return recovery_plan(request,policy,registry,[],run,summary,artifacts)

def main():
 request=json.loads((ROOT/'cloud/pending-recovery-request.json').read_text());policy=json.loads((ROOT/'cloud/audit804-release.json').read_text());registry=json.loads((ROOT/'cloud/fetch-update-release.json').read_text())['fresh_stores'];rid=str(request['source_run'])
 report={'run_id':os.environ['GITHUB_RUN_ID'],'checked_utc':datetime.now(timezone.utc).isoformat(),'source_run':rid,'status':'checking','stores':request['stores']}
 def save():publish(report,branch='pending-recovery-reports')
 save()
 runs=json.loads(gh('run','list','--repo',REPO,'--workflow','cloud-fetch.yml','--limit','100','--json','databaseId,displayTitle,status,conclusion'))
 run=json.loads(gh('api','repos/'+REPO+'/actions/runs/'+rid))
 if run.get('status')!='completed':report['status']='active_source_preserved';save();return
 resume_id=rid;parent_id=rid
 def saved_summary(identity):
  with tempfile.TemporaryDirectory() as tmp:
   gh('run','download',identity,'--repo',REPO,'--name','chotuapp-excel-files','--dir',tmp)
   summaries=list(Path(tmp).rglob('run-summary.json'))
   if len(summaries)!=1:raise ValueError('Unique saved run summary required')
   return json.loads(summaries[0].read_text())
 if request.get('allow_checkpoint_ancestor') is True:
  owned=chain_ids(runs,{rid});chain=[r for r in runs if str(r['databaseId']) in owned]
  if any(r['status']!='completed' for r in chain):report['status']='active_continuation_preserved';save();return
  if not chain:raise ValueError('Approved continuation chain unavailable; no speculative resume')
  parent_id=str(max(chain,key=lambda r:int(r['databaseId']))['databaseId'])
  leaf=json.loads(gh('api','repos/'+REPO+'/actions/runs/'+parent_id))
  if leaf.get('event')!='workflow_dispatch' or leaf.get('head_branch')!='main' or leaf.get('head_repository',{}).get('full_name')!=REPO:raise ValueError('Untrusted latest continuation')
  latest=saved_summary(parent_id)
  from resume_failed_stores import checkpoint_parent
  resume_id,checked=checkpoint_parent(parent_id);report.update(checkpoint_ancestor=resume_id,checked_ancestry=checked)
  summary=saved_summary(resume_id)
  artifacts=json.loads(gh('api','repos/'+REPO+'/actions/runs/'+resume_id+'/artifacts'))['artifacts']
  sites=ancestor_recovery_plan(request,policy,registry,runs,run,summary,artifacts,resume_id,latest)
 else:
  artifacts=json.loads(gh('api','repos/'+REPO+'/actions/runs/'+rid+'/artifacts'))['artifacts'];summary=saved_summary(rid)
  sites=recovery_plan(request,policy,registry,runs,run,summary,artifacts)
 if not sites:report['status']='existing_continuation_or_completed_work_preserved';save();return
 gh('workflow','run','cloud-fetch.yml','--repo',REPO,'--ref','main','-f','resume_run_id='+resume_id,'-f','partition_resume=true','-f','runner_group='+request['runner_group'],'-f','stores='+json.dumps(sites,separators=(',',':')),'-f','minutes=300','-f','save_checkpoint=true','-f','continuation_parent='+parent_id,'-f','auto_continue_limit=0','-f','auto_continue_once=false')
 report.update(status='one_checkpoint_resume_requested',completed_stores_preserved=[s['name'] for s in summary['stores'] if s['status']=='done'],checked_utc=datetime.now(timezone.utc).isoformat());save()
if __name__=='__main__':main()
