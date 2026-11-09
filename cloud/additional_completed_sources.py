"""Explicit additive completed exports enter the same independent audit/delivery gate."""
import json,re
REPO='chottuapp/ChotuApp-Software'
def approved_runs(config,sites,gh,selected=None):
 policy=config.get('additional_completed_sources',[])
 if not isinstance(policy,list) or len(policy)>20:raise ValueError('Additional source policy exceeds bound')
 result=[];seen=set()
 for item in policy:
  store=item.get('store');rid=str(item.get('run_id',''))
  if store not in config['stores'] or store not in sites or store in seen or not re.fullmatch(r'[0-9]{1,30}',rid):raise ValueError('Invalid additional completed source identity')
  expected_path=item.get('workflow','.github/workflows/cloud-fetch.yml')
  if expected_path!='.github/workflows/cloud-fetch.yml' and not (store=='ChotuApp Groceries' and expected_path=='.github/workflows/cloud-grocery-complete.yml'):raise ValueError('Unapproved additional source workflow')
  seen.add(store)
  if selected is not None and store not in selected:continue
  run=json.loads(gh('api','repos/'+REPO+'/actions/runs/'+rid))
  if str(run.get('id'))!=rid or run.get('head_branch')!='main' or run.get('path')!=expected_path or run.get('event')!='workflow_dispatch' or run.get('status')!='completed' or run.get('conclusion')!='success' or run.get('head_repository',{}).get('full_name')!=REPO:raise ValueError('Additional source is not a successful trusted main fetch')
  result.append(dict(databaseId=run['id'],displayTitle=run['display_title'],status=run['status'],conclusion=run['conclusion'],headSha=run['head_sha'],additional_store=store))
 return result
