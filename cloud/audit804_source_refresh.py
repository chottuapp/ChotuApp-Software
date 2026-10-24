"""Bounded refresh of public product facts for owner-requested audit repairs."""
import json,time,re,os,subprocess
from pathlib import Path
from urllib.parse import urlsplit,unquote
from urllib.robotparser import RobotFileParser
from datetime import datetime,timezone
import requests
from bs4 import BeautifulSoup
from source_research import publish
AGENT='ChotuAppCatalogRefresh'
def main():
 request=json.loads(Path('cloud/audit804-source-request.json').read_text());items=request['products']
 if not items:print('No actionable public source holds');return
 if not 1<=len(items)<=160:raise ValueError('Bounded public review required')
 hosts={urlsplit(s['url']).hostname.removeprefix('www.') for s in json.loads(Path('cloud/fetch-update-release.json').read_text())['fresh_stores']}
 robots={};session=requests.Session();session.headers['User-Agent']=AGENT;results=[]
 def read(url):
  host=urlsplit(url).hostname
  if host.removeprefix('www.') not in hosts:raise ValueError('Unapproved source host')
  if host not in robots:
   r=session.get('https://'+host+'/robots.txt',timeout=30);r.raise_for_status();robot=RobotFileParser();robot.parse(r.text.splitlines());robots[host]=robot
  if not robots[host].can_fetch(AGENT,url):raise ValueError('Public robots rule disallows source')
  time.sleep(1.5);r=session.get(url,timeout=40);r.raise_for_status()
  if urlsplit(r.url).hostname.removeprefix('www.')!=host.removeprefix('www.'):raise ValueError('Source changed storefront')
  if len(r.content)>10*1024**2:raise ValueError('Source response exceeds review bound')
  return r
 def emit(complete):
  report={'run_id':os.environ['GITHUB_RUN_ID'],'checked_utc':datetime.now(timezone.utc).isoformat(),'complete':complete,'next_cursor':request.get('next_cursor',0),'recent_checks':request.get('recent_checks',{}),'results':results}
  # Retain every primary fact and image URL/hash; optional image bodies must not
  # prevent later products or final evidence from being published.
  while len(json.dumps(report,ensure_ascii=True,indent=2).encode())>1900000:
   images=[v['public_image'] for v in results if v.get('public_image',{}).get('base64')]
   if not images:raise ValueError('Primary public facts exceed bounded report size')
   largest=max(images,key=lambda v:len(v['base64']));largest.pop('base64');largest['body_omitted_due_to_report_bound']=True
  publish(report,branch='audit804-source-evidence')
 for item in items:
  rec={k:item[k] for k in ('store','product_id','source_url','name')};url=item['source_url'];p=urlsplit(url)
  try:
   if p.scheme!='https' or p.username or p.password or p.query:raise ValueError('Exact public HTTPS product URL required')
   handle=unquote(p.path.rstrip('/').split('/')[-1]);product=None
   if '/products/' in p.path:
    try:
     raw=read(url+'.js').json()
     if raw.get('handle')!=handle:raise ValueError('Product handle mismatch')
     product={k:raw.get(k) for k in ('id','handle','title','description','body_html','type','product_type','vendor','tags','options','images')}
    except (requests.RequestException,ValueError):product=None
   if product:rec['product']=product
   if product and item.get('inspect_image') is True:
    import base64,hashlib
    image=(product.get('images') or [None])[0]
    if isinstance(image,str):
     image='https:'+image if image.startswith('//') else image
     image_url=urlsplit(image)
     if image_url.scheme=='https' and image_url.hostname=='cdn.shopify.com':
      image=image+('&' if image_url.query else '?')+'width=800'
      visual=session.get(image,timeout=40);visual.raise_for_status()
      if len(visual.content)<=250000 and visual.headers.get('Content-Type','').startswith('image/'):
       rec['public_image']={'source_url':image,'sha256':hashlib.sha256(visual.content).hexdigest(),'content_type':visual.headers.get('Content-Type'),'base64':base64.b64encode(visual.content).decode()}
   if not product or not (product.get('description') or product.get('body_html')):
    soup=BeautifulSoup(read(url).text,'html.parser')
    scripts=[]
    for node in soup.select('script[type="application/ld+json"]'):
     try:scripts.append(json.loads(node.get_text()))
     except ValueError:pass
    rec['structured_products']=scripts[:8]
    parts=soup.select('.product__description, .product-description, #product-description, [class*="bundle"][class*="title"], [class*="bundle"][class*="description"]')
    rec['public_description_fragments']=[n.get_text(' ',strip=True)[:8000] for n in parts[:10] if n.get_text(' ',strip=True)]
   rec['status']='review_evidence_collected'
  except Exception as exc:rec['error']=str(exc)[:500]
  request.setdefault('recent_checks',{})[item['store']+'|'+str(item['product_id'])]=datetime.now(timezone.utc).isoformat()
  results.append(rec);print(item['store'],item['product_id'],rec.get('error','public facts captured'),flush=True)
  if len(results)%20==0:emit(False)
 emit(True)
 # Re-enter the checked Rule 804/audit/delivery path immediately after source work.
 subprocess.run(['gh','workflow','run','cloud-drive-sync.yml','--repo','chottuapp/ChotuApp-Software','--ref','main'],check=True,capture_output=True,text=True,timeout=60)
if __name__=='__main__':
 if os.environ.get('AUTO_AUDIT_EVIDENCE')=='true':
  import subprocess
  from audit804_automation import request_from_holds
  def report(branch):
   subprocess.run(['git','fetch','origin',branch],check=True,capture_output=True)
   return json.loads(subprocess.run(['git','show','FETCH_HEAD:latest.json'],check=True,capture_output=True,text=True).stdout)
  state=report('drive-sync-reports')
  try:previous=report('audit804-source-evidence')
  except (subprocess.CalledProcessError,ValueError):previous={}
  sites={s['name']:s for s in json.loads(Path('cloud/fetch-update-release.json').read_text())['fresh_stores']}
  Path('cloud/audit804-source-request.json').write_text(json.dumps(request_from_holds(state,sites,previous,limit=40)))
 main()
