"""Bounded anonymous browser inspection of the owner-requested public meat store."""
import json,os,re
from urllib.parse import urlsplit,urljoin
from playwright.sync_api import sync_playwright
from source_research import publish
BASE='https://barkatmeathouse.com'

def snapshot(page):
 return dict(url=page.url,title=page.title(),text=page.locator('body').inner_text()[:24000],links=page.locator('a[href]').evaluate_all('(nodes)=>nodes.map(n=>({text:n.innerText.slice(0,160),href:n.href}))'),controls=page.locator('input,select,button').evaluate_all('(nodes)=>nodes.filter(n=>!/password|email|phone|token/i.test(n.name||n.type||"" )).map(n=>({tag:n.tagName,type:n.type,name:n.name,text:(n.innerText||n.getAttribute("aria-label")||"").slice(0,200),options:n.options?Array.from(n.options).map(o=>({value:o.value,text:o.text})):undefined}))')[:160],structured=[n.inner_text()[:60000] for n in page.locator('script[type="application/ld+json"]').all()])

def main():
 report=dict(run_id=os.environ['GITHUB_RUN_ID'],store='Barkat Meat House',pages=[])
 with sync_playwright() as p:
  browser=p.chromium.launch(headless=True)
  try:
   page=browser.new_page();response=page.goto(BASE,wait_until='domcontentloaded',timeout=60000)
   if not response or response.status>=400 or re.search(r'just a moment|attention required|captcha',page.title(),re.I):raise ValueError('Source unavailable or challenged; no bypass')
   page.wait_for_timeout(6000);home=snapshot(page);report['pages'].append(home)
   links=list(dict.fromkeys(v['href'] for v in home['links'] if (urlsplit(v['href']).hostname or '').removeprefix('www.')=='barkatmeathouse.com' and re.search(r'/(?:product|shop|menu|meat|chicken|beef|mutton)',urlsplit(v['href']).path,re.I)))
   for url in links[:3]:
    response=page.goto(url,wait_until='domcontentloaded',timeout=60000)
    if not response or response.status>=400:break
    page.wait_for_timeout(3000);report['pages'].append(snapshot(page))
  finally:browser.close()
 publish(report,branch='requested-store-reports');print('Public rendered product/navigation evidence saved')
if __name__=='__main__':main()
