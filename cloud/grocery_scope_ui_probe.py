"""Bounded anonymous UI evidence for exact owner-supplied grocery scopes."""
import json,os,re,tempfile,time
from pathlib import Path
from urllib.parse import urlsplit,urljoin,parse_qsl
from playwright.sync_api import sync_playwright
from source_research import publish

def parser_evidence(scope):
 """Compare the production traversal with bounded public card evidence."""
 import requests
 from types import SimpleNamespace
 from bs4 import BeautifulSoup
 from resume_support import ResponseCache
 from chotu_groceries_source_support import PublicCatalog
 with tempfile.TemporaryDirectory() as tmp:
  cache=ResponseCache(Path(tmp)/'pages.sqlite3')
  try:
   reader=PublicCatalog({'S':requests.Session(),'_chotu_tls':SimpleNamespace(saved_response_cache=cache),'_chotu_wait':lambda:None,'_chotu_backoff':lambda seconds,*_:time.sleep(seconds)},print)
   result={}
   try:
    links,total,pages=reader.discover_scope(scope)
    result.update(links=sorted(links),total=total,pages=sorted(pages),count_changed=reader.scope_count_changed)
   except Exception as exc:result.update(error=type(exc).__name__+': '+str(exc)[:500])
   result['rendered']=[]
   for (url,) in cache.db.execute('SELECT url FROM pages').fetchall():
    if '#chotu-rendered-listing-v2' not in url:continue
    response=cache.get(url);soup=BeautifulSoup(response.text,'html.parser')
    result['rendered'].append(dict(url=url.split('#')[0],toolbar=[v.get_text(' ',strip=True) for v in soup.select('.toolbar-amount')],cards=len(soup.select('.products-grid .product-item')),result_links=sorted({a['href'] for a in soup.select('#product_result a[href]')}),card_links=sorted({a['href'] for a in soup.select('.products-grid .product-item a.product-item-link[href]')})))
   return result
  finally:cache.close()

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
     record['page_size_controls']=page.locator('select[data-role="limiter"],select#limiter').evaluate_all('(nodes) => nodes.map(n => ({id:n.id,options:Array.from(n.options).map(o=>({value:o.value,selected:o.selected}))}))')
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
     if record['page_size_controls']:
      page.goto(scope['url'],wait_until='domcontentloaded',timeout=60000)
      limiter=page.locator('select[data-role="limiter"],select#limiter').first
      options=record['page_size_controls'][0]['options'];value=next((v['value'] for v in options if str(v['value']).isdigit()),None)
      if value:
       limiter.select_option(value);page.wait_for_timeout(4000)
       record['explicit_page_size']=dict(value=value,url=page.url,pages=[])
       record['explicit_page_size']['selected_toolbar']=page.locator('.toolbar-amount').all_text_contents()
       record['explicit_page_size']['selected_pagination']=page.locator('.pages a[href],a.next[href]').evaluate_all('(nodes)=>nodes.map(n=>n.href)')
       # Inspect the public toolbar configuration before testing its named URL control.
       from bs4 import BeautifulSoup
       toolbar=BeautifulSoup(page.content(),'html.parser')
       record['toolbar_config']=[dict(n.attrs) for n in toolbar.select('[data-mage-init]') if 'productListToolbarForm' in n.get('data-mage-init','')]
       from urllib.parse import urlencode,urlunsplit
       q=dict(seed_query,product_list_limit=value)
       target=urlunsplit((seed.scheme,seed.netloc,seed.path,urlencode(q),''))
       targets=[target];seen=set()
       while targets and len(seen)<5:
        target=targets.pop(0)
        if target in seen:continue
        part=urlsplit(target);q=dict(parse_qsl(part.query))
        if part.hostname!=seed.hostname or part.path.rstrip('/')!=seed.path.rstrip('/') or any(q.get(k)!=v for k,v in seed_query.items()):raise ValueError('Page-size UI changed owner scope')
        seen.add(target);response=page.goto(target,wait_until='domcontentloaded',timeout=60000)
        if not response or response.status>=400:break
        page.wait_for_timeout(2000)
        record['explicit_page_size']['pages'].append(dict(url=page.url,toolbar=page.locator('.toolbar-amount').all_text_contents(),links=page.locator('.products-grid .product-item a.product-item-link[href]').evaluate_all('(nodes)=>nodes.map(n=>n.href)')))
        for link in page.locator('.pages a[href],a.next[href]').evaluate_all('(nodes)=>nodes.map(n=>n.href)'):
         part=urlsplit(link);query=dict(parse_qsl(part.query))
         if part.hostname==seed.hostname and part.path.rstrip('/')==seed.path.rstrip('/') and {k:v for k,v in query.items() if k!='p'}=={k:v for k,v in q.items() if k!='p'} and link not in seen and link not in targets:targets.append(link)
    except Exception as exc:record['error']=type(exc).__name__
    finally:page.close();record['production_parser']=parser_evidence(scope);report['scopes'].append(record)
  finally:browser.close()
 publish(report,branch='chotu-groceries-reports');print('Public owner-scope UI evidence saved; no private catalogs accessed.')
if __name__=='__main__':main()
