"""Bounded anonymous UI evidence for exact owner-supplied grocery scopes."""
import json,os,re
from pathlib import Path
from urllib.parse import urlsplit,urljoin,parse_qsl
from playwright.sync_api import sync_playwright
from source_research import publish

def main():
 indexes=[int(v) for v in os.environ['GROCERY_PUBLIC_SCOPE_INDEXES'].split(',') if v.strip()]
 if not 1<=len(indexes)<=6 or len(set(indexes))!=len(indexes):raise ValueError('Select at most six exact owner scopes')
 scopes=json.loads((Path(__file__).with_name('chotu-groceries-request.json')).read_text())['pages']
 if any(not 1<=i<=len(scopes) for i in indexes):raise ValueError('Unknown owner scope')
 report=dict(run_id=os.environ['GITHUB_RUN_ID'],status='public_scope_ui_evidence',scopes=[])
 with sync_playwright() as driver:
  browser=driver.chromium.launch(headless=True)
  try:
   for index in indexes:
    scope=scopes[index-1];record=dict(index=index,scope=scope);page=browser.new_page()
    try:
     response=page.goto(scope['url'],wait_until='domcontentloaded',timeout=60000)
     record['http_status']=response.status if response else None
     if not response or response.status>=400:record['error']='Source denied or unavailable; no bypass';continue
     if re.search(r'captcha|just a moment|attention required',page.title(),re.I):record['error']='Source challenge; no bypass';continue
     page.wait_for_timeout(8000)
     record['page_title']=page.title();record['visible_text']=page.locator('body').inner_text()[:14000]
     record['toolbar']=[v.inner_text() for v in page.locator('.toolbar-amount').all()]
     record['product_links']=page.locator('#product_result a[href], .products-grid .product-item a.product-item-link[href]').evaluate_all('(nodes) => nodes.map(n => n.href)')
     record['product_links']=[u for u in record['product_links'] if urlsplit(u).hostname=='www.naheed.pk' and not urlsplit(u).query and not urlsplit(u).fragment and urlsplit(u).path.strip('/').count('/')==0]
     record['listing_cards']=page.locator('.products-grid .product-item').count()
     record['cards']=page.locator('.products-grid .product-item').evaluate_all('(nodes) => nodes.map(n => ({text:n.innerText.slice(0,250),links:Array.from(n.querySelectorAll(\"a.product-item-link[href]\")).map(a=>a.href)}))')
     record['result_container']=page.locator('#product_result').evaluate_all('(nodes) => nodes.map(n => n.innerText.slice(0,15000))')
     record['pagination']=page.locator('.pages a[href],a.next[href]').evaluate_all('(nodes) => nodes.map(n => ({text:n.innerText,url:n.href}))')
     record['next_pages']=[]
     seed=urlsplit(scope['url']);seed_query=dict(parse_qsl(seed.query))
     candidates=[]
     for link in record['pagination']:
      part=urlsplit(link['url']);query=dict(parse_qsl(part.query))
      if part.scheme=='https' and part.hostname==seed.hostname and part.path.rstrip('/')==seed.path.rstrip('/') and {k:v for k,v in query.items() if k!='p'}==seed_query and str(query.get('p','')).isdigit() and link['url'] not in candidates:candidates.append(link['url'])
     for url in candidates[:5]:
      next_response=page.goto(url,wait_until='domcontentloaded',timeout=60000)
      if not next_response or next_response.status>=400:record['next_pages'].append(dict(url=url,status=next_response.status if next_response else None));continue
      page.wait_for_timeout(5000)
      record['next_pages'].append(dict(url=url,status=next_response.status,toolbar=[v.inner_text() for v in page.locator('.toolbar-amount').all()],cards=page.locator('.products-grid .product-item').evaluate_all('(nodes) => nodes.map(n => ({text:n.innerText.slice(0,250),links:Array.from(n.querySelectorAll(\"a.product-item-link[href]\")).map(a=>a.href)}))')))
    except Exception as exc:record['error']=type(exc).__name__
    finally:page.close();report['scopes'].append(record)
  finally:browser.close()
 publish(report,branch='chotu-groceries-reports');print('Public owner-scope UI evidence saved; no private catalogs accessed.')
if __name__=='__main__':main()
