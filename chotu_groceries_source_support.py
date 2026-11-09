"""Owner-selected public HTML grocery pages; exact source offers and breadcrumbs."""
import hashlib,html,json,re,time
from pathlib import Path
from decimal import Decimal,InvalidOperation
from urllib.parse import urlsplit,urljoin,parse_qsl,urlencode,urlunsplit
from bs4 import BeautifulSoup
BASE='https://www.naheed.pk';STORE='ChotuApp Groceries'
class IncompleteProduct(ValueError):pass

def norm(value):return re.sub(r'\s+',' ',html.unescape(str(value or ''))).strip()
def amount(value):
 try:v=Decimal(str(value))
 except InvalidOperation:raise ValueError('Invalid source price')
 if not v.is_finite() or v<=0 or v*10000!=(v*10000).to_integral_value():raise ValueError('Unsupported exact PKR price')
 return v

def electronic_item(name,categories):
 taxonomy=' > '.join(categories)
 if re.search(r'\b(?:electronics?|mobile phones?|smartphones?|computers?|computer accessories|home appliances?|kitchen appliances?|audio equipment|headphones?|cameras?)\b',taxonomy,re.I):return True
 objects=r'\b(?:laptops?|smartphones?|smartwatches?|earbuds?|headphones?|headsets?|power banks?|chargers?|usb cables?|hair dryers?|hair straighteners?|electric shavers?|electric toothbrush(?:es)?|digital thermometers?|baby monitors?|blood pressure monitors?|vibrators?)\b'
 if re.search(objects,name+' '+taxonomy,re.I):return True
 return bool(re.search(r'\b(?:electric|rechargeable|battery[ -]operated)\b.{0,35}\b(?:kettle|iron|fan|heater|blender|mixer|trimmer|massager|toy|toothbrush)\b',name,re.I))

def listing_total(text):
 match=re.search(r'\bof\s+([\d,]+)\b',text,re.I) or re.search(r'\b([\d,]+)\s+items?\b',text,re.I)
 if not match:raise ValueError('Unknown source listing total format; no guessed completion')
 return int(match[1].replace(',',''))

def product(page,url):
 soup=BeautifulSoup(page,'html.parser');canonical=soup.select_one('link[rel=canonical][href]');title=soup.select_one('h1 [itemprop=name],h1 .base,h1')
 if not canonical or urljoin(url,canonical['href']).rstrip('/')!=url.rstrip('/') or not title:raise ValueError('Exact product canonical/name unverified')
 name=norm(title.get_text(' ',strip=True))
 source_categories=[norm(a.get_text(' ',strip=True)) for a in soup.select('.breadcrumbs li a[href]')]
 if electronic_item(name,source_categories):raise IncompleteProduct('Owner grocery rule: electronic item excluded; original product retained in skip receipt')
 box=soup.select_one('.product-info-main [data-product-id][data-role=priceBox]')
 if not box or not str(box.get('data-product-id','')).isdigit():raise IncompleteProduct('Source product ID absent')
 if soup.select_one('.super-attribute-select,.swatch-attribute,.product-options-wrapper select,.product-options-wrapper input[type=radio]'):raise IncompleteProduct('Selectable source options require exact per-variant offers; no option/price guessed')
 ident=int(box['data-product-id']);sku=soup.select_one('.product-info-main .sku,.product.attribute.sku .value');brand=soup.select_one('.product-info-main .brand-name a')
 brand=norm(brand.get_text(' ',strip=True)) if brand else ''
 if re.search(r'\bnaheed\b',name+' '+brand,re.I):raise IncompleteProduct('Retailer-branded product excluded; original brand is not renamed')
 structured=[]
 def walk(v):
  if isinstance(v,dict):
   if v.get('@type')=='Product' and v not in structured:structured.append(v)
   for item in v.values():walk(item)
  elif isinstance(v,list):
   for item in v:walk(item)
 for script in soup.select('script[type="application/ld+json"]'):
  try:walk(json.loads(script.get_text()))
  except (ValueError,TypeError):continue
 candidates=[p for p in structured if norm(p.get('name'))==name]
 if len(candidates)>1:raise ValueError('Conflicting repeated source product identity/schema; no offer guessed')
 if not candidates:raise IncompleteProduct('Matching source product schema missing')
 raw=candidates[0];offers=raw.get('offers');offers=offers if isinstance(offers,list) else [offers]
 if len(offers)!=1 or not isinstance(offers[0],dict) or offers[0].get('priceCurrency')!='PKR':raise IncompleteProduct('Exact single PKR source offer missing')
 offer=offers[0];price=amount(offer.get('price'));final=box.select_one('[data-price-type=finalPrice][data-price-amount]');old=box.select_one('[data-price-type=oldPrice][data-price-amount]')
 if not final or amount(final['data-price-amount'])!=price:raise ValueError('Visible/schema source price conflict')
 regular=amount(old['data-price-amount']) if old else price
 if regular<price:raise ValueError('Source regular/selling prices disagree')
 availability=str(offer.get('availability') or '').rsplit('/',1)[-1]
 if availability not in ('InStock','OutOfStock','SoldOut'):raise IncompleteProduct('Source stock unknown')
 available=availability=='InStock'
 stock=soup.select_one('.att-stock .attribute-value,.stock.available,.stock.unavailable')
 if stock:
  label=norm(stock.get_text(' ',strip=True)).lower()
  if label in ('in stock','out of stock') and (label=='in stock')!=available:raise ValueError('Visible/schema source stock conflict')
 links=soup.select('.breadcrumbs li a[href]');categories=[dict(name=norm(a.get_text(' ',strip=True)),link=urljoin(url,a['href'])) for a in links if norm(a.get_text(' ',strip=True)).lower()!='home']
 categories=[c for c in categories if urlsplit(c['link']).hostname==urlsplit(BASE).hostname]
 if not categories:raise IncompleteProduct('Source product breadcrumb category missing')
 body=[]
 for node in soup.select('.product.attribute.description .value,.product.attribute.overview .value,#description .value,[itemprop=description],.product-description'):
  if node.find_parent(class_=re.compile(r'product-item|related|upsell|crosssell')):continue
  text=node.get_text('\n',strip=True)
  if text and text not in body:body.append(text)
 if isinstance(raw.get('description'),str):
  text=BeautifulSoup(raw['description'],'html.parser').get_text('\n',strip=True)
  if text and text not in body:body.append(text)
 specs=[]
 for row in soup.select('#product-attribute-specs-table tr'):
  cells=row.select('th,td')
  if len(cells)==2:specs.append(norm(cells[0].get_text())+': '+norm(cells[1].get_text()))
 description='\n\n'.join(body+specs)
 if re.search(r'(?i)(?:manufactured|produced|packed)\s+by\s+naheed',description):raise IncompleteProduct('Retailer manufacturer identity cannot be relabelled')
 description=re.sub(r'(?i)\bnaheed(?:\.pk)?(?:\s+(?:supermarket|superstore))?\b',STORE,description)
 images=[]
 for a in soup.select('.MagicZoom[href],a[data-zoom-id][href]'):
  value=a.get('href','')
  if value.startswith('https://') and value not in [i['src'] for i in images]:images.append(dict(src=value))
 if not images:
  for im in soup.select('.product.media img[itemprop=image],.gallery-placeholder__image'):
   value=im.get('src','')
   if value.startswith('https://'):images.append(dict(src=value))
 schema_images=raw.get('image') or []
 for value in schema_images if isinstance(schema_images,list) else [schema_images]:
  value=value.get('url') if isinstance(value,dict) else value
  if isinstance(value,str) and value.startswith('https://') and value not in [im['src'] for im in images]:images.append(dict(src=value))
 p=dict(id=ident,name=name,title=name,sku=norm(sku.get_text()) if sku else str(raw.get('sku') or ''),permalink=url,_source_url=url,body_html=description,description=description,short_description='',type='simple',is_in_stock=available,is_purchasable=available,is_on_backorder=False,prices=dict(currency_code='PKR',currency_minor_unit=4,regular_price=str(int(regular*10000)),price=str(int(price*10000)),sale_price=str(int(price*10000))),images=images,categories=categories,manufacturer=brand,source_response_sha256=hashlib.sha256(page.encode()).hexdigest())
 return p

def scope_supported(group,p):
 context=' '.join(c['name'] for c in p['categories'])+' '+p['name']
 nonfood={'Beauty & Personal Care','Shampoo & Hair Care','Soap & Body Wash','Condoms Wellness'}
 if group not in nonfood and re.search(r'\b(?:cosmetics?|skincare|skin care|hair care|shampoos?|toiletries|fragrances?)\b',context,re.I):return False
 if group=='Milk & Dairy':return bool(re.search(r'\b(?:milk|dairy|cheese|yog[hu]?urt|butter|cream)\b',context,re.I))
 if group=='Shampoo & Hair Care':return bool(re.search(r'\b(?:hair|shampoo|conditioner|scalp)\b',context,re.I))
 if group=='Pet Food':return bool(re.search(r'\b(?:pet food|cat food|dog food|treats?|kibble)\b',context,re.I))
 if group=='Condoms Wellness':return bool(re.search(r'\b(?:condoms?|lubricants?|sexual|intimate|contracept)\b',context,re.I))
 return True

class PublicCatalog:
 label='Owner-selected public HTML'
 def __init__(self,g,log):
  self.g=g;self.log=log;self.products={};self.last=0;self.force_fresh=False;self.coverage_issues=[];self.coverage_status='incomplete';self.scope_count_changed=False;self.scope_totals=[]
  local=Path(__file__).with_name('chotu-groceries-request.json');local=local if local.exists() else Path(__file__).parent/'cloud/chotu-groceries-request.json'
  self.request=json.loads(local.read_text())
 def supports(self,base):return base.rstrip('/')==BASE
 def read_page(self,url):
  p=urlsplit(url)
  if p.scheme!='https' or p.hostname!=urlsplit(BASE).hostname or p.username or p.password:raise ValueError('Outside exact grocery source host')
  self.g['_chotu_wait']();delay=max(0,self.last+1.5-time.monotonic())
  if delay:self.g['_chotu_backoff'](delay,'Selected public grocery page pacing')
  self.last=time.monotonic()
  self.g.get('_chotu_debug_stage',lambda *a:None)('Grocery listing pages' if p.path.startswith(('/catalogsearch/','/allproducts')) else 'Grocery source product pages')
  self.g.get('_chotu_debug_request',lambda *a:None)(url,1)
  getter=(getattr(self.g['S'],'get_fresh',None) or self.g['S'].get) if self.force_fresh else self.g['S'].get
  r=getter(url,timeout=(15,45))
  self.g.get('_chotu_debug_response',lambda *a,**k:None)(r.status_code,len(r.content),cached=bool(getattr(r,'_chotu_cache_hit',False)))
  if r.status_code in (429,500,502,503,504):raise RuntimeError('SOURCE PAUSED: grocery public source temporary failure; retry saved store after at least 300s. Checkpoint retained')
  if r.status_code in (401,403):raise RuntimeError('SOURCE BLOCKED: grocery public page denied; no login, alternate API or challenge bypass attempted')
  r.raise_for_status()
  actual=urlsplit(r.url)
  if actual.hostname!=p.hostname or actual.path.rstrip('/')!=p.path.rstrip('/') or any(dict(parse_qsl(actual.query)).get(k)!=v for k,v in parse_qsl(p.query) if k in ('q','manufacturer','p')) or len(r.content)>8*1024*1024:raise ValueError('Unverified grocery response or scope-changing redirect')
  if re.search(r'cf-chl-|<title>\s*(?:Just a moment|Attention Required)',r.text,re.I):raise RuntimeError('SOURCE BLOCKED: source challenge; original requests retained')
  return r.text
 def discover_scope(self,scope):
  self.scope_count_changed=False;self.scope_totals=[]
  queue=[scope['url']];seen=set();discovered=set();expected=None
  seed=urlsplit(scope['url']);seed_query=dict(parse_qsl(seed.query))
  while queue:
   url=queue.pop(0)
   if url in seen:raise ValueError('Grocery pagination loop; scope incomplete')
   if len(seen)>=1000:raise ValueError('Grocery scope page bound exceeded')
   seen.add(url);soup=BeautifulSoup(self.read_page(url),'html.parser')
   selector='#product_result a[href], .products-grid .product-item a.product-item-link[href], .products.list.items .product-item a.product-item-link[href]'
   nodes=soup.select(selector)
   if self.force_fresh or soup.select_one('#load-more') or not nodes and soup.select_one('#product_result,.search-result-page'):
    cache=getattr(self.g.get('_chotu_tls'),'saved_response_cache',None);cache_key=url+'#chotu-rendered-listing-v2'
    saved=cache.get(cache_key) if cache and not self.force_fresh else None
    if saved is None:
     from grocery_browser_support import render_listing
     rendered=render_listing(url,self.g['_chotu_wait'],self.log)
     if cache:
      import requests
      saved=requests.Response();saved.status_code=200;saved.url=url;saved._content=rendered.encode();saved.encoding='utf-8';saved.headers['Content-Type']='text/html';cache.put(cache_key,saved)
    else:rendered=saved.text
    soup=BeautifulSoup(rendered,'html.parser');nodes=soup.select(selector)
   if not nodes and not re.search(r"We can.t find products|No products found|Your search returned no results",soup.get_text(' ',strip=True),re.I):raise ValueError('Public grocery listing schema unverified; no empty completion')
   for a in nodes:
    item=urljoin(url,a['href']);parsed=urlsplit(item)
    if parsed.hostname!=seed.hostname or parsed.scheme!='https':
     if 'product-item-link' in (a.get('class') or []):raise ValueError('Foreign product source URL')
     continue
    # Public result cards also contain wishlist/cart actions and fragment links.
    if parsed.query or parsed.fragment or parsed.path.strip('/').count('/') or parsed.path.rstrip('/') in ('','/allproducts','/customer','/checkout','/wishlist','/cart'):continue
    discovered.add(item)
   count=soup.select_one('.toolbar-amount')
   if count:
    total=listing_total(count.get_text(' ',strip=True))
    if total is not None:
     if expected is not None and expected!=total:self.scope_count_changed=True
     if total not in self.scope_totals:self.scope_totals.append(total)
     expected=total
   candidates=[]
   for a in soup.select('.pages a[href],a.next[href]'):
    item=urljoin(url,a['href']);part=urlsplit(item);query=dict(parse_qsl(part.query))
    if part.hostname!=seed.hostname or part.path.rstrip('/')!=seed.path.rstrip('/') or {k:v for k,v in query.items() if k!='p'}!=seed_query:continue
    if item not in seen and item not in queue and item not in candidates:candidates.append(item)
   queue.extend(candidates)
  return discovered,expected,seen

 def catalog(self):
  urls={};coverage=[];self.coverage_issues=[]
  for index,scope in enumerate(self.request['pages'],1):
   discovered,expected,seen=self.discover_scope(scope)
   if self.scope_count_changed or expected is not None and len(discovered)!=expected:
    self.log('GROCERY RECHECK: '+scope['url']+'; source total '+str(expected)+'; '+str(len(discovered))+' visible links; rechecking fresh public UI and all linked pages')
    self.force_fresh=True
    try:discovered,expected,seen=self.discover_scope(scope)
    finally:self.force_fresh=False
   status='complete'
   if self.scope_count_changed or expected is not None and len(discovered)!=expected:
    status='review_required';issue=dict(scope_url=scope['url'],reported_total=expected,visible_products=len(discovered),pages=len(seen),reported_totals=list(self.scope_totals))
    self.coverage_issues.append(issue);self.log('GROCERY COVERAGE REVIEW: '+json.dumps(issue)+'; source discrepancy retained; no complete-catalog approval')
   for item in discovered:
    if scope not in urls.setdefault(item,[]):urls[item].append(scope)
   coverage.append(dict(scope_url=scope['url'],pages=len(seen),products=len(discovered),reported_total=expected if expected is not None else '',coverage_status=status))
   self.log('GROCERY SCOPE: '+str(index)+'/'+str(len(self.request['pages']))+' traversed; '+str(len(urls))+' distinct product URLs; '+status)
  self.coverage_status='review_required' if self.coverage_issues else 'complete'
  import csv
  coverage_dir=Path(self.g.get('__file__',__file__)).resolve().parent/'audit_reports'/STORE;coverage_dir.mkdir(parents=True,exist_ok=True)
  with (coverage_dir/(STORE+' - SCOPE COVERAGE.csv')).open('w',encoding='utf-8-sig',newline='') as stream:
   writer=csv.DictWriter(stream,fieldnames=['scope_url','pages','products','reported_total','coverage_status']);writer.writeheader();writer.writerows(coverage)
  from locked_store_rules import incomplete_product_reasons,record_incomplete_product
  for index,url in enumerate(urls,1):
   page=self.read_page(url)
   try:
    p=product(page,url)
    scopes=urls[url];generic={'milk','nestle','cat food','dog food'}
    def key(value):
     import unicodedata
     return re.sub('[^a-z0-9]+',' ',unicodedata.normalize('NFKD',value).encode('ascii','ignore').decode().lower()).strip()
    exact=[v for v in scopes if key(v['label'])==key(p['manufacturer'])]
    specific=[v for v in scopes if key(v['label']) not in generic and key(v['label']) in key(p['name'])]
    candidates=exact or specific or scopes;groups={v['group'] for v in candidates}
    if len(groups)!=1:raise IncompleteProduct('Owner category scope conflicts across supplied pages; original source retained')
    p['owner_category']=next(iter(groups))
    if not scope_supported(p['owner_category'],p):raise IncompleteProduct('Search hit is outside the owner category purpose; source facts retained')
    p['owner_scope_url']=next(v['url'] for v in candidates if v['group']==p['owner_category'])
    reasons=incomplete_product_reasons(p)
    if not p['images']:reasons.append('No real source product image')
    if reasons:raise IncompleteProduct('; '.join(reasons))
   except IncompleteProduct as exc:
    raw=dict(title=norm(BeautifulSoup(page,'html.parser').h1.get_text()) if BeautifulSoup(page,'html.parser').h1 else '',_source_url=url,source_response_sha256=hashlib.sha256(page.encode()).hexdigest(),original_product_html=str(BeautifulSoup(page,'html.parser').select_one('main') or '')[:200000])
    record_incomplete_product(raw,BASE,STORE,self.g.get('__file__',__file__),[str(exc)]);self.log('GROCERY INCOMPLETE: '+url+'; '+str(exc));continue
   if not p['is_in_stock']:continue
   if p['id'] in self.products:raise ValueError('Repeated grocery source product ID')
   self.products[p['id']]=p
   self.log('GROCERY PRODUCTS: '+str(index)+'/'+str(len(urls))+' checked; '+str(len(self.products))+' complete available products')
  if not self.products:raise ValueError('No complete sellable grocery products; incomplete receipts retained')
  return list(self.products.values())
 def read(self,path):
  match=re.fullmatch(r'/wp-json/wc/store/v1/products/(\d+)',path)
  if not match or int(match[1]) not in self.products:raise ValueError('Unknown grocery product identity')
  return self.products[int(match[1])]

def enable_chotu_groceries(g):
 original=g['_chotuapp_run_site_original']
 def run(base,name,template,log):
  if (urlsplit(base).hostname or '').removeprefix('www.')!='naheed.pk':return original(base,name,template,log)
  if name!=STORE:raise ValueError('Grocery source requires owner-selected shop identity')
  from woocommerce_source_support import export
  provider=PublicCatalog(g,log);export(g,BASE,STORE,template,log,provider=provider)
  # Owner headings are the public Category; actual breadcrumbs remain evidence.
  from openpyxl import load_workbook
  from datetime import datetime,timezone
  path=g['OUT']/(STORE+' - REFRESH REVIEW.xlsx');book=load_workbook(path);sheet=book['Products'];headers={c.value:c.column for c in sheet[1]}
  fields=['source_scope_coverage_status','source_scope_review_count','owner_scope_url','source_manufacturer','Category','website_category_path','website_category_source_url','website_category_status','website_category_checked_at','subcategory_source','subcategory_evidence']
  for key in fields:
   if key not in headers:headers[key]=sheet.max_column+1;sheet.cell(1,headers[key],key)
  byid={g['uid']('CP',BASE+'|'+str(p['id'])):p for p in provider.products.values()};stamp=datetime.now(timezone.utc).isoformat()
  for number in range(2,sheet.max_row+1):
   p=byid.get(str(sheet.cell(number,headers['product_id']).value))
   if p is None:raise ValueError('Grocery source/export identity mismatch')
   taxonomy=' > '.join(c['name'] for c in p['categories']);values=dict(source_scope_coverage_status=provider.coverage_status,source_scope_review_count=len(provider.coverage_issues),owner_scope_url=p['owner_scope_url'],source_manufacturer=p['manufacturer'],Category=p['owner_category'],website_category_path=taxonomy,website_category_source_url=p['permalink'],website_category_status='verified_product_breadcrumb',website_category_checked_at=stamp,subcategory_source='owner_supplied_scope',subcategory_evidence='Owner category from '+p['owner_scope_url']+'; actual source breadcrumb '+taxonomy+'; response SHA256 '+p['source_response_sha256'])
   for key,value in values.items():sheet.cell(number,headers[key],value)
  book.save(path);book.close()
 g['_chotuapp_run_site_original']=run
