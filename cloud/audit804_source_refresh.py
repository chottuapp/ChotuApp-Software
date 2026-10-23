"""Bounded refresh of public product facts for owner-requested audit repairs."""
import json,time,re,os
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
  results.append(rec);print(item['store'],item['product_id'],rec.get('error','public facts captured'),flush=True)
  if len(results)%20==0:publish({'run_id':os.environ['GITHUB_RUN_ID'],'checked_utc':datetime.now(timezone.utc).isoformat(),'complete':False,'results':results},branch='audit804-source-evidence')
 publish({'run_id':os.environ['GITHUB_RUN_ID'],'checked_utc':datetime.now(timezone.utc).isoformat(),'complete':True,'results':results},branch='audit804-source-evidence')
if __name__=='__main__':main()
