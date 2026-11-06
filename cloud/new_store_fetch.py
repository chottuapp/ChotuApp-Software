"""Additive fetch requests before the owner supplies shop codes."""
import concurrent.futures,json,os,re,hashlib
from datetime import datetime,timezone
from pathlib import Path
from urllib.parse import urlsplit
from runtime import validate_site
from requested_stores import probe as source_probe,root_lane,gh
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

def public_next_product_state(html):
    """Read JSON-only public Next records, including split stream chunks."""
    from bs4 import BeautifulSoup
    fields={'id','name','title','slug','price','basePrice','salePrice','description','images','imageUrls','image','category','categoryId','variants','sizes','colors','stock','stockQuantity','isActive','active','currency','sku','isAvailable','inStock','quantity','sale','discount','sellingPrice','retailPrice','regularPrice','discountPrice','minPrice','maxPrice','stockOnHand','stockReserved','stockAvailable','inventoryQuantity','productId','colorName','sizeName','sizeLabel','colorHex','priceOverride','department','size','color','status','isPublished','trackStock','stockQty','baseRetailPrice','url','imageUrl','position','alt','onHand','reserved','available','isPrimary'}
    result={'hydration_products':[],'object_key_shapes':[],'product_contexts':[],'public_variant_data':[],'public_variant_shapes':[]}
    def clean(value):
        if isinstance(value,dict):return {k:clean(v) for k,v in value.items() if k in fields}
        if isinstance(value,list):return [clean(v) for v in value[:500]]
        return value
    def walk(value):
        if isinstance(value,dict):
            if 'variants' in value or 'product' in value:
                shape=sorted(value)
                if shape not in result['object_key_shapes']:result['object_key_shapes'].append(shape)
            if isinstance(value.get('variants'),list):
                result['public_variant_data'].append(clean(value['variants']))
                result['public_variant_shapes'].append([{k:sorted(v) if isinstance(v,dict) else type(v).__name__ for k,v in variant.items()} for variant in value['variants'][:3] if isinstance(variant,dict)])
            if isinstance(value.get('product'),dict):
                result['product_contexts'].append({k:clean(v) for k,v in value.items() if k in ('product','variants','images','sizes','colors')})
            if value.get('id') and (value.get('name') or value.get('title')):
                candidate=clean(value)
                if len(json.dumps(candidate))<150000 and candidate not in result['hydration_products']:result['hydration_products'].append(candidate)
            for v in value.values():walk(v)
        elif isinstance(value,list):
            for v in value:walk(v)
    chunks=[]
    for node in BeautifulSoup(html,'html.parser').find_all('script'):
        text=node.get_text()
        for match in re.finditer(r'self\.__next_f\.push\(',text):
            try:array,_=json.JSONDecoder().raw_decode(text[match.end():])
            except ValueError:continue
            if isinstance(array,list) and len(array)>=2 and isinstance(array[1],str):chunks.append(array[1])
    for line in ''.join(chunks).splitlines():
        try:walk(json.loads(line.partition(':')[2]))
        except ValueError:pass
    return result

def probe(site):
 result=source_probe(site)
 if result.get('status')!='adapter_required':return result
 # Bounded public evidence for an unknown storefront, never a guessed adapter.
 import requests
 from urllib.robotparser import RobotFileParser
 from bs4 import BeautifulSoup
 from source_research import clean_html,public_url
 try:
  agent='ChotuAppRequestedStoreCheck/1.0';base=site['url'].rstrip('/')
  session=requests.Session();session.headers['User-Agent']=agent
  robots=RobotFileParser();response=session.get(base+'/robots.txt',timeout=30)
  if response.status_code==404:robots.parse([])
  else:response.raise_for_status();robots.parse(response.text.splitlines())
  if not robots.can_fetch(agent,base+'/'):raise ValueError('Public robots rule disallows homepage')
  response=session.get(base+'/',timeout=30);response.raise_for_status()
  if (urlsplit(response.url).hostname or '').removeprefix('www.')!=urlsplit(base).hostname.removeprefix('www.'):raise ValueError('Foreign storefront redirect')
  if len(response.content)>5*1024*1024:raise ValueError('Homepage exceeds diagnostic bound')
  soup=BeautifulSoup(response.text,'html.parser')
  result['public_homepage_html']=clean_html(response.text)
  result['public_script_paths']=[public_url(__import__('urllib.parse',fromlist=['urljoin']).urljoin(response.url,s['src'])) for s in soup.select('script[src]')][:25]
  result['public_page_title']=soup.title.get_text(' ',strip=True) if soup.title else ''
  from urllib.parse import urljoin
  import time
  def public_read(url):
   if (urlsplit(url).hostname or '').removeprefix('www.')!=urlsplit(base).hostname.removeprefix('www.') or not robots.can_fetch(agent,url):raise ValueError('Unapproved public diagnostic URL')
   time.sleep(1.5);r=session.get(url,timeout=30);r.raise_for_status()
   if len(r.content)>3*1024*1024:raise ValueError('Diagnostic response exceeds bound')
   return r
  product_link=next((urljoin(base,a['href']) for a in soup.select('a[href]') if a['href'].startswith('/product/')),None)
  if product_link:
   detail=public_read(product_link);detail_soup=BeautifulSoup(detail.text,'html.parser')
   result['public_product_page']={'url':product_link,'html':clean_html(detail.text),'structured':[],'hydration_products':[]}
   for node in detail_soup.select('script[type="application/ld+json"]'):
    try:result['public_product_page']['structured'].append(json.loads(node.get_text()))
    except ValueError:pass
   result['public_product_page'].update(public_next_product_state(detail.text))
   scripts=[urljoin(product_link,t['src']) for t in detail_soup.select('script[src]') if '/app/' in t['src'] and ('page-' in t['src'] or 'layout-' in t['src'])]
   result['public_client_route_clues']=[]
   for script in scripts[:3]:
    if not robots.can_fetch(agent,script):continue
    text=public_read(script).text
    for match in re.finditer(r'/api/[A-Za-z0-9_/?=&${}.:-]+',text):
     context=text[max(0,match.start()-100):match.end()+160]
     if not re.search(r'token|secret|authorization|password|session|email|phone',context,re.I):result['public_client_route_clues'].append(context[:400])

 except (requests.RequestException,ValueError) as exc:result['inspection_error']=str(exc)[:300]
 return result

def main():
 request=json.loads((ROOT/'cloud/new-store-fetch-request.json').read_text());stores=validate(request)
 report=dict(run_id=os.environ['GITHUB_RUN_ID'],request_id=request['request_id'],checked_utc=datetime.now(timezone.utc).isoformat(),shop_codes='Pending owner; blank in exports',stores=[],groups=[],status='checking')
 def save():
  report['checked_utc']=datetime.now(timezone.utc).isoformat();publish(report,branch='requested-store-reports')
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
