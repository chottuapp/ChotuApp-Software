"""Robots-aware exact-host sitemap reader and reusable non-Shopify export hook."""
import csv,hashlib,re,time
from pathlib import Path
from urllib.parse import urlsplit,urljoin
from urllib.robotparser import RobotFileParser
from xml.etree import ElementTree as ET
AGENT='Mozilla/5.0 (compatible; ChotuAppCatalogRefresh/1.0)'
class PublicCatalog:
 def __init__(self,g,log,base,normalize,name):self.g=g;self.log=log;self.base=base;self.normalize=normalize;self.name=name;self.robot=None;self.last=0
 def read(self,url):
  p=urlsplit(url)
  if p.scheme!='https' or (p.hostname or '').removeprefix('www.')!=urlsplit(self.base).hostname.removeprefix('www.') or p.username or p.password:raise ValueError('Outside approved public source host')
  if self.robot and not self.robot.can_fetch(AGENT,url):raise ValueError('Public robots disallows source URL')
  self.g['_chotu_wait']();delay=max(0,self.last+1.5-time.monotonic())
  if delay:self.g['_chotu_backoff'](delay,'Public source pacing')
  self.last=time.monotonic();r=self.g['S'].get(url,timeout=40)
  if r.status_code in (429,503):raise self.g.get('ChotuRateLimited',RuntimeError)('SOURCE PAUSED: public source rate limit; checkpoint retained')
  if (urlsplit(r.url).hostname or '').removeprefix('www.')!=p.hostname.removeprefix('www.'):raise ValueError('Foreign source redirect')
  if len(r.content)>5*1024**2:raise ValueError('Public source response exceeds bound')
  r.raise_for_status();return r
 def catalog(self):
  r=self.read(self.base+'/robots.txt');self.robot=RobotFileParser();self.robot.parse(r.text.splitlines())
  maps=re.findall(r'(?im)^Sitemap:\s*(https://\S+)',r.text)
  if not maps:
   from bs4 import BeautifulSoup
   page=self.read(self.base+'/');maps=[urljoin(self.base,n['href']) for n in BeautifulSoup(page.text,'html.parser').select('a[href],link[href]') if 'sitemap' in n['href'] and n['href'].endswith('.xml')]
  queue=list(dict.fromkeys(maps));seen=set();urls=[]
  while queue:
   url=queue.pop(0)
   if url in seen:continue
   if len(seen)>=100:raise ValueError('Sitemap enumeration exceeds bound')
   seen.add(url);tree=ET.fromstring(self.read(url).content);kind=tree.tag.rsplit('}',1)[-1];locs=[n.text.strip() for n in tree.iter() if n.tag.rsplit('}',1)[-1]=='loc' and n.text]
   if kind=='sitemapindex':queue.extend(locs)
   elif kind=='urlset':urls.extend(u for u in locs if re.fullmatch(r'/products?/[^/]+/?',urlsplit(u).path))
   else:raise ValueError('Unknown public sitemap schema')
  urls=list(dict.fromkeys(urls))
  if not urls or len(urls)>20000:raise ValueError('Complete product sitemap unavailable or exceeds bound; no partial homepage fallback')
  products=[]
  for i,url in enumerate(urls,1):
   r=self.read(url)
   from laam_source_support import ConfirmedOutOfStock
   try:p=self.normalize(r.text,url)
   except ConfirmedOutOfStock:
    self.log('OWNER STOCK SKIP: '+url+'; source confirms no sellable variants');continue
   from locked_store_rules import incomplete_product_reasons,record_incomplete_product
   reasons=incomplete_product_reasons(p)
   if reasons:record_incomplete_product(p,self.base,self.name,self.g.get('__file__',__file__),reasons);continue
   products.append(p)
   if i==1 or i%25==0:self.log(f'PUBLIC PRODUCTS: {i}/{len(urls)} exact source pages checked; {len(products)} complete')
  return products,False

def enable_public_source(g,base,name,normalize,flag):
 if g.get(flag):return
 original=g['_chotuapp_run_site_original']
 def run(url,store,template,log):
  if (urlsplit(url).hostname or '').removeprefix('www.')!=urlsplit(base).hostname.removeprefix('www.'):return original(url,store,template,log)
  source=PublicCatalog(g,log,base,normalize,store);keys=('discover','collections','refresh_variant_prices','storefront_cover','verified_top20','audit_fractional_prices','storefront_price_audit');old={k:g[k] for k in keys}
  def audit(*args):
   for arg in args:
    if isinstance(arg,Path) and arg.suffix=='.csv':
     with arg.open('w',encoding='utf-8-sig',newline='') as f:
      w=csv.writer(f);w.writerow(['status','source','detail']);w.writerow(['REVIEW',base,'Exact public PKR variant offers retained; independent checkout and full website order unverified'])
   return set()
  def ranking(*args,**kwargs):g['_chotu_tls'].ranking_evidence={};return []
  g.update(discover=lambda *a:source.catalog(),collections=lambda *a:{},refresh_variant_prices=lambda b,p,l:p['variants'],storefront_cover=lambda *a:None,verified_top20=ranking,audit_fractional_prices=audit,storefront_price_audit=audit)
  try:return original(base,store,template,log)
  finally:g.update(old)
 g['_chotuapp_run_site_original']=run;g[flag]=True
