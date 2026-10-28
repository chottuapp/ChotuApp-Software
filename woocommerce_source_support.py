"""Allowlisted public WooCommerce Store API adapter; exact variation offers only."""
import csv,html,json,re,time
from decimal import Decimal
from urllib.parse import urlsplit
from bs4 import BeautifulSoup
HOSTS={'xcessorieshub.com','designbydas.com'}

def offer(p):
 q=p['prices']
 if q.get('currency_code')!='PKR':raise ValueError('Non-PKR WooCommerce offer')
 unit=q['currency_minor_unit']
 if not isinstance(unit,int) or not 0<=unit<=4:raise ValueError('Unknown currency scale')
 def amount(key):
  value=Decimal(str(q[key]))/(Decimal(10)**unit)
  if not value.is_finite() or value<=0:raise ValueError('Invalid source price')
  return value
 price=amount('price');regular=amount('regular_price')
 if regular<price:raise ValueError('Regular price below payable price')
 if not isinstance(p.get('is_in_stock'),bool) or not isinstance(p.get('is_purchasable'),bool):raise ValueError('Unknown availability')
 if p.get('is_on_backorder'):raise ValueError('Backorder policy requires explicit review')
 return regular,price,p['is_in_stock'] and p['is_purchasable']

def variants(parent,get):
 if parent['type']=='simple':return [(parent,{})]
 if parent['type']!='variable' or not parent.get('variations'):raise ValueError('Unsupported WooCommerce product type: '+str(parent.get('type')))
 result=[];seen=set()
 for entry in parent['variations']:
  ident=entry['id'];v=get('/wp-json/wc/store/v1/products/'+str(ident))
  if v.get('id')!=ident or v.get('parent')!=parent['id'] or v.get('type')!='variation':raise ValueError('Variation parent identity mismatch')
  attrs=entry['attributes'];values={a['name']:html.unescape(a['value']) for a in attrs}
  if not values or any(not value for value in values.values()) or len(values)>3:raise ValueError('Wildcard/unsupported variation dimensions')
  key=tuple(sorted(values.items()))
  if ident in seen or any(tuple(sorted(x[1].items()))==key for x in result):raise ValueError('Duplicate variation identity')
  seen.add(ident);offer(v);result.append((v,values))
 return result

def export(g,base,name,template,log):
 host=urlsplit(base).hostname.removeprefix('www.');base=base.rstrip('/')
 if host not in HOSTS:raise ValueError('Unapproved WooCommerce host')
 def get(path):
  url=base+path;g['_chotu_wait']();g['_chotu_debug_stage']('WooCommerce public product prices and pages')
  return g['get_json'](url)
 products=[];ids=set();page=1
 while True:
  batch=get('/wp-json/wc/store/v1/products?per_page=100&page='+str(page))
  if not isinstance(batch,list):raise ValueError('Public WooCommerce catalog unavailable')
  for p in batch:
   if p['id'] in ids:raise ValueError('Duplicate catalog pagination identity')
   ids.add(p['id']);products.append(p)
  log('WOO LISTING PROGRESS: '+str(len(products))+' distinct public products; page '+str(page))
  if len(batch)<100:break
  page+=1
  if page>1000:raise ValueError('WooCommerce pagination bound reached')
 if not products:raise ValueError('Empty public catalog')
 wb=g['load_workbook'](template)
 for sheet in ('Products','Product Images','Option Groups','Options','Variant Combinations'):
  if wb[sheet].max_row>1:wb[sheet].delete_rows(2,wb[sheet].max_row-1)
 from ranking_support import ensure_columns
 ensure_columns(wb['Products']);g['ensure_variant_image_fields'](wb['Variant Combinations'])
 checked=[];retained=0
 for index,p in enumerate(products,1):
  # A separate detail read verifies identity and current offers, not catalog aggregate prices.
  current=get('/wp-json/wc/store/v1/products/'+str(p['id']))
  if current.get('id')!=p['id'] or current.get('permalink')!=p['permalink']:raise ValueError('Primary product identity changed')
  p=current
  if p.get('is_password_protected'):continue
  if p.get('is_in_stock') is False:continue
  url=p['permalink']
  if urlsplit(url).hostname.removeprefix('www.')!=host:raise ValueError('Product belongs to another host')
  vs=variants(p,get);offers=[(v,a,offer(v)) for v,a in vs]
  available=[x for x in offers if x[2][2]]
  if not available:continue
  cover=p['images'][0]['src'] if p.get('images') else ''
  if not cover:raise ValueError('Product photo missing')
  pid=g['uid']('CP',base+'|'+str(p['id']));dimensions=[]
  for _,attrs,_ in offers:
   for label in attrs:
    if label not in dimensions:dimensions.append(label)
  gids={label:g['uid']('CG',pid+'|'+label) for label in dimensions}
  for label in dimensions:
   gid=gids[label];g['write_row'](wb['Option Groups'],{'group_id':gid,'title (customer ko dikhega)':label,'select_type':'single','min':1,'max':1,'required (yes/no)':'yes'})
   values=list(dict.fromkeys(a[label] for _,a,_ in offers))
   for value in values:
    linked={v['images'][0]['src'] for v,a,_ in offers if a[label]==value and v.get('images') and v['images'][0]['src']!=cover}
    g['write_row'](wb['Options'],{'option_id':g['uid']('CO',gid+'|'+value),'group_id':gid,'option_name':value,'extra_price (PKR)':0,'option_image_url (agar size/color/variant ki apni image ho)':next(iter(linked)) if len(linked)==1 else '', 'available (yes/no)':'yes' if any(a[label]==value and o[2] for v,a,o in offers) else 'no'})
  for v,attrs,(regular,price,available_now) in offers:
   image=v['images'][0]['src'] if v.get('images') else ''
   if v.get('type')=='variation' and image==cover:image='' # inherited cover is a labelled fallback
   row={'combination_id':g['uid']('CC',base+'|'+str(v['id'])),'product_id':pid,'source_variant_id':str(v['id']),'sku':v.get('sku',''),'base_price (PKR)':float(regular),'sale_price (PKR, agar discount ho)':float(price) if price<regular else None,'available (yes/no)':'yes' if available_now else 'no','variant_image_url':image,'source_url':url}
   row.update(g['variant_image_metadata'](image,cover))
   for pos,label in enumerate(dimensions,1):row.update({f'option_{pos}_group_id':gids[label],f'option_{pos}_value':attrs[label]})
   g['write_row'](wb['Variant Combinations'],row)
  cheapest=min(available,key=lambda x:x[2][1]);regular,price,_=cheapest[2]
  description=(p.get('description') or '')+'\n'+(p.get('short_description') or '')
  if p.get('formatted_weight'):description+='\nWeight: '+p['formatted_weight']
  if p.get('formatted_dimensions'):description+='\nDimensions: '+p['formatted_dimensions']
  # Preserve exact API taxonomy as source labels, never fabricate website order.
  labels=[html.unescape(c['name']) for c in p.get('categories',[])]
  g['write_row'](wb['Products'],{'product_id':pid,'name':html.unescape(p['name']),'description':g['txt'](description),'category':labels[-1] if labels else '', 'subcategory':'','brand':name,'condition (new/used)':'new','sku':cheapest[0].get('sku',''),'base_price (PKR)':float(regular),'sale_price (PKR, agar discount ho)':float(price) if price<regular else None,'available (yes/no)':'yes','scraped_image_url (cover, auto)':cover,'source_url':url,'option_groups':','.join(gids.values()),'website_order_status':'unverified','analysis_note':'Public WooCommerce taxonomy: '+' > '.join(labels)+'; API order is not verified website display order.'})
  for pos,im in enumerate(p['images'],1):g['write_row'](wb['Product Images'],{'image_id':g['uid']('CI',pid+'|'+str(pos)),'product_id':pid,'image_order':pos,'scraped_image_url (auto)':im['src'],'is_primary (yes/no)':'yes' if pos==1 else 'no','source_url':url})
  checked.append(url);retained+=1
  log('WOO PRODUCT PROGRESS: '+str(index)+'/'+str(len(products))+' checked; '+str(retained)+' retained')
 if not retained:raise ValueError('No verified sellable products')
 out=g['OUT'];out.mkdir(parents=True,exist_ok=True);target=out/(name+' - REFRESH REVIEW.xlsx');tmp=out/(name+' - BUILDING.xlsx');wb.save(tmp);wb.close();tmp.replace(target)
 for suffix in ['PRICE AUDIT','STOREFRONT AUDIT','IMAGE AUDIT','QUALITY REPORT']:
  with (out/(name+' - '+suffix+'.csv')).open('w',encoding='utf-8-sig',newline='') as f:
   writer=csv.writer(f);writer.writerow(['source_url','status','detail'])
   for url in checked:writer.writerow([url,'REVIEW','Exact public Store API detail and variation offers; website display order not independently proven.'])
 log('EXPORT BUILT: '+str(retained)+' products; full independent 804 Audit required before delivery');log('FILE: '+str(target))

def enable_woocommerce_source(g):
 original=g['_chotuapp_run_site_original']
 def run(base,name,template,log):
  if (urlsplit(base).hostname or '').removeprefix('www.') not in HOSTS:return original(base,name,template,log)
  return export(g,base,name,template,log)
 g['_chotuapp_run_site_original']=run
