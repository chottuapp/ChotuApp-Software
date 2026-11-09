"""Public storefront/code diagnosis only; no Drive, private catalogs or live writes."""
import json,os,re
from urllib.parse import urlsplit,urlunsplit
import requests
from source_research import publish
from hold804_repairs import category
from subcategory_inference_support import infer
from bs4 import BeautifulSoup

def read(url):
 r=requests.get(url,timeout=(10,30));r.raise_for_status();return r.json()
def probe(url):
 p=urlsplit(url)
 if p.scheme!='https' or p.hostname!='wvwjldtqorvkgtkunble.supabase.co' or p.username or p.password:raise ValueError('Outside exact public Mansab media host')
 result={'url':urlunsplit((p.scheme,p.netloc,p.path,'','')),'requests':[]}
 for mode,headers in [('normal',{}),('mobile',{'User-Agent':'Dart/3.5 (dart:io)'})]:
  try:
   with requests.get(url,headers=headers,timeout=(10,20),stream=True,allow_redirects=False) as r:
    prefix=next(r.iter_content(1024),b'')
    result['requests'].append(dict(mode=mode,status=r.status_code,content_type=r.headers.get('Content-Type'),bytes_sampled=len(prefix),sample_hex=prefix[:16].hex()))
  except requests.RequestException as exc:result['requests'].append(dict(mode=mode,error=type(exc).__name__))
 return result

def main():
 report=dict(run_id=os.environ['GITHUB_RUN_ID'],status='public_source_only_diagnosis',mansab={},blackbeiger=[])
 slug='charcoal-textured-2-piece-co-ord-suit-mansab'
 data=read('https://mansabpk.com/api/products?slug='+slug)
 if isinstance(data,dict) and data.get('slug')==slug:product=data
 elif isinstance(data,list):product=next(v for v in data if v.get('slug')==slug)
 else:raise ValueError('Unexpected public Mansab source schema')
 report['mansab']=dict(source='https://mansabpk.com/product/'+slug,name=product.get('name'),images=[probe(u) for u in product.get('images',[])[:3]])
 for page in (1,2):
  data=read('https://blackbeiger.com/products.json?limit=250&page='+str(page));products=data['products']
  for p in products:
   body=BeautifulSoup(p.get('body_html') or '', 'html.parser').get_text('\n',strip=True)
   row=dict(name=p['title'],description=body,source_url='https://blackbeiger.com/products/'+p['handle'])
   report['blackbeiger'].append(dict(**row,public_product_type=p.get('product_type'),classification=category(row,'Blackbeiger') or infer(row['name'],body)))
  if len(products)<250:break
 publish(report,branch='category-reports');print('Public storefront and classifier diagnosis published. No private catalogs accessed.')
if __name__=='__main__':main()
