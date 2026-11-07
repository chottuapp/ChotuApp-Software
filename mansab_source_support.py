"""Mansab public product API with exact size stock and PKR page-offer binding."""
import html,hashlib,re
from decimal import Decimal,InvalidOperation
from urllib.parse import urlsplit,urlencode
from bs4 import BeautifulSoup
from public_catalog_support import PublicCatalog,enable_public_source
from czone_source_support import structured
BASE='https://mansabpk.com'
def amount(v):
 try:n=Decimal(str(v))
 except InvalidOperation as e:raise ValueError('Mansab price unreadable') from e
 if not n.is_finite() or n<=0:raise ValueError('Mansab positive price missing')
 return n

def normalize(page,url,raw):
 p=urlsplit(url);slug=p.path.rstrip('/').rsplit('/',1)[-1]
 if p.scheme!='https' or (p.hostname or '').removeprefix('www.')!='mansabpk.com' or not p.path.startswith('/product/') or not re.fullmatch(r'[a-z0-9-]{1,250}',slug):raise ValueError('Mansab public source identity invalid')
 if not isinstance(raw,dict) or raw.get('slug')!=slug or not raw.get('id') or not raw.get('name'):raise ValueError('Mansab API product identity mismatch')
 records=structured(BeautifulSoup(page,'html.parser'),'Product')
 if len(records)!=1:raise ValueError('Exact Mansab page offer missing')
 meta=records[0];offer=meta.get('offers',{})
 if meta.get('name','').strip()!=raw['name'].strip() or not isinstance(offer,dict) or offer.get('priceCurrency')!='PKR':raise ValueError('Mansab PKR product metadata mismatch')
 offer_url=urlsplit(offer.get('url',''))
 if (offer_url.hostname or '').removeprefix('www.')!='mansabpk.com' or offer_url.path.rstrip('/')!=p.path.rstrip('/'):raise ValueError('Mansab offer URL mismatch')
 regular=amount(raw.get('price'));sale=amount(raw['sale_price']) if raw.get('sale_price') is not None else regular
 if sale>regular or sale!=amount(offer.get('price')):raise ValueError('Mansab page/API selling price conflict')
 sizes=raw.get('sizes');stock=raw.get('size_stock');total=raw.get('stock')
 if not isinstance(sizes,list) or not sizes or any(not isinstance(s,str) or not s for s in sizes) or len(set(sizes))!=len(sizes) or not isinstance(stock,dict):raise ValueError('Mansab exact source sizes/stock missing')
 if any(s not in stock or not isinstance(stock[s],int) or isinstance(stock[s],bool) or stock[s]<0 for s in sizes):raise ValueError('Mansab size quantity unknown')
 if any(k not in sizes and q!=0 for k,q in stock.items()):raise ValueError('Mansab undeclared size stock conflict')
 if not isinstance(total,int) or isinstance(total,bool) or total!=sum(stock[s] for s in sizes):raise ValueError('Mansab total/size stock conflict')
 if offer.get('availability') not in ('https://schema.org/InStock','https://schema.org/OutOfStock') or (offer['availability'].endswith('/InStock'))!=(total>0):raise ValueError('Mansab page/API availability conflict')
 variants=[]
 for size in sizes:
  # API supplies product+size identity, not native variant IDs/SKUs. Keep those blank.
  logical=hashlib.sha256((str(raw['id'])+'\0'+size).encode()).hexdigest()[:24]
  variants.append(dict(id='mansab-'+logical,_source_variant_id='',sku='',price=str(sale),compare_at_price=str(regular) if sale<regular else None,available=stock[size]>0,inventory_quantity=stock[size],inventory_management='public',_public_stock_quantity=stock[size],option1=size))
 blocks=[str(raw.get('description') or '')]
 for key,label in (('fabric','Fabric & Fit'),('set_details','Pack Contents'),('measurements','Measurements')):
  value=raw.get(key)
  if value:
   if not isinstance(value,str):raise ValueError('Unsupported Mansab '+key+' schema')
   blocks.append('<h3>'+label+'</h3><p>'+html.escape(value)+'</p>')
 images=raw.get('images')
 if not isinstance(images,list) or not images or any(not isinstance(i,str) or not i.startswith('https://') for i in images):raise ValueError('Mansab source photos missing')
 return dict(id=raw['id'],handle=slug,title=raw['name'],body_html='\n'.join(blocks),vendor='MANSAB',product_type=raw.get('category') or '',options=[dict(name='Size')],variants=variants,images=[dict(src=i,position=n+1) for n,i in enumerate(images)],_source_url=BASE+'/product/'+slug)

class MansabCatalog(PublicCatalog):
 def __init__(self,g,log,base,normalizer,name):
  super().__init__(g,log,base,normalizer,name)
  self.normalize=lambda page,url:normalizer(page,url,self.read(BASE+'/api/products?'+urlencode({'slug':urlsplit(url).path.rstrip('/').rsplit('/',1)[-1]})).json())

def enable_mansab_source(g):
 enable_public_source(g,BASE,'Mansab',normalize,'_chotu_mansab_source',catalog_class=MansabCatalog)
