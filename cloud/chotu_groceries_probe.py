"""Bounded source access/schema verification for the owner's exact groceries scope."""
import json,os,re,time
from pathlib import Path
from datetime import datetime,timezone
from urllib.parse import urljoin,urlsplit,urlencode
from urllib.robotparser import RobotFileParser
import requests
from bs4 import BeautifulSoup
from source_research import publish,clean_html
from source_probe import inspect_page
ROOT=Path(__file__).resolve().parents[1]

def main():
 request=json.loads((ROOT/'cloud/chotu-groceries-request.json').read_text());base=request['url'];host=urlsplit(base).hostname
 report=dict(run_id=os.environ['GITHUB_RUN_ID'],store=request['store'],checked_utc=datetime.now(timezone.utc).isoformat(),requested_pages=len(request['pages']),status='checking',responses=[])
 session=requests.Session();session.headers.update({'User-Agent':'ChotuAppCatalog/1.0'})
 robot=None
 def read(url):
  if urlsplit(url).scheme!='https' or urlsplit(url).hostname!=host:raise ValueError('Outside approved source host')
  if robot is not None and not robot.can_fetch('ChotuAppCatalog',url):raise ValueError('Public robots disallows requested source URL')
  time.sleep(1.5);r=session.get(url,timeout=(15,45),allow_redirects=False)
  report['responses'].append(dict(url=url,status=r.status_code,bytes=len(r.content)))
  if r.status_code in (401,403,429,503):raise ValueError('Source denied or limited; no alternate route attempted')
  r.raise_for_status()
  if r.is_redirect:raise ValueError('Source redirect requires review')
  if len(r.content)>8*1024*1024:raise ValueError('Source response exceeds bounds')
  return r
 try:
  r=read(base+'/robots.txt');robot=RobotFileParser();robot.parse(r.text.splitlines())
  report['scope_pages_allowed']=sum(robot.can_fetch('ChotuAppCatalog',p['url']) for p in request['pages'])
  allowed=[p['url'] for p in request['pages'] if robot.can_fetch('ChotuAppCatalog',p['url'])]
  if not allowed:raise ValueError('Public robots disallows every requested scope page')
  first=allowed[0];r=read(first);soup=BeautifulSoup(r.text,'html.parser')
  report['page_title']=soup.title.get_text(' ',strip=True) if soup.title else ''
  links=list(dict.fromkeys(urljoin(first,a['href']) for a in soup.select('a.product-item-link[href], .product.name a[href], .product-item-photo[href]')))
  links=[u for u in links if urlsplit(u).hostname==host and urlsplit(u).scheme=='https'];report['listing_product_links']=links[:5]
  report['pagination_links']=[urljoin(first,a['href']) for a in soup.select('.pages a[href], a.next[href]')][:6]
  if links:
   r=read(links[0]);detail=BeautifulSoup(r.text,'html.parser');report['sample_product_html']=clean_html(r.text);report['sample_product_structure']=inspect_page(r.text,links[0])
  else:report['listing_html']=clean_html(r.text)
  query='{products(search:"Shan",pageSize:1){total_count items{id sku name url_key stock_status categories{id name url_path} price_range{minimum_price{regular_price{value currency}final_price{value currency}}}}}}'
  endpoint=base+'/graphql?'+urlencode({'query':query})
  if robot.can_fetch('ChotuAppCatalog',endpoint):
   r=read(endpoint)
   try:report['public_catalog_schema']=r.json()
   except ValueError:report['public_catalog_schema']='not_json'
  report['status']='source_inspected'
 except (requests.RequestException,ValueError) as exc:report.update(status='source_hold',error=str(exc)[:500])
 finally:session.close()
 publish(report,branch='chotu-groceries-reports');print(report['status'],report.get('error',''))
if __name__=='__main__':main()
