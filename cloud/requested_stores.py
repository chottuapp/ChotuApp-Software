"""Additive owner-requested fetches. Never stop another runner or replace a checkpoint."""
import concurrent.futures,json,os,re,subprocess,time
from datetime import datetime,timezone
from pathlib import Path
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser
import requests
from source_research import publish
ROOT=Path(__file__).resolve().parents[1];REPO='chottuapp/ChotuApp-Software'

def gh(*args):
 return subprocess.run(['gh',*args],capture_output=True,text=True,check=True,timeout=180).stdout

def validate(request,registry,codes,policy):
 if request.get('campaign_id')!=policy['campaign_id'] or request.get('refresh_generation')!=policy['refresh_generation']:raise ValueError('Requested generation mismatch')
 if not re.fullmatch(r'requested\d{8}',request.get('request_id','')) or request.get('maximum_stores_per_runner')!=2:raise ValueError('Unexpected additive request')
 stores=request['stores'];names={s['name'] for s in stores}
 if not 1<=len(stores)<=20 or len(names)!=len(stores):raise ValueError('Duplicate or excessive requested stores')
 registered={s['name']:s for s in registry}
 for s in stores:
  r=registered.get(s['name']);u=urlsplit(s['url'])
  if not r or r.get('enabled',True) is False or s['name'] in policy.get('excluded_stores',[]):raise ValueError('Paused or unapproved requested store')
  if u.scheme!='https' or u.username or u.password or u.query or u.path not in ('','/') or u.port is not None:raise ValueError('Exact approved HTTPS homepage required')
  if u.hostname.removeprefix('www.')!=urlsplit(r['url']).hostname.removeprefix('www.') or codes.get(s['name'])!=s.get('shop_code'):raise ValueError('Requested source/code mismatch')
 return stores

def root_lane(run,runs):
 seen=set();byid={str(r['databaseId']):r for r in runs}
 while run:
  title=run.get('displayTitle','')
  if title.startswith('Cloud group '):return title.removeprefix('Cloud group ')
  match=re.fullmatch(r'Automatic continuation of (\d+)',title)
  if not match or match[1] in seen:return None
  seen.add(match[1]);run=byid.get(match[1])
 return None

def dispatch_plan(request,runs,ready,additional_active=()):
 prefix='audit804-'+request['campaign_id']+'-'+request['refresh_generation']+'-'+request['request_id']+'-'
 lanes=request['existing_lanes'];codes={s['shop_code']:s['name'] for s in request['stores']};active=set(additional_active);launched=set()
 for r in runs:
  lane=root_lane(r,runs)
  if lane and lane.startswith(prefix):
   listed={name for code,name in codes.items() if code in lane.split('-')};launched.update(listed)
   if r['status']!='completed':active.update(listed)
  elif r['status']!='completed' and lane in lanes:active.update(lanes[lane])
 plan=[]
 for i in range(0,len(request['stores']),2):
  selected=[s for s in request['stores'][i:i+2] if s['name'] in ready and s['name'] not in active|launched]
  if selected:
   lane=prefix+str(i//2+1)+'-'+'-'.join(s['shop_code'] for s in selected)
   plan.append(dict(runner_group=lane,stores=[dict(name=s['name'],url=s['url']) for s in selected]))
 return plan,active,launched

def probe(site):
 base=site['url'].rstrip('/');host=urlsplit(base).hostname.removeprefix('www.');session=requests.Session();session.headers['User-Agent']='ChotuAppRequestedStoreCheck/1.0';observations=[]
 def read(path):
  time.sleep(1.5);url=base+path
  if path!='/robots.txt' and not robots.can_fetch(session.headers['User-Agent'],url):raise ValueError('Public robots rule disallows '+path)
  r=session.get(url,timeout=(15,30))
  if urlsplit(r.url).hostname.removeprefix('www.')!=host:raise ValueError('Store redirects to a different source host')
  if len(r.content)>10*1024**2:raise ValueError('Public response exceeds probe bound')
  observations.append(dict(path=path,status=r.status_code,final_url=r.url))
  if r.status_code in (403,429,503):r.raise_for_status()
  return r
 result=dict(name=site['name'],url=base,observations=observations)
 try:
  robots=RobotFileParser();r=read('/robots.txt')
  if r.status_code==404:robots.parse([])
  else:r.raise_for_status();robots.parse(r.text.splitlines())
  r=read('/products.json?limit=1');data=None
  if r.ok:
   try:data=r.json()
   except ValueError:pass
  if isinstance(data,dict) and isinstance(data.get('products'),list) and data['products']:
   p=data['products'][0]
   if p.get('id') and p.get('handle') and isinstance(p.get('variants'),list) and p['variants']:
    result.update(provider='shopify',status='supported');return result
  r=read('/wp-json/wc/store/v1/products?per_page=1');data=None
  if r.ok:
   try:data=r.json()
   except ValueError:pass
  if isinstance(data,list) and data and isinstance(data[0],dict) and data[0].get('id') and data[0].get('prices',{}).get('currency_code')=='PKR':
   from woocommerce_source_support import HOSTS
   result.update(provider='woocommerce',status='supported' if host in HOSTS else 'adapter_registration_required',sample={k:data[0].get(k) for k in ('id','name','permalink','type','prices','is_in_stock','is_purchasable','has_options','attributes')});return result
  r=read('');html=r.text.lower();result.update(provider='magento' if 'magento' in html or 'mage/cookies' in html else 'unknown',status='adapter_required')
 except (requests.RequestException,ValueError) as exc:result.update(status='source_blocked',error=str(exc)[:500])
 return result

def main():
 read=lambda n:json.loads((ROOT/'cloud'/n).read_text())
 request=read('requested-stores.json');stores=validate(request,read('fetch-update-release.json')['fresh_stores'],read('confirmed-shop-codes.json'),read('audit804-release.json'))
 report=dict(run_id=os.environ['GITHUB_RUN_ID'],request_id=request['request_id'],checked_utc=datetime.now(timezone.utc).isoformat(),stores=[],groups=[],status='checking')
 def save():report['checked_utc']=datetime.now(timezone.utc).isoformat();publish(report,branch='requested-store-reports')
 with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:report['stores']=list(pool.map(probe,stores))
 save();ready={s['name'] for s in report['stores'] if s['status']=='supported'}
 runs=json.loads(gh('run','list','--repo',REPO,'--workflow','cloud-fetch.yml','--limit','200','--json','databaseId,displayTitle,status'))
 # Unknown active lanes are inspected rather than assumed unrelated.
 active=set()
 for r in runs:
  if r['status']=='completed':continue
  lane=root_lane(r,runs)
  if lane in request['existing_lanes'] or lane and request['request_id'] in lane:continue
  import tempfile
  try:
   with tempfile.TemporaryDirectory() as tmp:
    gh('run','download',str(r['databaseId']),'--repo',REPO,'--name','chotuapp-excel-files','--dir',tmp)
    paths=list(Path(tmp).rglob('run-summary.json'))
    if len(paths)!=1:raise ValueError('Active runner has no unique source summary')
    summary=json.loads(paths[0].read_text());active.update(s['name'] for s in summary['stores'])
  except Exception:
   report.update(status='active_source_identity_unavailable',blocked_run=str(r['databaseId']));save();return
 plan,active,launched=dispatch_plan(request,runs,ready,active)
 report.update(active_stores_preserved=sorted(active),already_dispatched=sorted(launched))
 for group in plan:
  lane=group['runner_group'];gh('workflow','run','cloud-fetch.yml','--repo',REPO,'--ref','main','-f','stores='+json.dumps(group['stores'],separators=(',',':')),'-f','runner_group='+lane,'-f','minutes=300','-f','save_checkpoint=true','-f','auto_continue_limit=48','-f','auto_continue_once=false')
  report['groups'].append(dict(group,status='dispatched'));save()
 report['status']='dispatch_complete';save();print(json.dumps(report,ensure_ascii=False))
if __name__=='__main__':main()
