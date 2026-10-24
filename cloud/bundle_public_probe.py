"""Inspect visible, anonymous bundle pages; no accounts, cookies or hidden APIs exported."""
import asyncio,json,os
from pathlib import Path
from urllib.robotparser import RobotFileParser
import requests
from playwright.async_api import async_playwright
from source_research import publish
URLS=['https://bonanzasatrangi.com/products/two-of-a-kind-deal','https://bonanzasatrangi.com/products/wedding-glow-up-bundle']
async def main():
 response=requests.get('https://bonanzasatrangi.com/robots.txt',timeout=30);response.raise_for_status();robots=RobotFileParser();robots.parse(response.text.splitlines());results=[]
 async with async_playwright() as p:
  browser=await p.chromium.launch(headless=True)
  for url in URLS:
   record={'source_url':url}
   if not robots.can_fetch('ChotuAppCatalogRefresh',url):record['error']='Public robots policy disallows product page';results.append(record);continue
   page=await browser.new_page()
   try:
    reply=await page.goto(url,wait_until='domcontentloaded',timeout=45000)
    await page.wait_for_timeout(12000)
    record['http_status']=reply.status if reply else None;record['final_url']=page.url.split('?')[0]
    root=page.locator('main').first
    if await root.count()==0:root=page.locator('body')
    record['visible_text']=(await root.inner_text())[:18000]
    record['title']=await page.title()
    record['visible_bundle_widgets']=await page.locator('[class*="bundle"], [id*="bundle"]').evaluate_all('(nodes)=>nodes.filter(n=>n.getBoundingClientRect().width && n.getBoundingClientRect().height).slice(0,12).map(n=>n.innerText.slice(0,6000))')
   except Exception as exc:record['error']=type(exc).__name__
   finally:await page.close()
   results.append(record)
  await browser.close()
 from datetime import datetime,timezone
 publish({'run_id':os.environ['GITHUB_RUN_ID'],'checked_utc':datetime.now(timezone.utc).isoformat(),'results':results,'scope':'Visible anonymous public-page text only; no bundle contents inferred.'},branch='audit804-bundle-evidence')
if __name__=='__main__':asyncio.run(main())
