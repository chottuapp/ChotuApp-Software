"""Inspect Farda's public catalog sources; do not alter the installed app."""
import json
import re
import time
from urllib.parse import urljoin,urlsplit
import requests

BASE='https://fardafoods.com'

def public_sample(data):
    if isinstance(data,dict) and isinstance(data.get('products'),list):items=data['products']
    elif isinstance(data,list):items=data
    else:return {'json_type':type(data).__name__,'keys':list(data)[:15] if isinstance(data,dict) else []}
    if not items:return {'records':0}
    p=items[0]
    if not isinstance(p,dict):return {'records':len(items),'record_type':type(p).__name__}
    result={'records':len(items),'keys':list(p),'sample':{}}
    for k in ('id','name','title','type','status','permalink','slug','on_sale','is_in_stock','is_purchasable','has_options','prices','price','regular_price','sale_price','stock_status','attributes','variations','variants'):
        if k in p:result['sample'][k]=p[k]
    for k in ('images','description','short_description','body_html'):
        if k in p:
            value=p[k]
            if isinstance(value,str):value=re.sub('<[^>]+>',' ',value)[:600]
            if isinstance(value,list):value=value[:2]
            result['sample'][k]=value
    return result


def probe(session,url):
    print('CHECK:',url,flush=True)
    try:
        r=session.get(url,timeout=(5,8));print('HTTP:',r.status_code,'FINAL:',r.url,'TYPE:',r.headers.get('Content-Type',''),flush=True)
        # Only public catalog evidence: no cookies, credentials or private app data.
        try:
            data=r.json()
            if r.status_code==200:print('CATALOG:',json.dumps(public_sample(data),ensure_ascii=True),flush=True)
            elif isinstance(data,dict):print('ERROR CODE:',str(data.get('code',''))[:100],flush=True)
        except ValueError:
            text=r.text
            print('PLATFORM MARKERS:',json.dumps({key:bool(re.search(pattern,text,re.I)) for key,pattern in {
                'shopify':r'cdn\.shopify\.com|Shopify\.shop|shopify-section',
                'wordpress':r'wp-content/|wp-includes/|api\.w\.org',
                'woocommerce':r'woocommerce|wc-block|wc/store',
                'wix':r'wixstatic\.com|wix-site',
            }.items()}),flush=True)
            title=re.search(r'<title[^>]*>(.*?)</title>',text,re.S|re.I)
            if title:print('PAGE TITLE:',re.sub(r'\s+',' ',title[1])[:180],flush=True)
            # Public product URLs help identify a custom storefront route.
            links=[]
            for link in re.findall(r'href=[\"\']([^\"\']+)',text,re.I):
                full=urljoin(r.url,link)
                if urlsplit(full).hostname not in ('fardafoods.com','www.fardafoods.com'):continue
                if re.search(r'/(?:product|products|shop)/',urlsplit(full).path) and full not in links:links.append(full)
                if len(links)==3:break
            print('PUBLIC PRODUCT LINKS:',json.dumps(links),flush=True)
    except requests.RequestException as exc:print('REQUEST FAILED:',type(exc).__name__,flush=True)


def main():
    print('FARDA SOURCE DIAGNOSTIC — READ ONLY',flush=True)
    print('No app, Excel, templates or saved-run files are read or changed.',flush=True)
    with requests.Session() as session:
        session.headers.update({'User-Agent':'Mozilla/5.0 (compatible; ChotuAppSourceDiagnostic/1.0)','Accept':'application/json,text/html;q=0.9,*/*;q=0.8'})
        for suffix in ('/','/products.json?limit=1&page=1','/wp-json/wc/store/v1/products?per_page=1','/wp-json/'):
            probe(session,BASE+suffix);time.sleep(.5)
    print('END FARDA DIAGNOSTIC',flush=True)

if __name__=='__main__':main()
