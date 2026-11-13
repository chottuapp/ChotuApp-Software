"""Owner-approved exact brands, discovered only through Naheed public pages."""
import json,re,unicodedata
import requests
from pathlib import Path
from functools import lru_cache
from urllib.parse import urlsplit,urljoin,parse_qsl,urlencode
from bs4 import BeautifulSoup
BASE='https://www.naheed.pk'

def brand_key(value):
 return ' '.join(unicodedata.normalize('NFKC',str(value or '')).casefold().split())

@lru_cache(maxsize=1)
def load_request():
 p=Path(__file__).parent/'naheed-brand-refresh.json'
 if not p.exists():p=Path(__file__).parent/'cloud/naheed-brand-refresh.json'
 if not p.exists():return None
 r=json.loads(p.read_text())
 if not r.get('active'):return None
 brands=r.get('brands',[])
 if r.get('source_host')!='www.naheed.pk' or not 1<=len(brands)<=300:raise ValueError('Unapproved Naheed brand request')
 seen=set()
 for item in brands:
  key=brand_key(item.get('brand'));expected=BASE+'/catalogsearch/result/?'+urlencode({'q':item.get('brand','')})
  if not key or key in seen or key=='unbranded' or item.get('url')!=expected:raise ValueError('Invalid/duplicate exact Naheed brand scope')
  seen.add(key)
  if len(item.get('examples',[]))>2 or any(not product_url(u) for u in item.get('examples',[])):raise ValueError('Invalid saved Naheed brand example')
 return r

def product_url(url):
 p=urlsplit(str(url));return p.scheme=='https' and p.netloc=='www.naheed.pk' and bool(p.path.strip('/')) and '/' not in p.path.strip('/') and not p.query and not p.fragment

def vendor_link(html,url,brand):
 soup=BeautifulSoup(html,'html.parser');canonical=soup.select_one('link[rel=canonical][href]');node=soup.select_one('.product-info-main .brand-name a[href]')
 if not canonical or urljoin(url,canonical['href']).rstrip('/')!=url.rstrip('/') or not node or brand_key(node.get_text(' ',strip=True))!=brand_key(brand):return None
 link=urljoin(url,node['href']);p=urlsplit(link);q=parse_qsl(p.query)
 if p.scheme!='https' or p.netloc!='www.naheed.pk' or p.fragment:return None
 if p.path.rstrip('/')=='/allproducts' and len(q)==1 and q[0][0]=='manufacturer' and re.fullmatch(r'\d+',q[0][1]):return link
 # Naheed also publishes named brand landing pages (e.g. Sajiero).
 # Accept only a link exposed by the exact product's matching manufacturer.
 if not q and re.fullmatch(r'/[a-z0-9][a-z0-9-]{0,150}/?',p.path) and p.path.rstrip('/')!=urlsplit(url).path.rstrip('/') and p.path.rstrip('/') not in ('/allproducts','/customer','/checkout','/wishlist','/cart','/contact','/about-us'):return link
 return None

def discover_brand_scope(reader,scope):
 """Prefer a current identity-matched vendor link; reconcile using exact brand search."""
 vendor=None
 for url in scope.get('examples',[]):
  try:page=reader.read_page(url)
  except requests.HTTPError as exc:
   if exc.response is not None and exc.response.status_code in (404,410):continue
   raise
  vendor=vendor_link(page,url,scope['brand'])
  if vendor:break
 vendor_proof=None
 if vendor:
  links,total,pages=discover_current_vendor(reader,scope,vendor)
  vendor_proof=dict(url=vendor,visible=len(links),total=total,pages=sorted(pages),count_changed=reader.scope_count_changed)
  if not reader.scope_count_changed and total is not None and len(links)==total:
   reader.brand_proofs.append(dict(brand=scope['brand'],scope_url=scope['url'],selected='current_vendor_page',vendor=vendor_proof))
   return links,total,pages
 fresh=reader.force_fresh if hasattr(reader,'force_fresh') else False
 reader.force_fresh=True
 try:links,total,pages=reader.discover_scope(dict(scope,_resolved_brand=True))
 finally:reader.force_fresh=fresh
 search_changed=reader.scope_count_changed;search_totals=list(reader.scope_totals)
 search_partial=reader.scope_partial;search_expected=reader.scope_expected
 if not vendor:
  prefix=re.sub(r'[^a-z0-9]+','-',brand_key(scope['brand'])).strip('-')
  candidates=sorted(links,key=lambda u:(not urlsplit(u).path.lstrip('/').startswith(prefix+'-'),u))
  for url in candidates[:3]:
   candidate=vendor_link(reader.read_page(url),url,scope['brand'])
   if not candidate:continue
   found,expected,traversed=discover_current_vendor(reader,scope,candidate)
   vendor_proof=dict(url=candidate,visible=len(found),total=expected,pages=sorted(traversed),count_changed=reader.scope_count_changed)
   if not reader.scope_count_changed and expected is not None and len(found)==expected:
    reader.brand_proofs.append(dict(brand=scope['brand'],scope_url=scope['url'],selected='current_vendor_page',vendor=vendor_proof))
    return found,expected,traversed
   # The complete search traversal remains the selected owner-approved scope.
   reader.scope_count_changed=search_changed;reader.scope_totals=search_totals
   reader.scope_partial=search_partial;reader.scope_expected=search_expected
   break
 reader.brand_proofs.append(dict(brand=scope['brand'],scope_url=scope['url'],selected='exact_brand_search',vendor=vendor_proof,search=dict(visible=len(links),total=total,pages=sorted(pages),count_changed=reader.scope_count_changed)))
 if links and total is None:
  from grocery_browser_support import ListingRenderIncomplete
  raise ListingRenderIncomplete('Exact brand search total is unverified; current vendor/search evidence retained; no partial brand completion')
 return links,total,pages

def select_brand_category(product,scopes):
 exact=[s for s in scopes if s.get('brand') and brand_key(s['brand'])==brand_key(product.get('manufacturer'))]
 if not exact:raise ValueError('Search hit manufacturer is outside the requested exact brands')
 categories=product.get('categories',[])
 if not categories or not str(categories[-1].get('name') or '').strip():raise ValueError('Verified Naheed product category missing')
 return exact[0]['url'],categories[-1]['name']

def verified_vendor_redirect(error,brand):
 """Only a source-linked vendor may rename to a same-host branded canonical page."""
 old=urlsplit(error.requested);new=urlsplit(error.actual)
 if any(p.scheme!='https' or p.netloc!='www.naheed.pk' or p.query or p.fragment or not re.fullmatch(r'/[a-z0-9][a-z0-9-]{0,150}/?',p.path) for p in (old,new)):return None
 soup=BeautifulSoup(error.html,'html.parser');canonical=soup.select_one('link[rel=canonical][href]');heading=soup.select_one('h1')
 if not canonical or urljoin(error.actual,canonical['href']).rstrip('/')!=error.actual.rstrip('/') or not heading:return None
 if not re.search(r'(?<!\w)'+re.escape(brand_key(brand))+r'(?!\w)',brand_key(heading.get_text(' ',strip=True))):return None
 return error.actual

def discover_current_vendor(reader,scope,vendor):
 from chotu_groceries_source_support import GroceryScopeRedirect
 try:return reader.discover_scope(dict(scope,url=vendor,_resolved_brand=True))
 except GroceryScopeRedirect as exc:
  target=verified_vendor_redirect(exc,scope['brand'])
  if not target:raise
  reader.log('GROCERY VENDOR RENAMED: '+vendor+' -> '+target+'; exact source brand/canonical verified')
  return reader.discover_scope(dict(scope,url=target,_resolved_brand=True))
