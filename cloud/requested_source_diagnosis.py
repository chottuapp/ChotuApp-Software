"""Bounded anonymous public evidence for the four owner-requested repairs."""
import json,os,re,time,concurrent.futures
from urllib.parse import urljoin,urlsplit
from urllib.robotparser import RobotFileParser
from xml.etree import ElementTree as ET
from bs4 import BeautifulSoup
import requests
from source_research import publish,clean_html,public_product_state
from next_public_support import public_next_product_state
AGENT='Mozilla/5.0 (compatible; ChotuAppCatalogRefresh/1.0)'
SITES={'Toynix':'https://www.toynix.pk','Alfateh Garments':'https://alfatehgarments.com','Mansab':'https://mansabpk.com','Rung Rez':'https://rungrez.com.pk'}
SENSITIVE=re.compile('token|secret|password|authorization|api.?key|bearer|email|phone|cookie|session',re.I)
def safe(value):
 if isinstance(value,dict):return {k:safe(v) for k,v in value.items() if not SENSITIVE.search(k)}
 if isinstance(value,list):return [safe(v) for v in value[:150]]
 return value

def inspect(item):
 name,base=item;out={'name':name,'responses':[]};session=requests.Session();session.headers['User-Agent']=AGENT;robot=None
 def read(url):
  if (urlsplit(url).hostname or '').removeprefix('www.')!=urlsplit(base).hostname.removeprefix('www.'):raise ValueError('Outside source host')
  if robot and not robot.can_fetch(AGENT,url):raise ValueError('Robots disallows path')
  time.sleep(1.5);r=session.get(url,timeout=(15,40));out['responses'].append({'url':url,'status':r.status_code,'bytes':len(r.content)})
  if len(r.content)>5*1024**2:raise ValueError('Response too large')
  if r.status_code in (401,403,429,503):
   out['denial']={'url':url,'status':r.status_code,'challenge':r.headers.get('cf-mitigated')=='challenge' or bool(re.search(r'cf-chl-|<title>\s*(?:Just a moment|Attention Required)',r.text,re.I)),'title':BeautifulSoup(r.text,'html.parser').title.get_text()[:120] if BeautifulSoup(r.text,'html.parser').title else ''}
   raise ValueError('Source denied/limited; no retries')
  r.raise_for_status();return r
 def detail(url):
  r=read(url);soup=BeautifulSoup(r.text,'html.parser');state=public_next_product_state(r.text)
  d={'url':url,'structured':[],'html':clean_html(r.text)[:45000],'next':state,'nuxt':public_product_state(soup),'inline_shapes':[],'commercial_snippets':[]}
  for node in soup.find_all('script'):
   text=node.string or node.get_text()
   if node.get('type')=='application/ld+json':
    try:d['structured'].append(safe(json.loads(text)))
    except ValueError:pass
   if not node.get('src') and node.get('type')!='application/ld+json':
    start=text[:100]
    d['inline_shapes'].append({'type':node.get('type'),'id':node.get('id'),'length':len(text),'prefix':start if not SENSITIVE.search(start) else '[redacted]'})
    for m in list(re.finditer(r'variants|stock_quantity|stockQuantity|regular_price|sale_price|product_variants|selectedVariant|variantId|availableStock|productData',text))[:12]:
     snippet=text[max(0,m.start()-80):m.end()+250]
     if not SENSITIVE.search(snippet):d['commercial_snippets'].append(snippet)
  return d,r.text
 try:
  r=read(base+'/robots.txt');robot=RobotFileParser();robot.parse(r.text.splitlines())
  if name=='Toynix':
   for query in ('limit=1','limit=50&page=1','limit=50&page=2'):
    r=read(base+'/products.json?'+query);data=r.json();out.setdefault('catalog_checks',[]).append({'query':query,'products':len(data.get('products',[])),'sample_ids':[p.get('id') for p in data.get('products',[])[:3]]})
   return out
  home=read(base+'/');soup=BeautifulSoup(home.text,'html.parser')
  links=list(dict.fromkeys(urljoin(base,a['href']) for a in soup.select('a[href]') if a['href'].startswith(('/product/','/products/'))))
  out['home_nuxt']=public_product_state(soup)
  if name in ('Alfateh Garments','Rung Rez'):
   maps=re.findall(r'(?im)^Sitemap:\s*(https://\S+)',r.text)
   for link in maps[:1]:
    tree=ET.fromstring(read(link).content);locs=[n.text for n in tree.iter() if n.tag.endswith('loc') and n.text]
    if tree.tag.endswith('sitemapindex'):
     child=next((u for u in locs if 'product' in u.lower()),locs[0]);tree=ET.fromstring(read(child).content);locs=[n.text for n in tree.iter() if n.tag.endswith('loc') and n.text]
    links=list(dict.fromkeys([u for u in locs if '/product/' in u or '/products/' in u]+links))
  out['details']=[]
  for link in links[:(25 if name in ('Alfateh Garments','Rung Rez') else 2)]:
   d,html=detail(link)
   if name in ('Alfateh Garments','Rung Rez'):
    if name=='Alfateh Garments':from alfateh_source_support import normalize
    else:from rungrez_source_support import normalize
    try:p=normalize(html,link);out.setdefault('valid_products',[]).append({'url':link,'variants':len(p['variants'])});continue
    except ValueError as e:d['normalize_error']=str(e)
   out['details'].append(d)
   if name in ('Alfateh Garments','Rung Rez') and any(x in d.get('normalize_error','') for x in ('mismatch','conflict')):break
 except Exception as exc:out['error']=str(exc)[:350]
 finally:session.close()
 return out

def main():
 with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:sources=list(pool.map(inspect,SITES.items()))
 publish({'run_id':os.environ['GITHUB_RUN_ID'],'sources':sources},branch='requested-store-reports')
 print('Sanitized source repair evidence saved')
if __name__=='__main__':main()
