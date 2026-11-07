"""Inspect anonymous public Mansab product responses using normal Chrome."""
import json,os,re
from urllib.parse import urlsplit,parse_qsl
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
from source_research import publish,clean_html,public_url
from urllib.robotparser import RobotFileParser
import requests
URL='https://mansabpk.com/product/charcoal-textured-2-piece-co-ord-suit-mansab'
FIELDS={'id','name','title','slug','description','price','sale_price','original_price','regular_price','discount_price','stock','stock_quantity','inventory','inventory_quantity','available','is_available','is_active','color','size','sizes','colors','variants','product_variants','product_id','sku','image_url','images','quantity','category','category_id','attributes','option1','option2','compare_at_price','data','products','product','count','status','is_on_sale','base_price','salePrice','regularPrice','stockQuantity','isActive','availableStock','value'}
MAPS={'size_stock','size_stocks','stock_by_size','sizeStock','inventory_by_size','size_inventory','variant_stock','stockBySize'}
FIELDS.update(MAPS|{'available_sizes','fabric','care_instructions','included_items','measurements','size_guide','details','fit','piece_count'})
def project(value):
 if isinstance(value,dict):return {k:({str(a):b for a,b in v.items() if isinstance(b,(int,float)) and not isinstance(b,bool)} if k in MAPS and isinstance(v,dict) else project(v)) for k,v in value.items() if k in FIELDS}
 if isinstance(value,list):return [project(v) for v in value[:150]]
 return value

def main():
 result={'run_id':os.environ['GITHUB_RUN_ID'],'source':URL,'responses':[]}
 r=requests.get('https://mansabpk.com/robots.txt',timeout=30)
 if r.status_code not in (200,404):raise ValueError('Public robots unavailable; no browser request')
 policy=RobotFileParser();policy.parse(r.text.splitlines() if r.status_code==200 else [])
 if not policy.can_fetch('*',URL):raise ValueError('Public robots disallows product')
 with sync_playwright() as p:
  browser=p.chromium.launch(executable_path='/usr/bin/google-chrome',headless=True)
  page=browser.new_page()
  def response(r):
   path=urlsplit(r.url).path
   if r.status==200 and re.search(r'products?|variants?|inventory|sizes|colors',path,re.I) and 'json' in r.headers.get('content-type',''):
    try:
     data=project(r.json())
     if len(json.dumps(data))<150000:result['responses'].append({'url':public_url(r.url),'public_query':{k:v for k,v in parse_qsl(urlsplit(r.url).query) if k in ('slug','id','category','limit','page','offset')},'product_keys':sorted(r.json()) if isinstance(r.json(),dict) else [],'data':data})
    except Exception:pass
  page.on('response',response)
  page.goto(URL,wait_until='domcontentloaded',timeout=60000)
  try:page.locator('h1').first.wait_for(timeout=25000)
  except Exception:pass
  page.wait_for_timeout(3000)
  result['title']=page.title();result['html']=clean_html(page.content());result['visible_text']=page.locator('body').inner_text()[:18000]
  result['controls']=[{'text':b.inner_text()[:100],'type':b.get_attribute('type'),'aria_pressed':b.get_attribute('aria-pressed'),'disabled':b.is_disabled()} for b in page.locator('button').all()][:70]
  browser.close()
 publish(result,branch='requested-store-reports');print('Anonymous public product evidence saved')
if __name__=='__main__':main()
