"""Rungrez public Nuxt/Octane PKR offers; no USD conversion or LAAM owner filter."""
from decimal import Decimal
from urllib.parse import urlsplit
from bs4 import BeautifulSoup
from czone_source_support import nuxt
from laam_source_support import normalize as normalize_octane
BASE='https://rungrez.com.pk'

def normalize(page,url):
 p=urlsplit(url)
 if p.scheme!='https' or (p.hostname or '').removeprefix('www.')!='rungrez.com.pk' or not p.path.startswith('/products/'):raise ValueError('Rungrez source identity unverified')
 handle=p.path.rstrip('/').rsplit('/',1)[-1];values,decode=nuxt(BeautifulSoup(page,'html.parser'));root=decode(0);found=[];seen=set()
 def walk(v):
  if isinstance(v,(dict,list)):
   if id(v) in seen:return
   seen.add(id(v))
  if isinstance(v,dict):
   if v.get('handle')==handle and isinstance(v.get('variants'),list) and v.get('description') and v.get('pricing_breakdown'):found.append(v)
   for item in v.values():walk(item)
  elif isinstance(v,list):
   for item in v:walk(item)
 walk(root)
 if len(found)!=1:raise ValueError('Exact Rungrez product state missing or ambiguous')
 raw=found[0];pricing=raw['pricing_breakdown']
 if str(pricing.get('currency','')).upper()!='PKR' or raw.get('not_sold_here') is not False:raise ValueError('Rungrez PKR market unverified')
 for v in raw['variants']:
  q=v.get('pricing_breakdown') or {}
  if str(q.get('currency','')).upper()!='PKR' or Decimal(str(q.get('price')))!=Decimal(str(v.get('price'))):raise ValueError('Rungrez variant PKR price conflict')
  if q.get('display_price') is not None and Decimal(str(q['display_price']))!=Decimal(str(v['price'])):raise ValueError('Rungrez displayed price conflict')
 selected=[v for v in raw['variants'] if (v.get('shopify_id') or v.get('id'))==pricing.get('display_variant_id')]
 if len(selected)!=1 or Decimal(str(selected[0]['price']))!=Decimal(str(pricing.get('price'))):raise ValueError('Rungrez product/variant price conflict')
 product=normalize_octane(raw,handle,active_only=True);product['_source_url']=BASE+'/products/'+handle
 return product

def enable_rungrez_source(g):
 from public_catalog_support import enable_public_source
 enable_public_source(g,BASE,'Rung Rez',normalize,'_chotu_rungrez_source')
