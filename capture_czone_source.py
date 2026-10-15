"""Capture public, unauthenticated storefront markup to verify Webx pagination.
No local app, configuration, exports, browser profile or saved run is read.
"""
import json,re,sys,zipfile
from pathlib import Path
from urllib.parse import urljoin,urlsplit
import requests
from bs4 import BeautifulSoup

BASE='https://www.czone.com.pk/'
MAX_BODY=8*1024*1024

def fetch(session,url):
    with session.get(url,timeout=(15,45),stream=True) as response:
        response.raise_for_status()
        parts=[];length=0
        for chunk in response.iter_content(65536):
            length+=len(chunk)
            if length>MAX_BODY:raise RuntimeError('Public source exceeds capture size limit: '+url)
            parts.append(chunk)
        return b''.join(parts),response.url,response.headers.get('Content-Type','')

def main():
    target=Path.home()/'Desktop'/'Czone_Source.zip'
    if target.exists():
        from datetime import datetime
        target=target.with_name('Czone_Source_'+datetime.now().strftime('%Y%m%d_%H%M%S')+'.zip')
    records=[];scripts=[];pages=[]
    print('CZONE PUBLIC SOURCE CAPTURE — READ ONLY')
    print('Reads only public website responses; does not change the application or saved work.')
    with requests.Session() as session,zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED) as archive:
        session.headers['User-Agent']='Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
        def save(url,name):
            data,final,kind=fetch(session,url)
            archive.writestr(name,data)
            records.append({'file':name,'url':url,'final_url':final,'type':kind,'bytes':len(data)})
            print('Captured:',name,len(data),'bytes')
            return data
        listing=save(BASE+'products','catalog.html')
        soup=BeautifulSoup(listing,'html.parser')
        for node in soup.select('script[type="application/ld+json"]'):
            try:
                obj=json.loads(node.get_text())
                for item in obj.get('mainEntity',{}).get('itemListElement',[]):
                    url=urljoin(BASE,item.get('url',''))
                    if urlsplit(url).hostname in ('www.czone.com.pk','czone.com.pk') and url not in pages:pages.append(url)
            except (ValueError,AttributeError,TypeError):pass
        if not pages:raise RuntimeError('No structured catalog product URLs found; capture retained for review.')
        # Two source products provide a check against accidentally parsing a recommendation price.
        for i,url in enumerate(pages[:2],1):
            p=urlsplit(url);url='https://www.czone.com.pk'+p.path+('?' + p.query if p.query else '')
            html=save(url,'product_'+str(i)+'.html')
            doc=BeautifulSoup(html,'html.parser')
            for tag in doc.select('script[src]'):
                script=urljoin(url,tag['src'])
                if script not in scripts:scripts.append(script)
        for tag in soup.select('script[src]'):
            script=urljoin(BASE,tag['src'])
            if script not in scripts:scripts.append(script)
        # Public storefront libraries only; skip analytics, trackers and advertising scripts.
        candidates=[u for u in scripts if (urlsplit(u).hostname or '').endswith(('webx.pk','czone.com.pk')) and not re.search(r'analytics|gtag|pixel|facebook|clarity',u,re.I)]
        for i,url in enumerate(candidates[:18],1):
            try:save(url,'scripts/script_'+str(i)+'.js')
            except requests.RequestException as exc:records.append({'url':url,'error':type(exc).__name__})
        for endpoint in ('robots.txt','sitemap.xml'):
            try:save(BASE+endpoint,endpoint)
            except requests.RequestException as exc:records.append({'url':BASE+endpoint,'error':type(exc).__name__})
        archive.writestr('manifest.json',json.dumps(records,indent=2))
    print('SOURCE ZIP SAVED:',target)
    print('Upload this ZIP to the chat so pagination and exact product selectors can be verified.')

if __name__=='__main__':
    try:main()
    except Exception as exc:
        print('CAPTURE STOPPED:',type(exc).__name__,str(exc));sys.exit(1)
