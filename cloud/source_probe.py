"""Bounded public-source diagnostics. No login, cookies, rate-limit bypass or full crawl."""
import argparse,json,re,time,os,subprocess,tempfile
from pathlib import Path
from urllib.parse import urlsplit,urljoin,urlunsplit
from urllib.robotparser import RobotFileParser
from datetime import datetime,timezone
import requests
from bs4 import BeautifulSoup
HOSTS=('laam.com','pk.khaadi.com','sapphireonline.pk','outfitters.com.pk','zellbury.com')
AGENT='ChotuAppSourceDiagnostic/1.0'

def safe_url(value):
    p=urlsplit(str(value))
    if p.scheme not in ('http','https') or not p.hostname or p.username or p.password:return ''
    return urlunsplit((p.scheme,p.netloc,p.path,'',''))

def inspect_page(text,url):
    soup=BeautifulSoup(text,'html.parser');lower=text.lower();markers=[]
    for name,patterns in [('Shopify',('cdn.shopify.com','shopify.theme')),('Salesforce Commerce',('demandware','sfcc','dwfrm_')),('Magento',('magento','mage/cookies')),('Next.js',('__next_data__','/_next/')),('Nuxt',('__nuxt__','/_nuxt/')),('Webx',('webx.pk','webx ecommerce'))]:
        if any(p in lower for p in patterns):markers.append(name)
    canonical=soup.find('link',rel='canonical');scripts=[]
    for s in soup.find_all('script',src=True):
        u=safe_url(urljoin(url,s['src']))
        if u and u not in scripts:scripts.append(u)
    structured=[]
    for s in soup.find_all('script',type='application/ld+json'):
        try:data=json.loads(s.string or s.get_text())
        except (ValueError,TypeError):continue
        seq=data if isinstance(data,list) else data.get('@graph',[data]) if isinstance(data,dict) else []
        for item in seq:
            if not isinstance(item,dict) or item.get('@type') not in ('Product','ProductGroup'):continue
            p={k:item[k] for k in ('@type','name','sku') if k in item and isinstance(item[k],(str,int,float))}
            if item.get('url'):p['url']=safe_url(urljoin(url,str(item['url'])))
            offers=item.get('offers');offers=offers if isinstance(offers,list) else [offers]
            p['offers']=[{k:o[k] for k in ('@type','price','lowPrice','highPrice','priceCurrency','availability') if k in o and isinstance(o[k],(str,int,float))} for o in offers[:2] if isinstance(o,dict)]
            structured.append(p)
    state=soup.find('script',id='__NEXT_DATA__');keys=[]
    if state:
        try:
            data=json.loads(state.string or state.get_text());props=data.get('props',{}).get('pageProps',{});keys=list(props)[:30] if isinstance(props,dict) else []
        except (ValueError,TypeError,AttributeError):pass
    return {'platform_markers':markers,'canonical_url':safe_url(urljoin(url,canonical.get('href',''))) if canonical else '', 'script_urls':scripts[:20],'next_page_prop_keys':keys,'product_schema_samples':structured[:2]}

def request(session,url,host,limit):
    domain='khaadi.com' if host.endswith('khaadi.com') else host if host.endswith('.com.pk') else '.'.join(host.split('.')[-2:])
    for _ in range(5):
        p=urlsplit(url);h=(p.hostname or '').lower()
        if p.scheme!='https' or p.username or p.password or not (h==domain or h.endswith('.'+domain)):raise ValueError('Cross-domain or non-HTTPS redirect requires review')
        with session.get(url,timeout=30,allow_redirects=False,stream=True) as response:
            if response.status_code in (301,302,303,307,308):
                url=urljoin(url,response.headers.get('Location',''));time.sleep(1.5);continue
            chunks=[];size=0
            for chunk in response.iter_content(65536):
                size+=len(chunk)
                if size>limit:raise ValueError('Public response exceeds diagnostic size limit')
                chunks.append(chunk)
            return response.status_code,url,b''.join(chunks),response.headers.get('Content-Type','')
    raise ValueError('Too many public redirects')

def capture(host,folder,session=None,wait=time.sleep):
    if host not in HOSTS:raise ValueError('Unsupported diagnostic host')
    folder=Path(folder)/host;folder.mkdir(parents=True,exist_ok=True);session=session or requests.Session();session.headers.update({'User-Agent':AGENT});records=[];robots=None
    for path,filename,limit in [('/robots.txt','robots.txt',65536),('/','homepage.html',2*1024*1024),('/products.json?limit=2','products.json',1024*1024)]:
        url='https://'+host+path
        if robots is not None and not robots.can_fetch(AGENT,url):records.append({'path':path,'outcome':'robots_disallowed'});continue
        try:
            status,final,body,kind=request(session,url,host,limit);(folder/filename).write_bytes(body);record={'path':path,'status':status,'final_url':safe_url(final),'bytes':len(body),'content_type':kind}
            if path=='/robots.txt' and status==200:robots=RobotFileParser();robots.parse(body.decode('utf-8',errors='replace').splitlines())
            if path=='/' and status==200:record.update(inspect_page(body.decode('utf-8',errors='replace'),final))
            if path.startswith('/products.json') and status==200:
                try:
                    data=json.loads(body);record['json_keys']=list(data)[:20] if isinstance(data,dict) else [];record['shopify_product_count']=len(data.get('products',[])) if isinstance(data,dict) and isinstance(data.get('products'),list) else None
                except ValueError:record['outcome']='not_json'
            records.append(record)
            if status in (401,403,429,503):break
        except Exception as exc:
            records.append({'path':path,'outcome':'request_failed','error_type':type(exc).__name__});break
        wait(1.5)
    return {'host':host,'responses':records}

def publish(report,repo='.'):
    """Publish only the allowlisted public summary; raw pages remain in short-lived artifacts."""
    payload=json.dumps(report,indent=2).encode();assert len(payload)<150000
    with tempfile.TemporaryDirectory() as d:
        env=dict(os.environ,GIT_INDEX_FILE=str(Path(d)/'index'))
        def git(*args,input=None):return subprocess.run(['git',*args],cwd=repo,env=env,input=input,stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True).stdout.decode().strip()
        ref='refs/heads/source-reports';parent=None
        if git('ls-remote','--heads','origin',ref):git('fetch','--depth=1','origin',ref);parent=git('rev-parse','FETCH_HEAD');git('read-tree',parent)
        else:git('read-tree','--empty')
        blob=git('hash-object','-w','--stdin',input=payload)
        for name in ('latest.json','runs/'+report['run_id']+'.json'):git('update-index','--add','--cacheinfo','100644,'+blob+','+name)
        args=['-c','user.name=github-actions[bot]','-c','user.email=41898282+github-actions[bot]@users.noreply.github.com','commit-tree',git('write-tree')]
        if parent:args+=['-p',parent]
        commit=git(*args,input=b'Public store source diagnostic\n');git('push','origin',commit+':'+ref)

def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,default=Path('source-diagnostics'));p.add_argument('--publish',action='store_true');a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
    report={'run_id':os.environ.get('GITHUB_RUN_ID','local'),'checked_utc':datetime.now(timezone.utc).isoformat(),'stores':[capture(host,a.output) for host in HOSTS]}
    (a.output/'report.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
    if a.publish:
        if not re.fullmatch(r'\d+',report['run_id']):raise ValueError('Publishing requires an Actions run identity')
        publish(report)
if __name__=='__main__':main()
