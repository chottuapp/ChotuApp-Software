"""Read product objects explicitly embedded in the public Axis Next.js page; never eval JS."""
import json,re
from bs4 import BeautifulSoup

def public_products(value):
 # Restrict extraction to product-shaped objects; unrelated session/config
 # JSON is never retained. Escaping prevents data from creating HTML tags.
 text=json.dumps({'product':value},ensure_ascii=True).replace('</','<\\/')
 return page_products('<script id="__NEXT_DATA__">'+text+'</script>')

def flight_values(html):
 soup=BeautifulSoup(html,'html.parser');payloads=[];decoder=json.JSONDecoder()
 for script in soup.find_all('script'):
  text=script.string or script.get_text()
  if script.get('id')=='__NEXT_DATA__':payloads.append(text)
  for match in re.finditer(r'self\.__next_f\.push\(',text):
   try:value,_=decoder.raw_decode(text[match.end():])
   except ValueError:continue
   if isinstance(value,list) and len(value)>1 and isinstance(value[1],str):payloads.append(value[1])
 joined=''.join(payloads);values=[]
 for payload in payloads:
  try:values.append(json.loads(payload))
  except ValueError:pass
 for match in re.finditer(r'(?m)^[0-9a-f]+:',joined):
  try:value,_=decoder.raw_decode(joined[match.end():]);values.append(value)
  except ValueError:continue
 return joined,values

def public_render_props(html):
 _,values=flight_values(html);found=[]
 def scrub(value):
  if isinstance(value,dict):return {k:scrub(v) for k,v in value.items() if not re.search(r'token|secret|password|authorization|api.?key|email|phone|session|cookie|customer|address',k,re.I)}
  if isinstance(value,list):return [scrub(v) for v in value]
  return value
 def walk(value):
  if isinstance(value,list):
   for v in value:walk(v)
  elif isinstance(value,dict):
   fields={k:v for k,v in value.items() if re.search(r'product|variant|size|colou?r|price|stock|inventory|currency|sku|slug',k,re.I) and not re.search(r'token|secret|password|authorization|api.?key|email|phone|session|cookie|customer|address',k,re.I)}
   fields=scrub(fields)
   if fields and len(json.dumps(fields))<40000 and fields not in found:found.append(fields)
   for v in value.values():
    if isinstance(v,(dict,list)):walk(v)
 for value in values:walk(value)
 return found[:12]

def page_products(html):
 joined,values=flight_values(html);decoder=json.JSONDecoder();found=[]
 def clean(value):
  if isinstance(value,dict):return {k:clean(v) for k,v in value.items() if not re.search(r'token|secret|password|authorization|api.?key|email|phone|session|cookie|customer|address',k,re.I)}
  if isinstance(value,list):return [clean(v) for v in value]
  return value
 def collect(value):
  if isinstance(value,list):
   for item in value:collect(item)
  elif isinstance(value,dict):
   if any(k in value for k in ('name','title','productName','product_name')) and any(k in value for k in ('id','_id','productId','product_id','slug','handle')) and any('price' in k.lower() for k in value):
    value=clean(value)
    if value not in found:found.append(value)
   else:
    for item in value.values():
     if isinstance(item,(dict,list)):collect(item)
 for match in re.finditer(r'"(?:initialProduct|product|initialProducts|products)"\s*:\s*',joined):
  try:value,_=decoder.raw_decode(joined[match.end():]);collect(value)
  except ValueError:continue
 for value in values:collect(value)
 return found

BASE='https://www.axispk.shop'
class SourcePriceConflict(ValueError):pass

def access_challenge(html):
 soup=BeautifulSoup(html,'html.parser');title=soup.title.get_text(' ',strip=True) if soup.title else ''
 return bool(re.search(r'just a moment|attention required|captcha verification',title,re.I) or re.search(r'verify (?:that )?you are human',soup.get_text(' ',strip=True),re.I) or soup.select_one('#challenge-form, #challenge-running'))

def normalize_product(html,url):
 from decimal import Decimal,InvalidOperation
 from urllib.parse import urlsplit,urljoin,parse_qs
 soup=BeautifulSoup(html,'html.parser');path=urlsplit(url).path.rstrip('/');slug=path.split('/')[-1]
 if urlsplit(url).hostname not in ('www.axispk.shop','axispk.shop') or not path.startswith('/product/'):raise ValueError('Axis product source identity invalid')
 products=[p for p in page_products(html) if p.get('slug')==slug]
 if len(products)!=1:raise ValueError('Exact Axis product state missing or ambiguous')
 p=products[0];ident=p.get('productId',p.get('id'));main=soup.select_one('main');title=main.find('h1') if main else None
 if isinstance(ident,bool) or not isinstance(ident,int) or ident<=0 or not title or title.get_text(' ',strip=True)!=p.get('name'):raise ValueError('Axis visible title and product identity disagree')
 if not any(x.get('currencyCode')=='PKR' for x in public_render_props(html)):raise ValueError('Axis PKR currency not verified')
 visible=main.get_text('\n',strip=True);head=re.split(r'(?m)^(?:COLOR|SIZE)$',visible,maxsplit=1)[0]
 amounts=re.findall(r'(?:Rs\.?|PKR)\s*([\d,]+(?:\.\d+)?)',head)
 if not amounts or len(amounts)>2:raise ValueError('Axis displayed product prices ambiguous')
 def amount(value):
  try:v=Decimal(str(value).replace(',',''))
  except InvalidOperation as exc:raise ValueError('Axis price invalid') from exc
  if not v.is_finite() or v<=0 or v*100!=(v*100).to_integral_value():raise ValueError('Axis price invalid')
  return v
 displayed=amount(amounts[0]);regular=amount(amounts[1]) if len(amounts)==2 else displayed
 if regular<displayed or amount(p.get('basePrice'))!=displayed:raise SourcePriceConflict('Axis displayed and product base prices disagree; no prices exported')
 raw=p.get('variants')
 if not isinstance(raw,list) or not raw:raise ValueError('Axis exact source variants missing')
 photos=[]
 def image(value):
  if not isinstance(value,str):return
  value=urljoin(BASE,value);parts=urlsplit(value)
  if parts.path=='/_next/image':value=parse_qs(parts.query).get('url',[''])[0];parts=urlsplit(value)
  if parts.scheme=='https' and parts.hostname and not parts.username and not parts.password and value not in photos:photos.append(value)
 image(p.get('image'))
 for tag in main.select('button[class*="aspect-square"] img[src]'):image(tag.get('src'))
 body=head.split('\n',1)[-1]
 body=re.sub(r'(?:Rs\.?|PKR)\s*[\d,]+(?:\.\d+)?|^-\d+%\s*$', '',body,flags=re.M).strip()
 base=dict(id=ident,name=p['name'],permalink=BASE+path,description=body,short_description='',images=[{'src':u} for u in photos],categories=[],condition='',sku='',type='variable')
 def prices(price):return dict(currency_code='PKR',currency_minor_unit=2,price=str(int(price*100)),regular_price=str(int(regular*100)),sale_price=str(int(price*100)) if price<regular else '')
 children=[];seen=set();dimensions={}
 for v in raw:
  vid=v.get('id');stock=v.get('stock');active=v.get('is_active');price=amount(v.get('price'))
  if isinstance(vid,bool) or not isinstance(vid,int) or vid<=0 or vid==ident or vid in seen or v.get('product_id')!=ident:raise ValueError('Axis variant identity invalid')
  if not isinstance(active,bool) or isinstance(stock,bool) or not isinstance(stock,int) or stock<0:raise ValueError('Axis variant availability not explicit')
  # This source currently renders one fixed price even after size selection.
  # Conflicting embedded variant prices are held, never silently substituted.
  if active and price!=displayed:raise SourcePriceConflict('Axis price conflict for variant '+str(vid)+': page PKR '+str(displayed)+', variant PKR '+str(price)+'; source correction required, no price guessed')
  attrs=[]
  for label,key in [('Color','color_name'),('Size','size_name')]:
   value=v.get(key)
   if not isinstance(value,str) or not value.strip():raise ValueError('Axis variant '+label+' missing')
   attrs.append(dict(name=label,value=value));dimensions.setdefault(label,[])
   if value not in dimensions[label]:dimensions[label].append(value)
  seen.add(vid);children.append(dict(base,id=vid,parent=ident,type='variation',sku=v.get('sku') or '',prices=prices(price),is_in_stock=active and stock>0,is_purchasable=active,stock_quantity=stock,attributes=attrs))
 base.update(prices=prices(displayed),is_in_stock=any(c['is_in_stock'] for c in children),is_purchasable=any(c['is_purchasable'] for c in children),attributes=[dict(name=k,has_variations=True,terms=[dict(name=v,slug=v) for v in vals]) for k,vals in dimensions.items()],variations=[dict(id=c['id'],attributes=c['attributes']) for c in children])
 return base,children

class PublicCatalog:
 label='Axis public Next.js product pages'
 def __init__(self,g,base,log):self.g=g;self.base=base.rstrip('/');self.log=log;self.byid={};self.children={};self.policy=None;self.rendered_catalog_links=[]
 def supports(self,base):return base.rstrip('/')==BASE and self.base==BASE
 def page(self,url):
  from urllib.parse import urlsplit
  parsed=urlsplit(url)
  if parsed.scheme!='https' or parsed.username or parsed.password or parsed.hostname!='www.axispk.shop':raise ValueError('Axis cross-source URL rejected')
  if self.policy and not self.policy.can_fetch('ChotuAppCatalogRefresh',url):raise ValueError('Axis robots disallows page; source retained')
  self.g['_chotu_wait']();reader=getattr(self.g['S'],'get_fresh',self.g['S'].get);response=reader(url,timeout=(15,45));response.raise_for_status()
  if urlsplit(response.url).hostname!='www.axispk.shop' or urlsplit(response.url).path.rstrip('/')!=urlsplit(url).path.rstrip('/'):raise ValueError('Axis page redirected to another identity')
  if access_challenge(response.text):raise ValueError('Axis public source access challenge; no renderer fallback attempted')
  return response.text
 def render(self,url,catalog=False):
  # Used only for a successfully readable JS shell, never after an HTTP denial.
  from playwright.sync_api import sync_playwright
  from urllib.parse import urlsplit
  self.g['_chotu_wait']()
  with sync_playwright() as driver:
   browser=driver.chromium.launch(channel='chrome',headless=True)
   try:
    context=browser.new_context(user_agent=self.g.get('HEADERS',{}).get('User-Agent','Mozilla/5.0 (compatible; ChotuAppCatalogRefresh/1.0)'));page=context.new_page()
    response=page.goto(url,wait_until='domcontentloaded',timeout=45000)
    if not response or response.status!=200:raise ValueError('Axis rendered page not permitted/readable; stopped without retry')
    if urlsplit(page.url).hostname!='www.axispk.shop' or urlsplit(page.url).path.rstrip('/')!=urlsplit(url).path.rstrip('/'):raise ValueError('Axis browser source identity changed')
    if access_challenge(page.content()):raise ValueError('Axis browser access challenge; stopped without interaction')
    page.wait_for_selector('main a[href*="/product/"]' if catalog else 'main h1',timeout=20000)
    if catalog:
     found=[];stagnant=0;denials=[]
     page.on('response',lambda reply:denials.append(reply.status) if reply.status in (401,403,429,503) and reply.request.resource_type in ('document','xhr','fetch') and urlsplit(reply.url).hostname=='www.axispk.shop' else None)
     for _ in range(300):
      self.g['_chotu_wait']()
      if denials or access_challenge(page.content()):raise ValueError('Axis catalog source denied/rate limited; stopped without retry')
      before=len(found)
      for link in page.eval_on_selector_all('main a[href]', '(nodes)=>nodes.map(n=>n.href)'):
       parsed=urlsplit(link)
       if parsed.scheme=='https' and parsed.hostname=='www.axispk.shop' and parsed.path.startswith('/product/') and not parsed.query and not parsed.fragment and link not in found:found.append(link)
      stagnant=stagnant+1 if len(found)==before else 0
      if stagnant>=8:break
      page.evaluate('window.scrollTo(0,document.body.scrollHeight)');page.wait_for_timeout(1200)
     else:raise ValueError('Axis public catalog scroll bound reached; no partial export')
     self.rendered_catalog_links=found
    return page.content()
   finally:browser.close()
 def product_page(self,url):
  html=self.page(url)
  if not BeautifulSoup(html,'html.parser').select_one('main h1'):html=self.render(url)
  return html
 def catalog(self):
  from urllib.robotparser import RobotFileParser
  from urllib.parse import urljoin,urlsplit,parse_qs
  raw=self.page(BASE+'/robots.txt');self.policy=RobotFileParser();self.policy.parse(raw.splitlines())
  queue=[BASE+'/shop'];visited=set();urls=[]
  while queue:
   url=queue.pop(0)
   if url in visited:continue
   if len(visited)>=100:raise ValueError('Axis public pagination bound reached')
   html=self.page(url);soup=BeautifulSoup(html,'html.parser');main=soup.select_one('main')
   embedded=page_products(html)
   if not main or not main.select('a[href*="/product/"]'):
    html=self.render(url,catalog=True);soup=BeautifulSoup(html,'html.parser');main=soup.select_one('main');embedded=page_products(html)
   if not main:raise ValueError('Axis shop content missing')
   visited.add(url)
   for link in self.rendered_catalog_links:
    if link not in urls:urls.append(link)
   for item in embedded:
    slug=item.get('slug')
    if not isinstance(slug,str):continue
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,200}',slug):raise ValueError('Axis catalog slug format needs source review')
    link=BASE+'/product/'+slug
    if link not in urls:urls.append(link)
   for a in main.select('a[href]'):
    link=urljoin(BASE,a['href']);p=urlsplit(link)
    if p.hostname!='www.axispk.shop' or p.fragment:continue
    if p.path.startswith('/product/') and not p.query and link not in urls:urls.append(link)
    if p.path=='/shop' and p.query and set(parse_qs(p.query))=={'page'} and all(v.isdigit() for v in parse_qs(p.query)['page']) and link not in visited|set(queue):queue.append(link)
   if any(re.fullmatch(r'(?:load|show) more|next(?: page)?|[›→]',b.get_text(' ',strip=True) or b.get('aria-label','') or b.get('title',''),re.I) and not b.has_attr('disabled') for b in main.find_all('button')):raise ValueError('Axis catalog has an unverified interactive pagination control; no partial catalog exported')
  if not urls:raise ValueError('Axis public shop product links missing')
  result=[]
  for i,url in enumerate(urls,1):
   parent,children=normalize_product(self.product_page(url),url)
   if parent['id'] in self.byid:raise ValueError('Axis duplicate source identity')
   self.byid[parent['id']]=parent;self.children.update({c['id']:c for c in children});result.append(parent)
   self.log('AXIS: verified '+str(i)+'/'+str(len(urls))+' exact public products')
  return result
 def read(self,path):
  key=int(path.rstrip('/').split('/')[-1])
  if key in self.children:return self.children[key]
  item=self.byid[key];parent,children=normalize_product(self.product_page(item['permalink']),item['permalink'])
  if parent['id']!=key:raise ValueError('Axis fresh product identity changed')
  self.children.update({c['id']:c for c in children});return parent

def enable_axis_source(g):
 original=g['_chotuapp_run_site_original']
 def run(base,name,template,log):
  if base.rstrip('/')!=BASE:return original(base,name,template,log)
  from woocommerce_source_support import export
  return export(g,base,name,template,log,provider=PublicCatalog(g,base,log))
 g['_chotuapp_run_site_original']=run
