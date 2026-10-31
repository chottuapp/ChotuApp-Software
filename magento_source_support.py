"""Paklap's public Magento GraphQL catalog; exact offers, no guessed options/stock."""
import json,re,requests
from decimal import Decimal
from urllib.parse import urlsplit,urlencode,urljoin
from urllib.robotparser import RobotFileParser
from bs4 import BeautifulSoup
BASE='https://www.paklap.pk'
PRICE='price_range{minimum_price{regular_price{value currency}final_price{value currency}}}'
BASIC='__typename id sku name url_key stock_status '+PRICE
DETAIL=BASIC+' url_suffix description{html} short_description{html} image{url label} media_gallery{url label disabled} categories{id name url_path} ... on CustomizableProductInterface{options{__typename option_id title required ... on CustomizableDropDownOption{value{option_type_id title price price_type}} ... on CustomizableRadioOption{value{option_type_id title price price_type}} ... on CustomizableMultipleOption{value{option_type_id title price price_type}} ... on CustomizableCheckboxOption{value{option_type_id title price price_type}}}} ... on ConfigurableProduct{configurable_options{attribute_code label values{value_index label}} variants{attributes{code label value_index} product{'+BASIC+' image{url label}}}}'

def prices(raw):
 p=raw['price_range']['minimum_price'];regular=p['regular_price'];final=p['final_price']
 if regular['currency']!='PKR' or final['currency']!='PKR':raise ValueError('Non-PKR Magento offer')
 values=[Decimal(str(x['value'])) for x in (regular,final)]
 if any(not v.is_finite() or v<=0 or v*10000!=(v*10000).to_integral_value() for v in values) or values[1]>values[0]:raise ValueError('Invalid exact Magento prices')
 return dict(currency_code='PKR',currency_minor_unit=4,regular_price=str(int(values[0]*10000)),price=str(int(values[1]*10000)),sale_price=str(int(values[1]*10000)))

def custom_options(options):
 result=[];seen=set()
 kinds={'CustomizableDropDownOption':'single','CustomizableRadioOption':'single','CustomizableMultipleOption':'multi','CustomizableCheckboxOption':'multi'}
 for option in options or []:
  kind=kinds.get(option.get('__typename'));ident=option.get('option_id')
  if not kind or not isinstance(ident,int) or ident in seen or not option.get('title') or not isinstance(option.get('required'),bool):raise ValueError('Custom option requires explicit supported selectable identity')
  seen.add(ident);choices=[];values=set()
  for value in option.get('value') or []:
   vid=value.get('option_type_id');fee=Decimal(str(value.get('price')))
   if not isinstance(vid,int) or vid in values or not value.get('title') or value.get('price_type')!='FIXED' or not fee.is_finite() or fee<0 or fee*10000!=(fee*10000).to_integral_value():raise ValueError('Custom option price/identity is not an exact fixed PKR amount')
   values.add(vid);choices.append(dict(id=vid,title=value['title'],extra_price=fee))
  if not 1<=len(choices)<=500:raise ValueError('Custom option choices missing or excessive')
  result.append(dict(id=ident,title=option['title'],select_type=kind,required=option['required'],choices=choices))
 return result

def normalize(raw,base=BASE,*,parent=None,permalink=None):
 kind=raw.get('__typename');identity=raw.get('id');stock=raw.get('stock_status')
 if not isinstance(identity,int) or not raw.get('sku') or not raw.get('name'):raise ValueError('Magento product identity missing')
 if stock not in ('IN_STOCK','OUT_OF_STOCK'):raise ValueError('Magento availability unknown')
 if kind not in ('SimpleProduct','ConfigurableProduct','VirtualProduct'):raise ValueError('Unsupported Magento type: '+str(kind))
 custom=custom_options(raw.get('options'))
 if permalink is None:
  key=raw.get('url_key');suffix=raw.get('url_suffix')
  if not isinstance(suffix,str) or not isinstance(key,str) or not key or any(x in key+suffix for x in ('..','?','#',':','/')):raise ValueError('Magento source URL is not explicit')
  permalink=base+'/'+key+suffix
 photos=[]
 for image in [raw.get('image')]+[i for i in raw.get('media_gallery',[]) if not i.get('disabled')]:
  url=(image or {}).get('url','')
  if url.startswith('https://') and url not in [i['src'] for i in photos]:photos.append(dict(src=url))
 result=dict(id=identity,sku=raw['sku'],name=raw['name'],type='variation' if parent else 'variable' if kind=='ConfigurableProduct' else 'simple',parent=parent,permalink=permalink,is_in_stock=stock=='IN_STOCK',is_purchasable=stock=='IN_STOCK',is_on_backorder=False,prices=prices(raw),images=photos,description=(raw.get('description') or {}).get('html',''),short_description=(raw.get('short_description') or {}).get('html',''),categories=[dict(name=c['name']) for c in raw.get('categories',[]) if c.get('name')],condition='used' if re.search(r'\bused\b',raw['name'],re.I) else '')
 result['custom_options']=custom
 result['virtual']=kind=='VirtualProduct'
 result['magento_product_type']=kind
 if kind=='ConfigurableProduct':
  options=raw.get('configurable_options') or []
  if not options or not 1<=len(options)<=3:raise ValueError('Unsupported configurable dimensions')
  dimensions={o['attribute_code']:o for o in options}
  result['attributes']=[dict(name=o['label'],has_variations=True,terms=[dict(name=v['label']) for v in o['values']]) for o in options];result['variations']=[]
  for v in raw.get('variants') or []:
   attrs=v.get('attributes') or []
   if {a['code'] for a in attrs}!=set(dimensions):raise ValueError('Incomplete Magento option selection')
   selection=[]
   for a in attrs:
    option=dimensions[a['code']];value=next((x for x in option['values'] if x['value_index']==a['value_index']),None)
    if value is None or value['label']!=a['label']:raise ValueError('Magento variant label identity mismatch')
    selection.append(dict(name=option['label'],value=value['label']))
   result['variations'].append(dict(id=v['product']['id'],attributes=selection))
  if not result['variations']:raise ValueError('No actual configurable variants')
 return result

class PublicCatalog:
 label='Magento GraphQL'
 def __init__(self,g,base,log):self.g=g;self.base=base.rstrip('/');self.log=log;self.byid={};self.children={};self.robot=None
 def supports(self,base):return base.rstrip('/')==BASE and self.base==BASE
 def query(self,body):
  url=self.base+'/graphql?'+urlencode({'query':body})
  if self.robot is None:
   r=self.g['S'].get(self.base+'/robots.txt',timeout=(15,30));r.raise_for_status()
   if urlsplit(r.url).hostname.removeprefix('www.')!='paklap.pk':raise ValueError('Magento robots changed source host')
   self.robot=RobotFileParser();self.robot.parse(r.text.splitlines())
  if not self.robot.can_fetch('ChotuAppCatalog',url):raise ValueError('Public robots rule disallows Magento source')
  self.g['_chotu_wait']();data=self.g['get_json'](url)
  if data.get('errors') or not isinstance(data.get('data'),dict):raise ValueError('Magento GraphQL returned incomplete/error data')
  return data['data']['products']
 def catalog(self):
  products=[];seen=set();expected=None
  for page in range(1,1001):
   data=self.query('{products(search:"",pageSize:50,currentPage:'+str(page)+'){total_count items{'+BASIC+'}}}')
   if not isinstance(data.get('total_count'),int) or not isinstance(data.get('items'),list):raise ValueError('Invalid public catalog pagination')
   if expected is None:expected=data['total_count']
   if expected!=data['total_count']:raise ValueError('Magento catalog changed during pagination; retry from saved work')
   for item in data['items']:
    if item['id'] in seen:raise ValueError('Duplicate Magento catalog ID')
    seen.add(item['id']);item['permalink']='pending-source-detail';self.byid[item['id']]=item;products.append(item)
   self.log('MAGENTO CATALOG: '+str(len(products))+'/'+str(expected))
   if len(products)==expected:break
   if not data['items'] or len(products)>expected:raise ValueError('Incomplete Magento catalog')
  if not products or len(products)!=expected:raise ValueError('Magento pagination bound or empty catalog')
  return products
 def read(self,path):
  match=re.fullmatch(r'/wp-json/wc/store/v1/products/(\d+)',path)
  if not match:raise ValueError('Unknown normalized product lookup')
  ident=int(match[1])
  if ident in self.children:return self.children[ident]
  item=self.byid[ident];query='{products(filter:{sku:{eq:'+json.dumps(item['sku'])+'}},pageSize:2){items{'+DETAIL+'}}}'
  data=self.query(query);items=data.get('items',[])
  # Some public SKU indexes omit a catalogued product. Its exact published URL
  # key offers another lookup, never permission to accept another ID or SKU.
  if items==[] and isinstance(item.get('url_key'),str) and item['url_key']:
   data=self.query('{products(filter:{url_key:{eq:'+json.dumps(item['url_key'])+'}},pageSize:2){items{'+DETAIL+'}}}')
   items=data.get('items',[])
  if len(items)!=1 or items[0].get('id')!=ident or items[0].get('sku')!=item['sku'] or items[0].get('url_key')!=item.get('url_key'):raise ValueError('Exact Magento SKU/product identity mismatch: id='+str(ident)+' sku='+str(item['sku']))
  raw=items[0];product=normalize(raw,self.base)
  if self.robot.can_fetch('ChotuAppCatalog',product['permalink']):
   self.g['_chotu_wait']()
   try:
    response=self.g['S'].get(product['permalink'],timeout=(15,40))
    soup=BeautifulSoup(response.text,'html.parser');canonical=soup.select_one('link[rel=canonical][href]');title=soup.select_one('h1')
    norm=lambda value:re.sub(r'\s+',' ',str(value)).strip().casefold()
    matched=(getattr(response,'status_code',None)==200 and response.url.rstrip('/')==product['permalink'].rstrip('/') and canonical and urljoin(response.url,canonical['href']).rstrip('/')==product['permalink'].rstrip('/') and title and norm(title.get_text(' ',strip=True))==norm(product['name']))
    if matched:
     specs=[]
     for row in soup.select('#product-attribute-specs-table tr'):
      cells=row.select('th,td')
      if len(cells)==2:specs.append(cells[0].get_text(' ',strip=True)+': '+cells[1].get_text(' ',strip=True))
     if specs:product['description']+='\nSpecifications\n'+'\n'.join(specs)
    else:product['source_notes']='Product-specific page/specification identity not verified; retained exact public API facts only.'
   except requests.RequestException:
    product['source_notes']='Product-specific page unavailable; retained exact public API facts only.'
  else:product['source_notes']='Public robots policy disallows product-page supplementation; retained exact public API facts only.'
  for v in raw.get('variants') or []:
   child=normalize(v['product'],self.base,parent=ident,permalink=product['permalink']);self.children[child['id']]=child
  # Existing shared exporter checks list/detail permalink identity. Here the
  # listing lacks a suffix; bind it only to this exact freshly verified detail.
  item['permalink']=product['permalink']
  return product

def enable_magento_source(g):
 original=g['_chotuapp_run_site_original']
 def run(base,name,template,log):
  if base.rstrip('/')!=BASE:return original(base,name,template,log)
  from woocommerce_source_support import export
  catalog=PublicCatalog(g,base,log)
  # Shared workbook writer consumes a normalized catalog, not a synthetic HTTP API.
  return export(g,base,name,template,log,provider=catalog)
 g['_chotuapp_run_site_original']=run
