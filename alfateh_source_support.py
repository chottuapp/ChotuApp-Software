"""Exact public Alfateh product offers and variant selector state."""
import csv,json,re,time,hashlib
from decimal import Decimal,InvalidOperation
from pathlib import Path
from urllib.parse import urlsplit,urljoin
from urllib.robotparser import RobotFileParser
from xml.etree import ElementTree as ET
from bs4 import BeautifulSoup
from next_public_support import public_next_product_state
BASE='https://alfatehgarments.com'
AGENT='ChotuAppCatalogRefresh'
class IncompleteProduct(ValueError):pass

def same_product(url,expected):
 a,b=urlsplit(url),urlsplit(expected)
 return a.scheme=='https' and (a.hostname or '').removeprefix('www.')==(b.hostname or '').removeprefix('www.') and a.path.rstrip('/')==b.path.rstrip('/') and not a.query

def amount(value):
 try:n=Decimal(str(value))
 except InvalidOperation as exc:raise ValueError('Unreadable source price') from exc
 if not n.is_finite() or n<=0:raise ValueError('Invalid source price')
 return n

def normalize(page,url):
 soup=BeautifulSoup(page,'html.parser');records=[]
 def walk(value):
  if isinstance(value,dict):
   if value.get('@type')=='Product':records.append(value)
   for v in value.values():walk(v)
  elif isinstance(value,list):
   for v in value:walk(v)
 for script in soup.select('script[type="application/ld+json"]'):
  try:walk(json.loads(script.get_text()))
  except ValueError:pass
 if len(records)!=1:raise IncompleteProduct('Exact public product metadata missing or ambiguous')
 raw=records[0];offer=raw.get('offers',{});title=raw.get('name');h1=soup.select_one('h1')
 if isinstance(offer,list) or offer.get('priceCurrency')!='PKR' or not same_product(offer.get('url',''),url):raise ValueError('Exact PKR offer identity unverified')
 if not h1 or h1.get_text(' ',strip=True)!=title:raise ValueError('Public product heading/metadata mismatch')
 state=public_next_product_state(page);lists=state['public_variant_data']
 if len(lists)!=1 or not lists[0]:raise IncompleteProduct('Exact public variant selector missing')
 variants=[];sizes=[];colors=[];seen=set();dimensions=[]
 for field,label,key in (('size','Size','value'),('color','Color','name')):
  values=[(v.get(field) or {}).get(key) for v in lists[0]]
  if all(v.get(field) is None for v in lists[0]):continue
  if any(not isinstance(value,str) or not value for value in values):raise IncompleteProduct('Exact source '+field+' selection missing')
  dimensions.append((field,label,key))
 for v in lists[0]:
  vid=v.get('id');size=(v.get('size') or {}).get('value');color=(v.get('color') or {}).get('name');stock=v.get('availableStock');active=v.get('isActive')
  if not vid or vid in seen:raise ValueError('Missing or duplicate source variant identity')
  if not isinstance(stock,int) or isinstance(stock,bool) or stock<0 or not isinstance(active,bool):raise IncompleteProduct('Explicit public stock or active state missing')
  regular=amount(v.get('regularPrice'));sale=amount(v['salePrice']) if v.get('salePrice') is not None else regular
  if sale>regular:raise ValueError('Source sale exceeds regular price')
  seen.add(vid);sizes.append(size);colors.append(color)
  row=dict(id=vid,sku=str(v.get('sku') or ''),price=str(sale),compare_at_price=str(regular) if sale<regular else None,available=active and stock>0,inventory_quantity=stock)
  for index,(field,label,key) in enumerate(dimensions,1):row['option'+str(index)]=v[field][key]
  variants.append(row)
 selected=[v for v in variants if v['sku']==raw.get('sku')]
 available=offer.get('availability')
 if available not in ('https://schema.org/InStock','https://schema.org/OutOfStock'):raise IncompleteProduct('Explicit selected offer availability missing')
 # Product Code identifies the parent. A uniform-price product offer does not
 # claim to select a size/colour; keep every actual variant SKU and stock value.
 uniform={amount(v['price']) for v in variants}
 if len(uniform)==1:
  if amount(offer.get('price')) not in uniform:raise ValueError('Published selected SKU/price mismatch')
  expected_available=any(v['available'] for v in variants)
 else:
  if len(selected)!=1 or amount(selected[0]['price'])!=amount(offer.get('price')):raise ValueError('Published selected SKU/price mismatch')
  expected_available=selected[0]['available']
 if (available.endswith('/InStock'))!=expected_available:raise ValueError('Selected source stock/offer conflict')
 images=raw.get('image') or []
 if isinstance(images,str):images=[images]
 images=[dict(src=urljoin(BASE,i),position=index+1) for index,i in enumerate(images) if isinstance(i,str) and urljoin(BASE,i).startswith('https://')]
 if not images:raise IncompleteProduct('Real source product photos missing')
 details=soup.select('main div.mt-8.space-y-4')
 body=str(details[0]) if len(details)==1 else str(raw.get('description') or '')
 from locked_store_rules import incomplete_product_reasons
 if incomplete_product_reasons(dict(title=title,body_html=body)):raise IncompleteProduct('Incomplete source description')
 return dict(id=hashlib.sha256(urlsplit(url).path.encode()).hexdigest()[:20],handle=urlsplit(url).path.rstrip('/').rsplit('/',1)[-1],title=title,body_html=body,vendor=(raw.get('brand') or {}).get('name',''),images=images,variants=variants,options=[dict(name=label) for _,label,_ in dimensions],_source_url=url,_source_product_code=raw.get('sku'))

class PublicCatalog:
 def __init__(self,g,log):self.g=g;self.log=log;self.robot=None;self.last=0
 def read(self,url):
  p=urlsplit(url)
  if p.scheme!='https' or (p.hostname or '').removeprefix('www.')!='alfatehgarments.com' or p.username or p.password:raise ValueError('Outside approved public Alfateh host')
  if self.robot and not self.robot.can_fetch(AGENT,url):raise ValueError('Public robots rule disallows source path')
  self.g['_chotu_wait']();delay=max(0,self.last+1.5-time.monotonic())
  if delay:self.g['_chotu_backoff'](delay,'Alfateh public pacing')
  self.last=time.monotonic();response=self.g['S'].get(url,timeout=40)
  if response.status_code in (429,503):raise RuntimeError('SOURCE PAUSED: Alfateh rate limit; retry saved store after at least 60s. Checkpoint retained')
  response.raise_for_status()
  if (urlsplit(response.url).hostname or '').removeprefix('www.')!='alfatehgarments.com':raise ValueError('Foreign source redirect')
  if len(response.content)>5*1024*1024:raise ValueError('Public source exceeds response bound')
  return response
 def catalog(self):
  robots=self.read(BASE+'/robots.txt');self.robot=RobotFileParser();self.robot.parse(robots.text.splitlines())
  maps=re.findall(r'(?im)^Sitemap:\s*(https://\S+)',robots.text);queue=list(maps);seen=set();urls=[]
  while queue:
   url=queue.pop(0)
   if url in seen:continue
   if len(seen)>=100:raise ValueError('Public sitemap enumeration exceeds bound')
   seen.add(url);tree=ET.fromstring(self.read(url).content);kind=tree.tag.rsplit('}',1)[-1]
   links=[n.text.strip() for n in tree.iter() if n.tag.rsplit('}',1)[-1]=='loc' and n.text]
   if kind=='sitemapindex':queue.extend(links)
   elif kind=='urlset':urls.extend(u for u in links if re.fullmatch(r'/product/[^/]+/?',urlsplit(u).path))
   else:raise ValueError('Unknown public sitemap format')
  if not urls:
   page=self.read(BASE+'/shop');soup=BeautifulSoup(page.text,'html.parser')
   urls=[urljoin(BASE,a['href']) for a in soup.select('a[href]') if a['href'].startswith('/product/')]
  urls=list(dict.fromkeys(urls))
  if not urls:raise ValueError('No public product URLs discovered')
  products=[]
  for i,url in enumerate(urls,1):
   response=self.read(url)
   try:product=normalize(response.text,url)
   except IncompleteProduct as exc:
    from locked_store_rules import record_incomplete_product
    record_incomplete_product({'_source_url':url,'source_response_sha256':hashlib.sha256(response.content).hexdigest()},BASE,'Alfateh Garments',self.g.get('__file__',__file__),[str(exc)])
    self.log('OWNER INCOMPLETE SKIP: '+url+'; '+str(exc));continue
   products.append(product)
   if i==1 or i%25==0:self.log(f'ALFATEH PUBLIC PRODUCTS: {i}/{len(urls)} exact pages inspected; {len(products)} complete products')
  self.log('REVIEW REQUIRED: public PKR offers and explicit variant stock retained; independent checkout and listing order unverified')
  return products,False

def enable_alfateh_source(g):
 if g.get('_chotu_alfateh_source'):return
 original=g['_chotuapp_run_site_original']
 def run(base,name,template,log):
  if (urlsplit(base).hostname or '').removeprefix('www.')!='alfatehgarments.com':return original(base,name,template,log)
  source=PublicCatalog(g,log);keys=('discover','collections','refresh_variant_prices','storefront_cover','verified_top20','audit_fractional_prices','storefront_price_audit');old={k:g[k] for k in keys}
  def audit(*args):
   for arg in args:
    if isinstance(arg,Path) and arg.suffix=='.csv':
     with arg.open('w',encoding='utf-8-sig',newline='') as f:
      writer=csv.writer(f);writer.writerow(['status','source','detail']);writer.writerow(['REVIEW',BASE,'Exact public PKR selected offer and published variant stock; independent checkout unverified'])
   return set()
  def ranking(*args,**kwargs):
   g['_chotu_tls'].ranking_evidence={};log('TOP 20: UNVERIFIED — no public sales ranking inferred');return []
  g.update(discover=lambda *a:source.catalog(),collections=lambda *a:{},refresh_variant_prices=lambda b,p,l:p['variants'],storefront_cover=lambda *a:None,verified_top20=ranking,audit_fractional_prices=audit,storefront_price_audit=audit)
  try:return original(BASE,name,template,log)
  finally:g.update(old)
 g['_chotuapp_run_site_original']=run;g['_chotu_alfateh_source']=True
