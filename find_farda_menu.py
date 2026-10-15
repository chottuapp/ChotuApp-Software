"""List public navigation and ordering links; never alter ChotuApp files."""
from html import unescape
from html.parser import HTMLParser
import json
import re
from urllib.parse import urljoin,urlsplit
import requests

BASE='https://fardafoods.com/'

class Links(HTMLParser):
    def __init__(self):super().__init__();self.current=None;self.text=[];self.links=[]
    def handle_starttag(self,tag,attrs):
        attrs=dict(attrs)
        if tag=='a':self.current=attrs.get('href');self.text=[]
        for key in ('data-url','data-href'):
            if attrs.get(key):self.links.append((key,attrs[key]))
        onclick=attrs.get('onclick','')
        for url in re.findall(r'[\"\'](https?://[^\"\']+)[\"\']',onclick):self.links.append(('Button',url))
    def handle_data(self,data):
        if self.current:self.text.append(data)
    def handle_endtag(self,tag):
        if tag=='a' and self.current:
            self.links.append((' '.join(' '.join(self.text).split()),self.current));self.current=None;self.text=[]

def normalized(label,link):
    if not link or link.startswith(('#','mailto:','tel:','javascript:')):return None
    url=urljoin(BASE,unescape(link));parsed=urlsplit(url)
    if parsed.scheme not in ('https','http'):return None
    if re.search(r'(^|\.)(facebook|instagram|twitter|youtube|tiktok|wa|whatsapp)\.',parsed.hostname or ''):return None
    return re.sub(r'\s+',' ',unescape(label)).strip()[:100] or '(unlabelled)',url

def main():
    print('FARDA PUBLIC MENU LINKS — READ ONLY',flush=True)
    seen=set();found=[]
    def add(label,url):
        item=normalized(label,url)
        if item and item[1] not in seen:seen.add(item[1]);found.append(item)
    with requests.Session() as session:
        session.headers['User-Agent']='Mozilla/5.0 (compatible; ChotuAppSourceDiagnostic/1.0)'
        try:
            r=session.get(BASE,timeout=(5,10));print('Homepage HTTP:',r.status_code,flush=True);r.raise_for_status()
            parser=Links();parser.feed(r.text)
            for label,url in parser.links:add(label,url)
        except requests.RequestException as exc:print('Homepage unavailable:',type(exc).__name__,flush=True)
        try:
            r=session.get(BASE+'wp-json/wp/v2/pages?per_page=100&_fields=link,title,slug',timeout=(5,10));print('Public pages HTTP:',r.status_code,flush=True)
            data=r.json()
            if r.status_code==200 and isinstance(data,list):
                for page in data:
                    title=page.get('title') or {};title=title.get('rendered','') if isinstance(title,dict) else str(title)
                    add(re.sub('<[^>]+>',' ',title),page.get('link',''))
        except (requests.RequestException,ValueError) as exc:print('Public pages unavailable:',type(exc).__name__,flush=True)
    candidates=[item for item in found if re.search(r'menu|shop|order|product|catalog|delivery',item[0]+' '+urlsplit(item[1]).path,re.I)]
    print('MENU / SHOP / ORDER CANDIDATES:',flush=True)
    for label,url in candidates[:25]:print(label+' -> '+url,flush=True)
    if not candidates:print('No labelled menu/order link found; inspect the public navigation below.',flush=True)
    print('OTHER PUBLIC NAVIGATION:',flush=True)
    for label,url in [item for item in found if item not in candidates][:45]:print(label+' -> '+url,flush=True)
    print('END FARDA LINKS',flush=True)

if __name__=='__main__':main()
