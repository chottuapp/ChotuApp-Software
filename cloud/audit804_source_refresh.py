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
def saved_input_cover(item):
 """Read a cover only from the checksum-verified exact held workbook identity."""
 import tempfile,hashlib
 from audit804_queue import restore
 from audit804 import rows
 campaign=json.loads(Path('cloud/audit804-release.json').read_text())['campaign_id']
 if item.get('campaign_id')!=campaign:raise ValueError('Saved cover campaign mismatch')
 with tempfile.TemporaryDirectory() as tmp:
  source=restore(item['held_input'],Path(tmp)/'source.xlsx',item['store'],campaign)
  found=[r for r in rows(source) if (str(r.get('product_id')),r.get('name'),r.get('source_url'))==(str(item['product_id']),item['name'],item['source_url'])]
  if len(found)!=1:raise ValueError('Saved cover product identity mismatch')
  row=found[0];url=str(row.get('scraped_image_url (cover, auto)') or '')
  parsed=urlsplit(url)
  if parsed.scheme!='https' or parsed.hostname!='cdn.shopify.com' or parsed.username or parsed.password:raise ValueError('Saved cover must use approved public image CDN')
  return url,{'input_workbook_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'input_description_sha256':hashlib.sha256(str(row.get('description') or '').encode()).hexdigest(),'saved_input_verified':True}

def capture_saved_cover(item,session):
 import base64,hashlib
 url,proof=saved_input_cover(item);render=url+('&' if urlsplit(url).query else '?')+'width=800'
 response=session.get(render,timeout=40);response.raise_for_status()
 final=urlsplit(response.url)
 if final.scheme!='https' or final.hostname!='cdn.shopify.com':raise ValueError('Image redirected away from approved CDN')
 if len(response.content)>250000 or not response.headers.get('Content-Type','').startswith('image/'):raise ValueError('Saved cover exceeds image review bounds')
 return dict(source_url=render,sha256=hashlib.sha256(response.content).hexdigest(),content_type=response.headers['Content-Type'],base64=base64.b64encode(response.content).decode(),**proof)

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
     response=read(url+'.js');raw=response.json()
     if raw.get('handle')!=handle:raise ValueError('Product handle mismatch')
     if item.get('inspect_commercial') is True:
      import hashlib
      rec['product_response_sha256']=hashlib.sha256(response.content).hexdigest()
      rec['commercial_source']={'endpoint':url+'.js','id':raw.get('id'),'available':raw.get('available'),'price':raw.get('price'),'compare_at_price':raw.get('compare_at_price'),'variants':[{k:v.get(k) for k in ('id','title','price','compare_at_price','available','sku')} for v in raw.get('variants',[])]}

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
   if item.get('inspect_bundle') or not product or not (product.get('description') or product.get('body_html')):
    soup=BeautifulSoup(read(url).text,'html.parser')
    if item.get('inspect_media') is True:
     selectors=['.woocommerce-product-gallery img','.images img','.product img','meta[property="og:image"]']
     rec['public_media_probe']={'canonical':[n.get('href') for n in soup.select('link[rel=canonical][href]')[:3]],'headings':[n.get_text(' ',strip=True)[:300] for n in soup.select('h1')[:5]],'cart_ids':[n.get('value') or n.get('data-product_id') for n in soup.select('button[name="add-to-cart"],input[name="add-to-cart"],form[data-product_id]')[:10]],'images':{selector:[{k:n.get(k) for k in ('src','data-src','data-lazy-src','data-large_image','content') if n.get(k) and not str(n.get(k)).startswith('data:')} for n in soup.select(selector)[:12]] for selector in selectors}}
    scripts=[]
    for node in soup.select('script[type="application/ld+json"]'):
     try:scripts.append(json.loads(node.get_text()))
     except ValueError:pass
    rec['structured_products']=scripts[:8]
    if item.get('inspect_bundle'):
     from urllib.parse import urljoin
     rec['public_bundle_scripts']=[urljoin(url,n['src']).split('?')[0] for n in soup.select('script[src]') if re.search(r'(?i)bundle',n['src'])][:12]
     raw=str(soup.select_one('main') or soup)
     contexts=[]
     for match in list(re.finditer(r'(?i)fastbundle|fast-bundle|bundle_id|bundleId|bundle-products|bundle_products',raw))[:12]:
      context=raw[max(0,match.start()-250):match.end()+800]
      if re.search(r'(?i)password|access.token|authorization|secret|api.key|set.cookie',context):continue
      contexts.append(context)
     rec['public_bundle_context']=contexts

    parts=soup.select('.product__description, .product-description, #product-description, [class*="bundle"][class*="title"], [class*="bundle"][class*="description"]')
    rec['public_description_fragments']=[n.get_text(' ',strip=True)[:8000] for n in parts[:10] if n.get_text(' ',strip=True)]
   rec['status']='review_evidence_collected'
  except Exception as exc:rec['error']=str(exc)[:500]
  if item.get('inspect_saved_cover') is True:
   try:rec['public_image']=capture_saved_cover(item,session)
   except Exception as exc:rec['image_error']=str(exc)[:500]
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
