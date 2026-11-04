"""One normal anonymous browser check per approved homepage; stop on access controls."""
import asyncio,json,os,re,sys,shutil
from pathlib import Path
from urllib.parse import urljoin,urlsplit
from urllib.robotparser import RobotFileParser
import requests
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
AGENT='Mozilla/5.0 (compatible; ChotuAppCatalogRefresh/1.0)'
STORES=('Computer Zone','Gift4U','Axis PK')
def denied(status,text):
 from bs4 import BeautifulSoup
 soup=BeautifulSoup(text,'html.parser');title=soup.title.get_text(' ',strip=True) if soup.title else ''
 visible=soup.get_text(' ',strip=True)
 return status in (401,403,429,503) or bool(re.search(r'just a moment|attention required|captcha verification',title,re.I)) or bool(re.search(r'verify (?:that )?you are human',visible,re.I)) or bool(soup.select_one('#challenge-running, #challenge-form, .cf-challenge-running'))
def product_link(soup,base,policy):
 host=(urlsplit(base).hostname or '').removeprefix('www.')
 for anchor in soup.select('.products .product a[href], .wx-listing-product-wrapper .listing-grid a[href], a.woocommerce-LoopProduct-link[href], a[href*="/product/"], a[href*="/products/"]'):
  url=urljoin(base,anchor.get('href',''));p=urlsplit(url)
  if p.scheme=='https' and not p.username and not p.password and (p.hostname or '').removeprefix('www.')==host and not p.query and not p.fragment and policy.can_fetch(AGENT,url):return url
 return None
async def main():
 from bs4 import BeautifulSoup
 from playwright.async_api import async_playwright
 sites={s['name']:s for s in json.loads((ROOT/'cloud/fetch-update-release.json').read_text())['fresh_stores']};results=[]
 selected=json.loads(os.environ.get('PUBLIC_STORE_NAMES',json.dumps(STORES)))
 if not isinstance(selected,list) or not selected or len(selected)>len(STORES) or any(s not in STORES for s in selected):raise ValueError('Only approved exact source names may be checked')
 async with async_playwright() as driver:
  browser=await driver.chromium.launch(headless=True,**({'channel':'chrome'} if shutil.which('google-chrome') else {}))
  for name in dict.fromkeys(selected):
   base=sites[name]['url'].rstrip('/');record={'store':name,'status':'unchecked'};page=None
   try:
    robots=requests.get(base+'/robots.txt',headers={'User-Agent':AGENT},timeout=30,allow_redirects=False)
    record['robots_status']=robots.status_code
    if robots.status_code not in (200,404):record['status']='permissions_unverified';continue
    policy=RobotFileParser();policy.parse(robots.text.splitlines() if robots.status_code==200 else [])
    if not policy.can_fetch(AGENT,base+'/'):record['status']='robots_disallowed';continue
    context=await browser.new_context(user_agent=AGENT);page=await context.new_page()
    response=await page.goto(base+'/',wait_until='domcontentloaded',timeout=45000);status=response.status if response else 0;body=await page.content();record['homepage_status']=status
    if (urlsplit(page.url).hostname or '').removeprefix('www.')!=(urlsplit(base).hostname or '').removeprefix('www.'):record['status']='external_redirect_unverified';continue
    if denied(status,body):record['status']='public_homepage_denied';continue
    if status!=200:record['status']='homepage_unavailable';continue
    from source_probe import inspect_page
    home_info=inspect_page(body,page.url)
    record['platform_markers']=home_info['platform_markers']
    home_soup=BeautifulSoup(body,'html.parser')
    record['public_link_samples']=list(dict.fromkeys(urljoin(base,a['href']).split('?')[0] for a in home_soup.select('a[href]') if re.search('product|shop|catalog',a['href'],re.I)))[:8]
    url=product_link(home_soup,base,policy)
    if name=='Computer Zone' and base+'/products' in record['public_link_samples'] and policy.can_fetch(AGENT,base+'/products'):url=base+'/products'
    record['status']='public_homepage_only'
    if not url:continue
    response=await page.goto(url,wait_until='domcontentloaded',timeout=45000);status=response.status if response else 0;body=await page.content();record['product_status']=status
    if (urlsplit(page.url).hostname or '').removeprefix('www.')!=(urlsplit(base).hostname or '').removeprefix('www.'):record['status']='external_redirect_unverified';continue
    if denied(status,body):record['status']='public_product_denied';continue
    if status!=200:record['status']='public_product_unavailable';continue
    await page.wait_for_timeout(1500)
    body=await page.content()
    if denied(status,body):record['status']='public_product_denied';continue
    from source_probe import inspect_page
    info=inspect_page(body,page.url)
    record.update(status='public_product_readable',source_url=page.url.split('?')[0],platform_markers=info['platform_markers'],product_schema_samples=info['product_schema_samples'])
    content=page.locator('main').first
    if await content.count()==0:content=page.locator('body')
    record['visible_product_text']=(await content.inner_text())[:18000]
    record['public_controls']=await content.locator('button, select, input[type="radio"]').evaluate_all('(nodes)=>nodes.slice(0,60).map(n=>({tag:n.tagName,text:n.innerText,name:n.name,value:n.value,disabled:n.disabled,classes:n.className}))')
    from source_research import public_product_state
    record['public_product_state']=public_product_state(BeautifulSoup(body,'html.parser'))
    if name=='Axis PK':
     from axis_source_support import page_products
     record['public_next_products']=page_products(body)
   except Exception as exc:record.update(status='check_unavailable',error_type=type(exc).__name__)
   finally:
    if page:await page.context.close()
    results.append(record);print(json.dumps(record,sort_keys=True),flush=True)
  await browser.close()
 Path('public-page-access-results.json').write_text(json.dumps(results,indent=2))
if __name__=='__main__':asyncio.run(main())
