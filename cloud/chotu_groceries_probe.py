"""Bounded source access/schema verification for the owner's exact groceries scope."""
import json,re,time
from pathlib import Path
from datetime import datetime,timezone
from urllib.parse import urljoin,urlsplit,urlencode
from urllib.robotparser import RobotFileParser
import requests
from bs4 import BeautifulSoup
from source_research import publish
ROOT=Path(__file__).resolve().parents[1]

def main():
 request=json.loads((ROOT/'cloud/chotu-groceries-request.json').read_text());base=request['url'];host=urlsplit(base).hostname
 report=dict(store=request['store'],checked_utc=datetime.now(timezone.utc).isoformat(),requested_pages=len(request['pages']),status='checking',responses=[])
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
  first=request['pages'][0]['url'];r=read(first);soup=BeautifulSoup(r.text,'html.parser')
  report['page_title']=soup.title.get_text(' ',strip=True) if soup.title else ''
  links=list(dict.fromkeys(urljoin(first,a['href']) for a in soup.select('a.product-item-link[href], .product.name a[href], .product-item-photo[href]')))
  links=[u for u in links if urlsplit(u).hostname==host and urlsplit(u).scheme=='https'];report['listing_product_links']=links[:5]
  report['pagination_links']=[urljoin(first,a['href']) for a in soup.select('.pages a[href], a.next[href]')][:6]
  if links:
   r=read(links[0]);detail=BeautifulSoup(r.text,'html.parser');report['sample_product_html']=str(detail.select_one('main') or detail)[:180000]
  else:report['listing_html']=str(soup.select_one('main') or soup)[:100000]
  report['status']='source_inspected'
 except (requests.RequestException,ValueError) as exc:report.update(status='source_hold',error=str(exc)[:500])
 finally:session.close()
 publish(report,branch='chotu-groceries-reports');print(report['status'],report.get('error',''))
if __name__=='__main__':main()
