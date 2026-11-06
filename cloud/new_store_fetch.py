"""Additive fetch requests before the owner supplies shop codes."""
import concurrent.futures,json,os,re,hashlib
from datetime import datetime,timezone
from pathlib import Path
from urllib.parse import urlsplit
from runtime import validate_site
from requested_stores import probe,root_lane,gh
from source_research import publish
ROOT=Path(__file__).resolve().parents[1]
REPO='chottuapp/ChotuApp-Software'

def validate(request):
 if not re.fullmatch(r'new\d{8}',request.get('request_id','')):raise ValueError('Dated request identity required')
 stores=request.get('stores',[])
 if not 1<=len(stores)<=20:raise ValueError('Bounded store list required')
 from locked_store_rules import owner_paused
 names=set();hosts=set();result=[]
 for raw in stores:
  site=validate_site(raw,resolve=False);host=urlsplit(site['url']).hostname.removeprefix('www.')
  if not site['url'].startswith('https://') or raw.get('shop_code') not in (None,''):raise ValueError('HTTPS stores with owner-pending shop codes only')
  if site['name'] in names or host in hosts or owner_paused(site['name'],site['url']):raise ValueError('Duplicate or owner-paused source')
  names.add(site['name']);hosts.add(host);result.append(site)
 return result

def key(site):return 'src'+hashlib.sha256(urlsplit(site['url']).hostname.removeprefix('www.').encode()).hexdigest()[:12]

def plan(request,stores,observations,runs):
 prefix='requested-'+request['request_id']+'-';already=set()
 for run in runs:
  lane=root_lane(run,runs)
  if lane and lane.startswith(prefix):already.update(s['name'] for s in stores if key(s) in lane.split('-'))
 ready={o['name'] for o in observations if o.get('status')=='supported' and o.get('provider')=='shopify'}
 groups=[]
 for i in range(0,len(stores),2):
  selected=[s for s in stores[i:i+2] if s['name'] in ready-already]
  if selected:groups.append(dict(runner_group=prefix+str(i//2+1)+'-'+'-'.join(key(s) for s in selected),stores=selected))
 return groups,already

def main():
 request=json.loads((ROOT/'cloud/new-store-fetch-request.json').read_text());stores=validate(request)
 report=dict(run_id=os.environ['GITHUB_RUN_ID'],request_id=request['request_id'],checked_utc=datetime.now(timezone.utc).isoformat(),shop_codes='Pending owner; blank in exports',stores=[],groups=[],status='checking')
 def save():
  report['checked_utc']=datetime.now(timezone.utc).isoformat();publish(report,branch='new-store-fetch-reports')
 with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:report['stores']=list(pool.map(probe,stores))
 save()
 runs=json.loads(gh('run','list','--repo',REPO,'--workflow','cloud-fetch.yml','--limit','200','--json','databaseId,displayTitle,status'))
 groups,already=plan(request,stores,report['stores'],runs);report['already_dispatched']=sorted(already)
 for group in groups:
  gh('workflow','run','cloud-fetch.yml','--repo',REPO,'--ref','main','-f','stores='+json.dumps(group['stores']),'-f','runner_group='+group['runner_group'],'-f','minutes=300','-f','save_checkpoint=true','-f','auto_continue_limit=6','-f','auto_continue_once=false')
  report['groups'].append(dict(group,status='dispatched'));save()
 report['status']='dispatch_complete';save()
 print(json.dumps(report))
if __name__=='__main__':main()
