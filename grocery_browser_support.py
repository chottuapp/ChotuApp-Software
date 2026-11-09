"""Render the ordinary anonymous public search UI, including its Load More button."""
import re
from urllib.parse import urlsplit,parse_qsl
from bs4 import BeautifulSoup
SELECTOR='#product_result a[href], .products-grid .product-item a.product-item-link[href], .ais-Hits-item a[href]'

def render_listing(url,pause=lambda:None,log=lambda _:None,*,load_all=True):
 if urlsplit(url).scheme!='https' or urlsplit(url).hostname!='www.naheed.pk':raise ValueError('Outside approved public grocery storefront')
 from playwright.sync_api import sync_playwright,TimeoutError as BrowserTimeout
 with sync_playwright() as driver:
  browser=driver.chromium.launch(headless=True)
  try:
   page=browser.new_page();limited=[]
   page.on('response',lambda r:limited.append(r.status) if r.status in (429,503) and urlsplit(r.url).hostname=='www.naheed.pk' else None)
   response=page.goto(url,wait_until='domcontentloaded',timeout=60000)
   if not response or response.status in (401,403):raise RuntimeError('SOURCE BLOCKED: public grocery browser request denied; no access challenge bypass')
   if response.status>=400:raise RuntimeError('SOURCE PAUSED: public grocery browser service error; checkpoint retained')
   actual=urlsplit(page.url);wanted=urlsplit(url)
   if actual.hostname!='www.naheed.pk' or actual.path.rstrip('/')!=wanted.path.rstrip('/') or any(dict(parse_qsl(actual.query)).get(k)!=v for k,v in parse_qsl(wanted.query) if k in ('q','manufacturer','p')):raise ValueError('Foreign or scope-changing grocery browser redirect')
   if re.search(r'just a moment|attention required|captcha',page.title(),re.I):raise RuntimeError('SOURCE BLOCKED: public storefront challenge; no solver used')
   page.wait_for_function("selector => document.querySelector(selector) || /no products found|we can.t find products|your search returned no results/i.test(document.body.innerText)",arg=SELECTOR,timeout=60000)
   page.wait_for_timeout(1000)
   if load_all:
    for step in range(1000):
     pause()
     if limited:raise RuntimeError('SOURCE PAUSED: public grocery storefront rate limit; retry saved store after at least 300s')
     button=page.locator('#load-more').first
     if not button.count() or not button.is_visible():break
     before=page.locator(SELECTOR).count();button.click(timeout=30000)
     page.wait_for_function("({selector,before}) => document.querySelectorAll(selector).length>before || (document.querySelector('#load-more') && getComputedStyle(document.querySelector('#load-more')).display==='none')",arg={'selector':SELECTOR,'before':before},timeout=60000)
     page.wait_for_timeout(750)
     if step%10==0:log('GROCERY PUBLIC UI: load-more step '+str(step+1)+'; '+str(page.locator(SELECTOR).count())+' product links')
    else:raise ValueError('Grocery public load-more bound exceeded; no partial completion')
   content=page.content()
   if len(content.encode())>16*1024*1024:raise ValueError('Rendered grocery listing exceeds bound')
   return content
  except BrowserTimeout as exc:raise RuntimeError('SOURCE PAUSED: public grocery rendering incomplete; retry saved store after at least 300s; no empty catalog guessed') from exc
  finally:browser.close()
