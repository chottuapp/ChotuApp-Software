"""Read-only public Czone source discovery; never reads local app/user data."""
import json,re,sys
from urllib.parse import urljoin,urlsplit
import requests
from bs4 import BeautifulSoup

BASE='https://www.czone.com.pk/'

def inspect(session,url):
    response=session.get(url,timeout=(15,40))
    print('\nCHECK:',url,'\nHTTP:',response.status_code,'FINAL:',response.url,'TYPE:',response.headers.get('Content-Type',''))
    if response.status_code!=200:
        print('SOURCE ERROR: public page could not be inspected.');return []
    soup=BeautifulSoup(response.text,'html.parser')
    print('TITLE:',soup.title.get_text(' ',strip=True) if soup.title else '(none)')
    for node in soup.select('script[type="application/ld+json"]'):
        print('STRUCTURED DATA:',node.get_text()[:18000])
    links=[]
    for a in soup.select('a[href]'):
        target=urljoin(response.url,a['href'])
        if (urlsplit(target).hostname or '').lower() not in ('czone.com.pk','www.czone.com.pk'):continue
        if re.search(r'_(?:pid|cid|cat|categ|pc|pn)[-=]|/products|/laptops',target,re.I):
            pair=(a.get_text(' ',strip=True)[:160],target)
            if pair not in links:links.append(pair)
    print('CATALOG LINKS:',json.dumps(links[:45],ensure_ascii=True))
    # Webx uses both legacy -p.ID.aspx and extensionless product URLs.
    for node in soup.select('script[type="application/ld+json"]'):
        try:
            data=json.loads(node.get_text())
            for item in data.get('mainEntity',{}).get('itemListElement',[]):
                target=urljoin(response.url,item.get('url',''))
                if urlsplit(target).hostname in ('www.czone.com.pk','czone.com.pk'):
                    pair=(item.get('name',''),target)
                    if pair not in links:links.append(pair)
        except (ValueError,AttributeError,TypeError):pass
    paging=[str(a) for a in soup.select('a[href]') if re.search(r'page|next|pagination',str(a),re.I)]
    print('PAGINATION MARKUP:', '\n'.join(paging)[-14000:])
    # Only public visible text and markup around product attributes, never cookies/headers/forms.
    for tag in soup(['script','style','form','nav','footer','header']):tag.decompose()
    text=soup.get_text('\n',strip=True)
    print('PUBLIC PAGE TEXT:',text[:20000])
    candidates=[]
    for node in soup.find_all(attrs={'id':True}):
        if re.search(r'price|stock|avail|product|spec|detail|paging',node.get('id',''),re.I):
            fragment=str(node)
            if len(fragment)<18000:candidates.append(fragment)
    print('PRODUCT MARKUP:', '\n'.join(candidates)[:28000])
    return links

def main():
    print('CZONE SOURCE DIAGNOSTIC — READ ONLY\nNo application, templates, Excel or saved-run files are read or changed.')
    with requests.Session() as session:
        session.headers['User-Agent']='Mozilla/5.0 (Windows NT 10.0; Win64; x64) ChotuApp-Source-Diagnostic/1.0'
        links=inspect(session,BASE+'products')
        products=[u for _,u in links if re.search(r'(?:_pid[-=]|-p\.\d+\.aspx)',u,re.I)]
        if products:inspect(session,products[0])
        else:
            listings=[u for _,u in links if re.search(r'_(?:cid|cat|categ|pc)[-=]|/products|/laptops',u,re.I)]
            if listings:
                found=inspect(session,listings[0])
                products=[u for _,u in found if re.search(r'(?:_pid[-=]|-p\.\d+\.aspx)',u,re.I)]
                if products:inspect(session,products[0])
    print('\nEND CZONE DIAGNOSTIC')

if __name__=='__main__':
    try:main()
    except Exception as exc:
        print('DIAGNOSTIC FAILED:',type(exc).__name__,str(exc));sys.exit(1)
