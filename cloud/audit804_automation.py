"""Bounded public evidence refresh; never executes source text or approves an audit."""
import hashlib,json,re
from pathlib import Path
from datetime import datetime,timezone,timedelta
from urllib.parse import urlsplit
from bs4 import BeautifulSoup

def normalized(value):return re.sub(r'[^a-z0-9]+','',str(value or '').casefold())
def validated_facts(report,sites,now=None):
 now=now or datetime.now(timezone.utc)
 checked=datetime.fromisoformat(str(report['checked_utc']).replace('Z','+00:00'))
 if checked.tzinfo is None or not timedelta(minutes=-5)<=now-checked<=timedelta(days=1):raise ValueError('Public evidence is stale or has an invalid timestamp')
 results=report.get('results',[])
 if not isinstance(results,list) or len(results)>160:raise ValueError('Public evidence batch exceeds limit')
 facts=[]
 for item in results:
  store=item.get('store');product=item.get('product');url=urlsplit(str(item.get('source_url') or ''))
  if store not in sites or not isinstance(product,dict) or item.get('error'):continue
  host=urlsplit(sites[store]['url']).hostname
  if url.scheme!='https' or url.username or url.password or url.query or not url.hostname or url.hostname.removeprefix('www.')!=host.removeprefix('www.'):continue
  if not item.get('product_id') or not normalized(item.get('name')) or normalized(item['name'])!=normalized(product.get('title')):continue
  # The collector verifies the returned Shopify handle against this exact URL.
  if '/products/' not in url.path or product.get('handle')!=url.path.rstrip('/').split('/')[-1]:continue
  body=product.get('description') or product.get('body_html') or ''
  if not isinstance(body,str) or len(body)>100000:continue
  facts.append(dict(store=store,product_id=str(item['product_id']),source_url=item['source_url'],requested_name=item['name'],public_title=product['title'],product_type=str(product.get('type') or product.get('product_type') or '')[:300],description=BeautifulSoup(body,'html.parser').get_text('\n',strip=True),evidence_run=str(report.get('run_id','')),checked_utc=report['checked_utc']))
 return facts

def refresh(root,gh,sites,cache=None):
 report=json.loads(gh('api','repos/chottuapp/ChotuApp-Software/contents/latest.json?ref=audit804-source-evidence','-H','Accept: application/vnd.github.raw+json'))
 incoming=validated_facts(report,sites)
 merged={}
 for fact in cache or []:
  try:
   record=dict(store=fact['store'],product_id=fact['product_id'],name=fact['requested_name'],source_url=fact['source_url'],product=dict(handle=urlsplit(fact['source_url']).path.rstrip('/').split('/')[-1],title=fact['public_title'],type=fact['product_type'],description=fact['description']))
   valid=validated_facts({'checked_utc':fact['checked_utc'],'run_id':fact['evidence_run'],'results':[record]},sites)
   if valid:merged[(fact['store'],fact['product_id'],fact['source_url'])]=valid[0]
  except (ValueError,KeyError,TypeError):continue
 for fact in incoming:merged[(fact['store'],fact['product_id'],fact['source_url'])]=fact
 facts=sorted(merged.values(),key=lambda row:(row['checked_utc'],row['store'],row['product_id']))[-500:]
 while facts and len(json.dumps(facts).encode())>512000:facts.pop(0)
 # Ignore changing observation times: identical facts must not restart expensive audits.
 stable=sorted([{k:v for k,v in row.items() if k not in ('checked_utc','evidence_run')} for row in facts],key=lambda row:(row['store'],row['product_id'],row['source_url']))
 digest=hashlib.sha256(json.dumps(stable,sort_keys=True).encode()).hexdigest()
 target=Path(root)/'cloud/audit804-auto-source.json';target.write_text(json.dumps({'products':facts}),encoding='utf-8')
 from hold804_repairs import public_index
 public_index.cache_clear()
 return digest,len(facts),facts

def request_from_holds(state,sites,previous=None,limit=160):
 """Rotate bounded batches fairly across stores; no credentials or workbook contacts."""
 groups=[]
 for store,report in sorted(state.get('audit804_results',{}).items()):
  if store not in sites or report.get('status')!='hold':continue
  group=[]
  for row in report.get('findings',[]):
   url=urlsplit(str(row.get('source_url') or ''));host=urlsplit(sites[store]['url']).hostname
   if row.get('product_id') and row.get('name') and url.scheme=='https' and not url.query and not url.username and not url.password and url.hostname and url.hostname.removeprefix('www.')==host.removeprefix('www.'):
    group.append(dict(store=store,product_id=row['product_id'],name=row['name'],source_url=row['source_url'],inspect_image=False))
  if group:groups.append(group)
 pool=[]
 while any(groups):
  for group in groups:
   if group:pool.append(group.pop(0))
 if not pool:return {'request':'No actionable public source holds','products':[],'cursor':0}
 cursor=int((previous or {}).get('next_cursor',0))%len(pool)
 selected=(pool+pool)[cursor:cursor+min(limit,len(pool))]
 return {'request':'Automatic bounded primary-source refresh for 804 holds','products':selected,'cursor':cursor,'next_cursor':(cursor+len(selected))%len(pool)}
