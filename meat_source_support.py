"""Read the exact public meat-store UI; observe each genuine weight/pack offer."""
import hashlib,json,re
from decimal import Decimal,InvalidOperation
from pathlib import Path
from urllib.parse import urlsplit,parse_qs,urljoin
import requests
from bs4 import BeautifulSoup
from retailer_branding_support import customer_fields,clean
BASE='https://barkatmeathouse.com';STORE='ChotuApp Meat House';CODE='SE10086'
PRODUCT=re.compile(r'^/product/[a-z0-9-]+-([a-f0-9]{24})\.html$')

def money(text):
 match=re.search(r'Rs\.\s*([\d,]+(?:\.\d{1,2})?)',str(text))
 if not match:raise ValueError('Visible PKR price missing')
 value=Decimal(match[1].replace(',',''))
 if not value.is_finite() or value<=0:raise ValueError('Nonpositive source PKR price')
 return value

def visible_offer(state):
 soup=BeautifulSoup(state['price_html'],'html.parser');old=soup.select_one('del')
 regular=money(old.get_text(' ',strip=True)) if old else None
 for node in soup.select('del'):node.decompose()
 price=money(soup.get_text(' ',strip=True));regular=regular or price
 if regular<price or state.get('enabled') and money(state['cart_text'])!=price or state.get('selected')!=state.get('label'):raise ValueError('Visible product/selected-option/cart price conflict')
 return dict(currency_code='PKR',currency_minor_unit=2,price=str(int(price*100)),regular_price=str(int(regular*100)),sale_price=str(int(price*100)) if price<regular else '')

def normalize_capture(capture):
 url=capture['url'];part=urlsplit(url);match=PRODUCT.fullmatch(part.path)
 if part.scheme!='https' or part.netloc!='barkatmeathouse.com' or not match or part.query or part.fragment:raise ValueError('Foreign or unverified meat product URL')
 ident=match[1];name=capture['name'].strip();states=capture['states']
 if not name or not states or len(states)>30 or len({s['label'] for s in states})!=len(states):raise ValueError('Source product/options missing or duplicated')
 first=capture.get('initial',states[0]);initial=visible_offer(first);available=first['enabled']
 if not isinstance(available,bool):raise ValueError('Source availability not verified')
 matching=[]
 for product in capture['schemas']:
  if product.get('@type')!='Product' or product.get('name')!=name or product.get('url')!=url or str(product.get('sku'))!=ident:continue
  offers=product.get('offers');offers=offers if isinstance(offers,list) else [offers]
  for offer in offers:
   if not isinstance(offer,dict) or offer.get('priceCurrency')!='PKR':continue
   try:value=Decimal(str(offer.get('price')))
   except InvalidOperation:continue
   stock=str(offer.get('availability','')).rsplit('/',1)[-1]
   if value==Decimal(initial['price'])/100 and stock==('InStock' if available else 'OutOfStock'):matching.append(product)
 if not matching:raise ValueError('Product schema does not corroborate the visible live identity/price/availability')
 images=[dict(src=u,alt=clean(name)) for u in capture['images'] if urlsplit(u).scheme=='https' and urlsplit(u).hostname in ('barkatmeathouse.com','api.barkatmeathouse.com')]
 if not images or not capture['category'].strip():raise ValueError('Actual source image/category missing')
 supplier_description=capture['description'];body=supplier_description+'\n\n'+capture['option_name']+' options: '+', '.join(s['label'] for s in states)+'.'
 fields=customer_fields(url,name,body);fields['original_source_description']=supplier_description
 p=dict(id=ident,name=fields['name'],title=fields['name'],sku=ident,permalink=url,_source_url=url,description=fields['description'],body_html=fields['description'],short_description='',type='variable',is_in_stock=available,is_purchasable=available,is_on_backorder=False,prices=initial,images=images,categories=[dict(id=capture['category'],name=capture['category'])],attributes=[dict(name=capture['option_name'],has_variations=True,terms=[dict(name=s['label']) for s in states])],variations=[],_observed_variants=[],_source_capture=capture,_source_branding=fields)
 for state in states:
  if not isinstance(state['enabled'],bool):raise ValueError('Option availability unverified')
  prices=visible_offer(state);vid='ui-'+hashlib.sha256((ident+'|'+state['label']).encode()).hexdigest()[:24]
  p['variations'].append(dict(id=vid,attributes=[dict(name=capture['option_name'],value=state['label'])]))
  p['_observed_variants'].append(dict(id=vid,parent=ident,type='variation',name=fields['name'],sku='',prices=prices,is_in_stock=state['enabled'],is_purchasable=state['enabled'],is_on_backorder=False,images=[],source_option_evidence=state['label']))
 return p

def schemas(page):
 result=[]
 def walk(value):
  if isinstance(value,dict):
   if value.get('@type')=='Product':result.append(value)
   for v in value.values():walk(v)
  elif isinstance(value,list):
   for v in value:walk(v)
 for node in page.locator('script[type="application/ld+json"]').all():
  try:walk(json.loads(node.inner_text()))
  except ValueError:continue
 return result

def open_page(page,url):
 if urlsplit(url).scheme!='https' or urlsplit(url).netloc!='barkatmeathouse.com':raise ValueError('Outside exact owner-requested meat source')
 response=page.goto(url,wait_until='domcontentloaded',timeout=60000)
 if not response or response.status in (401,403) or re.search(r'just a moment|attention required|captcha',page.title(),re.I):raise RuntimeError('SOURCE BLOCKED: public meat storefront unavailable; no bypass')
 if response.status>=400:raise RuntimeError('SOURCE PAUSED: meat storefront HTTP '+str(response.status)+'; saved work retained')
 actual=urlsplit(page.url)
 if actual.netloc!='barkatmeathouse.com' or actual.scheme!='https' or actual.path.rstrip('/')!=urlsplit(url).path.rstrip('/'):raise ValueError('Unverified source redirect')
 page.wait_for_selector('main',timeout=30000)

def capture_product(page,url):
 open_page(page,url);page.wait_for_selector('main .detail-copy .weights button',timeout=30000);page.wait_for_timeout(700)
 detail=page.locator('main .detail-copy');name=detail.locator('h1').inner_text();category=detail.locator(':scope > .eyebrow').inner_text()
 description='\n\n'.join(detail.locator(':scope > p,.product-specifications p').all_text_contents())
 labels=detail.locator('.weights button').all_text_contents();option_label=detail.locator(':scope > label').first.inner_text()
 capture=dict(url=page.url,name=name,category=category,description=description,option_name='Weight' if 'WEIGHT' in option_label.upper() else 'Quantity' if 'QUANTITY' in option_label.upper() else '',images=page.locator('main .product-gallery img[src]').evaluate_all('(nodes)=>nodes.map(n=>n.src)'),schemas=schemas(page),states=[])
 if not capture['option_name']:raise ValueError('Unknown actual source option control')
 cart=detail.locator('.add-row button.button');active=detail.locator('.weights button.active')
 if cart.count()!=1 or active.count()!=1:raise ValueError('Initial source selected offer is ambiguous')
 label=active.inner_text();capture['initial']=dict(label=label,selected=label,price_html=detail.locator('.detail-price').inner_html(),cart_text=cart.inner_text(),enabled=not cart.is_disabled())
 capture['declared_options']=labels
 if not capture['initial']['enabled']:
  capture['states']=[capture['initial']];return capture
 for label in labels:
  node=detail.locator('.weights button').filter(has_text=re.compile('^'+re.escape(label)+'$'))
  if node.count()!=1 or node.is_disabled():raise ValueError('A declared source option cannot be selected; its price is not guessed')
  node.click();page.wait_for_timeout(200)
  cart=detail.locator('.add-row button.button');active=detail.locator('.weights button.active')
  if cart.count()!=1 or active.count()!=1:raise ValueError('Exact selected source offer control missing')
  capture['states'].append(dict(label=label,selected=active.inner_text(),price_html=detail.locator('.detail-price').inner_html(),cart_text=cart.inner_text(),enabled=not cart.is_disabled()))
 return capture

class PublicMeatCatalog:
 label='Public selected-weight meat storefront UI'
 def __init__(self,g,log):self.g=g;self.log=log;self.products={};self.items={}
 def supports(self,base):return base.rstrip('/')==BASE
 def read(self,path):
  ident=path.rsplit('/',1)[-1]
  if ident not in self.items:raise ValueError('Unknown observed public product/option identity')
  return self.items[ident]
 def catalog(self):
  from playwright.sync_api import sync_playwright
  cache=getattr(self.g.get('_chotu_tls'),'saved_response_cache',None);revision=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()[:16]
  with sync_playwright() as driver:
   browser=driver.chromium.launch(headless=True)
   try:
    page=browser.new_page();open_page(page,BASE);page.wait_for_timeout(1200)
    links=page.locator('a[href]').evaluate_all('(nodes)=>nodes.map(n=>n.href)')
    scopes=list(dict.fromkeys(u for u in links if urlsplit(u).netloc=='barkatmeathouse.com' and urlsplit(u).path=='/shop' and parse_qs(urlsplit(u).query).get('category')))
    if not scopes:raise ValueError('Public catalog category navigation missing')
    urls=set();coverage=[]
    for scope in scopes:
     self.g['_chotu_wait']();open_page(page,scope);page.wait_for_timeout(800)
     text=page.locator('main').inner_text();count=re.search(r'\b(\d+)\s+(?:Beef|Mutton|Veal(?:\s*\(Bachiya\))?)\s+products\b',text,re.I)
     found=set(page.locator('main .product-grid .product-card a[href]').evaluate_all('(nodes)=>nodes.map(n=>n.href)'))
     found={u for u in found if urlsplit(u).netloc=='barkatmeathouse.com' and PRODUCT.fullmatch(urlsplit(u).path)}
     if not count or len(found)!=int(count[1]):raise ValueError('Meat catalog category count incomplete; no partial completion')
     urls.update(found);coverage.append(dict(scope_url=scope,total=int(count[1]),links=sorted(found)))
    for index,url in enumerate(sorted(urls),1):
     self.g['_chotu_wait']();self.g.get('_chotu_debug_stage',lambda _:None)('Meat product weight offers');key=url+'#chotu-public-weight-ui-'+revision;saved=cache.get(key) if cache else None
     capture=saved.json() if saved is not None else capture_product(page,url)
     p=normalize_capture(capture)
     if p['id'] in self.products and self.products[p['id']]['permalink']!=p['permalink']:raise ValueError('Repeated source product identity across different canonical pages')
     if saved is None and cache:
      response=requests.Response();response.status_code=200;response.url=url;response._content=json.dumps(capture).encode();response.encoding='utf-8';cache.put(key,response)
     self.products[p['id']]=p;self.items[p['id']]=p
     for v in p['_observed_variants']:
      if v['id'] in self.items:raise ValueError('Duplicate observed option identity')
      self.items[v['id']]=v
     self.log('MEAT PRODUCTS: '+str(index)+'/'+str(len(urls))+' verified; '+str(len(p['_observed_variants']))+' observed options')
    folder=Path(self.g['__file__']).resolve().parent/'audit_reports'/STORE;folder.mkdir(parents=True,exist_ok=True)
    (folder/(STORE+' - SOURCE COVERAGE.json')).write_text(json.dumps(coverage,indent=2))
   finally:browser.close()
  return list(self.products.values())

def enable_meat_source(g):
 original=g['_chotuapp_run_site_original']
 def run(base,name,template,log):
  if (urlsplit(base).hostname or '').removeprefix('www.')!='barkatmeathouse.com':return original(base,name,template,log)
  if name!=STORE:raise ValueError('Exact owner-confirmed meat seller name required')
  from woocommerce_source_support import export
  provider=PublicMeatCatalog(g,log);export(g,BASE,STORE,template,log,provider=provider)
  from openpyxl import load_workbook
  from datetime import datetime,timezone
  path=g['OUT']/(STORE+' - REFRESH REVIEW.xlsx');book=load_workbook(path);sheet=book['Products'];headers={c.value:c.column for c in sheet[1]};byid={g['uid']('CP',BASE+'|'+str(p['id'])):p for p in provider.products.values()}
  for n in range(2,sheet.max_row+1):
   p=byid[sheet.cell(n,headers['product_id']).value];fields=p['_source_branding']
   metadata=dict(shop_code=CODE,name=fields['name'],description=fields['description'],brand=STORE,sku=p['sku'],Category=p['categories'][-1]['name'],website_category_path=p['categories'][-1]['name'],website_category_source_url=p['permalink'],website_category_status='verified_navigation_membership',website_category_checked_at=datetime.now(timezone.utc).isoformat(),subcategory_source='website',subcategory_evidence='Verified category navigation and matching source product category; exact weight/pack offer observed')
   metadata.update({k:v for k,v in fields.items() if k.startswith('original_') or k=='retailer_branding_rule'})
   for key,value in metadata.items():
    if key not in headers:headers[key]=sheet.max_column+1;sheet.cell(1,headers[key],key)
    sheet.cell(n,headers[key],value)
  variants=book['Variant Combinations'];vh={c.value:c.column for c in variants[1]}
  if 'source_variant_id' in vh:
   for n in range(2,variants.max_row+1):variants.cell(n,vh['source_variant_id'],'')
  book.save(path);book.close()
 g['_chotuapp_run_site_original']=run
