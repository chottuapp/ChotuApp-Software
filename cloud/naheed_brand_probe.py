"""Bounded verification of the selected Naheed brand-discovery paths."""
import json,os,time
import requests
from bs4 import BeautifulSoup
from chotu_groceries_source_support import PublicCatalog
from naheed_brand_support import brand_key,load_request
from source_research import publish

def main():
 requested=[v.strip() for v in os.environ['GROCERY_BRAND_NAMES'].split(',') if v.strip()]
 if not 1<=len(requested)<=3:raise ValueError('Inspect one to three exact approved brands')
 approved={brand_key(v['brand']):v for v in load_request()['brands']}
 # Read-only spelling verification for the owner's explicitly requested brand.
 if brand_key('Rose Patel') in approved:
  from urllib.parse import urlencode
  approved[brand_key('Rose Petal')]=dict(brand='Rose Petal',url='https://www.naheed.pk/catalogsearch/result/?'+urlencode({'q':'Rose Petal'}),examples=[])
 if any(brand_key(v) not in approved for v in requested):raise ValueError('Brand not in owner-approved request')
 reader=PublicCatalog({'S':requests.Session(),'_chotu_wait':lambda:None,'_chotu_backoff':lambda seconds,*_:time.sleep(seconds)},print,brand_refresh=True)
 records=[]
 for name in requested:
  scope=approved[brand_key(name)];record=dict(brand=scope['brand'])
  try:
   links,total,pages=reader.discover_scope(scope)
   record.update(visible=len(links),total=total,pages=sorted(pages),count_changed=reader.scope_count_changed,proofs=[v for v in reader.brand_proofs if v['brand']==scope['brand']],samples=[])
   for url in sorted(links)[:3]:
    soup=BeautifulSoup(reader.read_page(url),'html.parser');brand=soup.select_one('.product-info-main .brand-name a');title=soup.select_one('h1')
    record['samples'].append(dict(url=url,manufacturer=brand.get_text(' ',strip=True) if brand else '',title=title.get_text(' ',strip=True) if title else ''))
  except Exception as exc:
   record.update(error=type(exc).__name__+': '+str(exc)[:500],response_identity=getattr(reader,'last_response_identity',None))
   if getattr(exc,'html',None):
    soup=BeautifulSoup(exc.html,'html.parser');heading=soup.select_one('h1');canonical=soup.select_one('link[rel=canonical][href]')
    record['redirect_page']=dict(title=soup.title.get_text(' ',strip=True)[:300] if soup.title else '',heading=heading.get_text(' ',strip=True)[:500] if heading else '',canonical=canonical.get('href') if canonical else None)
  records.append(record)
 publish(dict(run_id=os.environ['GITHUB_RUN_ID'],brand_discovery=records),branch='chotu-groceries-reports')
 print('Exact Naheed brand discovery evidence saved')
if __name__=='__main__':main()
