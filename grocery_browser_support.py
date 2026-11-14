"""Render the ordinary anonymous public search UI, including its Load More button."""
import re,time
from urllib.parse import urlsplit,parse_qsl
from bs4 import BeautifulSoup
class ListingRenderIncomplete(RuntimeError):
 """Public UI did not finish; retain scope review without approving empty results."""

SELECTOR='#product_result a[href], .products-grid .product-item a.product-item-link[href], .ais-Hits-item a[href]'

def brand_filter_pattern(brand):
 return re.compile(r'^\s*'+re.escape(brand).replace(r'\ ',r'\s+')+r'\s*\(\s*([\d,]+)\s*\)\s*$',re.I)

def select_brand_filter(page,brand):
 pattern=brand_filter_pattern(brand)
 matches=[n for n in page.get_by_text(pattern).all() if n.is_visible()]
 if len(matches)!=1:raise ListingRenderIncomplete('Exact public By Brand filter missing or ambiguous: '+brand)
 node=matches[0];match=pattern.fullmatch(node.inner_text());expected=int(match[1].replace(',',''))
 node.click(timeout=30000);page.wait_for_timeout(1500)
 matches=[n for n in page.get_by_text(pattern).all() if n.is_visible()]
 if len(matches)!=1:raise ListingRenderIncomplete('Selected brand filter cannot be verified: '+brand)
 selected=matches[0].evaluate("n => {const scope=n.closest('label')||n.closest('li')||n.parentElement;const box=scope.querySelector('input[type=checkbox]');if(box)return box.checked;const role=n.closest('[role=checkbox]');return role?role.getAttribute('aria-checked')==='true':null;}")
 if selected is not True:raise ListingRenderIncomplete('Public By Brand selection not confirmed: '+brand)
 return expected

def exhaust_listing(page,pause,log,limited,pending,*,max_steps=1000):
 def button_visible():
  node=page.locator('#load-more').first
  return bool(node.count() and node.is_visible())
 def busy():return bool(page.locator('#loader:visible,.loading-mask:visible').count())
 def settle(before):
  deadline=time.monotonic()+60
  while True:
   pause()
   if limited:raise RuntimeError('SOURCE PAUSED: grocery public source rate limit; retry saved store after at least 300s')
   if not pending and not busy():
    if page.locator(SELECTOR).count()>before:return
    if not button_visible():
     page.wait_for_timeout(500)
     if not pending and not busy() and not button_visible():return
   if time.monotonic()>deadline:raise ListingRenderIncomplete('Grocery loading did not settle; scope requires review; no partial catalog approval')
   page.wait_for_timeout(250)
 idle=0
 for step in range(max_steps):
  pause()
  if limited:raise RuntimeError('SOURCE PAUSED: grocery public source rate limit; retry saved store after at least 300s')
  before=page.locator(SELECTOR).count()
  if button_visible():
   page.locator('#load-more').first.click(timeout=30000);page.wait_for_timeout(250);settle(before);idle=0
  else:
   page.evaluate("selector => {const nodes=document.querySelectorAll(selector); if(nodes.length) nodes[nodes.length-1].scrollIntoView({block:'end'}); window.scrollBy(0,window.innerHeight);}",SELECTOR)
   page.wait_for_timeout(1500);settle(before)
   idle=idle+1 if page.locator(SELECTOR).count()==before and not button_visible() else 0
   if idle>=2:break
  if step%10==0:log('GROCERY PUBLIC UI: traversal step '+str(step+1)+'; '+str(page.locator(SELECTOR).count())+' product links')
 else:raise ValueError('Grocery public traversal bound exceeded; no partial completion')

def render_listing(url,pause=lambda:None,log=lambda _:None,*,load_all=True,brand=None):
 if urlsplit(url).scheme!='https' or urlsplit(url).hostname!='www.naheed.pk':raise ValueError('Outside approved public grocery storefront')
 from playwright.sync_api import sync_playwright,TimeoutError as BrowserTimeout
 with sync_playwright() as driver:
  browser=driver.chromium.launch(headless=True)
  try:
   page=browser.new_page();limited=[];pending=set()
   def track(request):
    if request.resource_type in ('xhr','fetch') and not re.search(r'google-analytics|googletagmanager|facebook|doubleclick|clarity\.ms|hotjar',urlsplit(request.url).hostname or ''):pending.add(request)
   page.on('request',track);page.on('requestfinished',lambda request:pending.discard(request));page.on('requestfailed',lambda request:pending.discard(request))
   page.on('response',lambda r:limited.append(r.status) if r.status in (429,503) and urlsplit(r.url).hostname=='www.naheed.pk' else None)
   response=page.goto(url,wait_until='domcontentloaded',timeout=60000)
   if not response or response.status in (401,403):raise RuntimeError('SOURCE BLOCKED: public grocery browser request denied; no access challenge bypass')
   if response.status>=400:raise RuntimeError('SOURCE PAUSED: public grocery browser service error; checkpoint retained')
   actual=urlsplit(page.url);wanted=urlsplit(url)
   if actual.hostname!='www.naheed.pk' or actual.path.rstrip('/')!=wanted.path.rstrip('/') or any(dict(parse_qsl(actual.query)).get(k)!=v for k,v in parse_qsl(wanted.query) if k in ('q','manufacturer','p')):raise ValueError('Foreign or scope-changing grocery browser redirect')
   if re.search(r'just a moment|attention required|captcha',page.title(),re.I):raise RuntimeError('SOURCE BLOCKED: public storefront challenge; no solver used')
   page.wait_for_function("selector => document.querySelector(selector) || /no products found|no products for query|we can.t find products|your search returned no results/i.test(document.body.innerText)",arg=SELECTOR,timeout=60000)
   page.wait_for_timeout(1000)
   brand_total=select_brand_filter(page,brand) if brand else None
   if load_all:exhaust_listing(page,pause,log,limited,pending)
   if brand:
    page.evaluate("value => {document.documentElement.setAttribute('data-chotu-selected-brand',value.brand);document.documentElement.setAttribute('data-chotu-brand-total',String(value.total));}",dict(brand=brand,total=brand_total))
   content=page.content()
   if len(content.encode())>16*1024*1024:raise ValueError('Rendered grocery listing exceeds bound')
   return content
  except BrowserTimeout as exc:raise ListingRenderIncomplete('Public grocery rendering timed out; scope requires review; no empty catalog guessed') from exc
  finally:browser.close()
