"""Bounded public storefront fixtures for adapter diagnosis; no authentication or full crawl."""
import json,re,time,os,subprocess,tempfile
from pathlib import Path
from urllib.parse import urlsplit,urljoin,urlunsplit,parse_qsl,urlencode
from urllib.robotparser import RobotFileParser
from datetime import datetime,timezone
import requests
from bs4 import BeautifulSoup,Comment
from source_probe import request,inspect_page
HOSTS=('laam.com','pk.khaadi.com','sapphireonline.pk')
AGENT='ChotuAppSourceDiagnostic/1.0'
PUBLIC_QUERY={'pid','cid','start','sz','page','pageSize','count','limit','offset','lang','locale','country','currency','cgid','format','color','size','sort','sort_by','srule'}
def public_url(value):
 p=urlsplit(str(value))
 if p.scheme not in ('https','http') or not p.hostname or p.username or p.password:return ''
 query=[(k,v) for k,v in parse_qsl(p.query) if k in PUBLIC_QUERY or k.startswith('dwvar_')]
 return urlunsplit((p.scheme,p.netloc,p.path,urlencode(query),''))
def clean_html(text):
 soup=BeautifulSoup(text,'html.parser')
 for tag in list(soup.find_all(['script','style','svg','noscript','iframe','input'])):tag.decompose()
 for node in soup.find_all(string=lambda s:isinstance(s,Comment)):node.extract()
 for tag in soup.find_all(True):
  for key in list(tag.attrs):
   if re.search('token|secret|password|key|email|phone',key,re.I):del tag.attrs[key]
   elif key in ('href','src','action','data-url','data-href'):
    value=str(tag.attrs[key]);tag.attrs[key]=public_url(value) if value.startswith(('http://','https://')) else value.split('?')[0]
 # Preserve product/variation/cart-free markup, with bounded public snippets.
 candidate=soup.select_one('main') or soup.select_one('[role=main]') or soup.select_one('.product-detail') or soup.select_one('.search-results') or soup.select_one('#maincontent')
 return str(candidate if candidate else soup)[:80000]
def public_product_state(soup):
    state=soup.find('script',id='__NUXT_DATA__')
    if state is None:return []
    try:flat=json.loads(state.string or state.get_text())
    except (ValueError,TypeError):return []
    if not isinstance(flat,list):return []
    def decode(index,seen=frozenset(),depth=0):
        if not isinstance(index,int) or isinstance(index,bool):return index
        if index<0 or index>=len(flat) or index in seen or depth>18:return None
        value=flat[index];seen=seen|{index}
        if isinstance(value,dict):return {k:decode(v,seen,depth+1) for k,v in value.items() if not re.search('token|secret|password|authorization|email|phone|session|cookie|address',k,re.I)}
        if isinstance(value,list):
            if value and isinstance(value[0],str) and value[0] in ('Ref','ShallowRef','Reactive','ShallowReactive'):return decode(value[1],seen,depth+1) if len(value)>1 else None
            return [decode(v,seen,depth+1) for v in value[:300]]
        return value
    result=[]
    for item in flat:
        if not isinstance(item,dict):continue
        # Only decoded objects with product identity and explicit commercial fields.
        keys=set(item)
        if keys.intersection(('variants','variant_groups','product_variants','options')) and keys.intersection(('title','name','handle','slug','product_id','id')):
            obj={k:decode(v) for k,v in item.items() if not re.search('token|secret|password|authorization|email|phone|session|cookie|address',k,re.I)}
            payload=json.dumps(obj,ensure_ascii=True)
            if len(payload)<90000:result.append(obj)
        if len(result)>=8:break
    return result

def controller_clues(soup,url):
    urls=[];clues=[]
    for script in soup.find_all('script'):
        text=script.string or script.get_text()
        for match in re.finditer(r'(?:Product|Country|Locale|Sites?)-[A-Za-z]+',text):
            snippet=text[max(0,match.start()-160):match.end()+220]
            if not re.search('token|secret|password|authorization|api.?key|bearer|email|phone',snippet,re.I):clues.append(snippet[:400])
        for match in re.finditer(r'https?://[^\s"\x27<>]+|/on/demandware.store/[^\s"\x27<>]+',text):
            value=match.group(0)
            if re.search(r'(?:Product|Country|Locale)-',value):
                u=public_url(urljoin(url,value))
                if u and u not in urls:urls.append(u)
    for tag in soup.find_all(True):
        for key,value in tag.attrs.items():
            if key.startswith('data-') and isinstance(value,str) and re.search(r'(?:Product|Country|Locale)-',value):
                u=public_url(urljoin(url,value))
                if u and u not in urls:urls.append(u)
    return urls[:20],clues[:30]

def describe(text,url):
 soup=BeautifulSoup(text,'html.parser');links=[]
 for a in soup.find_all('a',href=True):
  u=public_url(urljoin(url,a['href']));label=a.get_text(' ',strip=True)[:90]
  if u and not re.search(r'login|account|register|logout|checkout|cart|mailto|tel:|javascript:',u,re.I) and not any(x['url']==u for x in links):links.append({'url':u,'text':label})
 product_links=[]
 for a in soup.select('.product-tile a[href], .product[data-pid] a[href], .product-item a[href]'):
  u=public_url(urljoin(url,a['href']))
  if u and u not in product_links and '/products/' in u:product_links.append(u)
 locale_controls=[str(t)[:2000] for t in soup.select('select[name*=country],select[id*=country],a[data-country],form[action*=Country],a[href*="pk.khaadi"]')][:10]
 controllers,clues=controller_clues(soup,url)
 return {'url':public_url(url),'public_controller_urls':controllers,'public_route_clues':clues,'page':inspect_page(text,url),'product_links':product_links[:30],'locale_controls':locale_controls,'links':links[:500],'visible_html':clean_html(text),'public_product_state':public_product_state(soup),'module_preloads':[public_url(urljoin(url,t['href'])) for t in soup.select('link[rel=modulepreload][href]')][:15]}
def inspect(host):
 session=requests.Session();session.headers['User-Agent']=AGENT;records=[];robots=None;home=None
 def get(url):
  nonlocal robots
  if robots is not None and not robots.can_fetch(AGENT,url):return None
  status,final,body,kind=request(session,url,host,5*1024**2);time.sleep(1.5)
  record={'requested':public_url(url),'status':status,'final_url':public_url(final),'bytes':len(body),'content_type':kind}
  if status==200 and 'html' in kind:record.update(describe(body.decode('utf-8',errors='replace'),final))
  elif status==200 and 'json' in kind:
   try:
    value=json.loads(body);record['json_keys']=list(value)[:50] if isinstance(value,dict) else []
   except ValueError:pass
  records.append(record)
  if status in (401,403,429,503):raise RuntimeError('Source unavailable or limited; diagnostic stopped')
  return record
 try:
  status,final,body,kind=request(session,'https://'+host+'/robots.txt',host,65536)
  if status==200:
   robot_text=body.decode('utf-8',errors='replace');robots=RobotFileParser();robots.parse(robot_text.splitlines());records.append({'sitemaps':re.findall(r'(?im)^Sitemap:\s*(https://\S+)',robot_text)[:12]})
  if status in (401,403,429,503):raise RuntimeError('Source robots request denied or limited')
  # Read one declared sitemap and one product child to establish actual catalog routes.
  from xml.etree import ElementTree as ET
  maps=list(dict.fromkeys(re.findall(r'(?im)^Sitemap:\s*(https://\S+)',robot_text))) if status==200 else []
  for map_url in maps[:1]:
   def sitemap_info(url):
    status,final,body,kind=request(session,url,host,5*1024**2);time.sleep(1.5)
    if status!=200:return []
    tree=ET.fromstring(body);locs=[e.text.strip() for e in tree.iter() if e.tag.rsplit('}',1)[-1]=='loc' and e.text]
    records.append({'sitemap_url':public_url(final),'sitemap_type':tree.tag.rsplit('}',1)[-1],'url_count':len(locs),'sample_urls':[public_url(u) for u in locs[:8]]})
    return locs if tree.tag.rsplit('}',1)[-1]=='sitemapindex' else []
   children=sitemap_info(map_url)
   if children:
    child=next((u for u in children if 'product' in u.lower()),children[0]);sitemap_info(child)
  home=get('https://'+host+'/')
  if home and home.get('status')==200:
   canonical=urlsplit(home['final_url']).hostname
   # Follow real navigation only; never guess product/category API routes.
   if host=='pk.khaadi.com' and canonical!='pk.khaadi.com':
    records.append({'outcome':'pakistan_locale_unverified','redirect_host':canonical})
    for record in list(records):
     if record.get('sitemap_type')=='urlset':
      products=[u for u in record['sample_urls'] if urlsplit(u).hostname=='pk.khaadi.com' and not urlsplit(u).path.endswith('.xml')]
      for product in products[:1]:get(product)
    return {'host':host,'responses':records}
   links=[x['url'] for x in home.get('links',[]) if urlsplit(x['url']).hostname==canonical and urlsplit(x['url']).path not in ('','/')]
   categories=[u for u in links if not re.search(r'privacy|terms|contact|about|shipping|return|faq|stores?|careers|track|polic|country',u,re.I)]
   category_links=[u for u in categories if '/collections/' in u or re.search(r'/(?:new-in|women|men|kids)(?:/|$)',urlsplit(u).path)]
   if category_links:categories=category_links
   for url in categories[:2]:
    page=get(url)
    if not page or page.get('status')!=200:continue
    products=page.get('product_links',[]) or [x['url'] for x in page.get('links',[]) if urlsplit(x['url']).hostname==canonical and '/products/' in x['url'] and x['url']!=url]
    for product in list(dict.fromkeys(products))[:2]:get(product)
   # Inspect one actual first-party application script, extracting only public route clues.
   scripts=home.get('page',{}).get('script_urls',[])
   script=next((u for u in scripts if ('/_nuxt/' in u and urlsplit(u).hostname=='cdn.octane.store') or ('/js/main.js' in u and urlsplit(u).hostname==canonical)),None)
   if script and (robots is None or urlsplit(script).hostname!=canonical or robots.can_fetch(AGENT,script)):
    with session.get(script,timeout=30,stream=True,allow_redirects=False) as response:
     if response.status_code==200:
      chunks=[];size=0
      for part in response.iter_content(65536):
       size+=len(part)
       if size>3*1024**2:raise ValueError('App script exceeds diagnostic limit')
       chunks.append(part)
      text=b''.join(chunks).decode('utf-8',errors='replace');snippets=[]
      for match in re.finditer(r'https?://[^\s"\x27`<>]+|/api/[^\s"\x27`<>]+|(?:graphql|baseURL|baseUrl|Search-Show|Product-[A-Za-z]+|Country-[A-Za-z]+|Locale-[A-Za-z]+|Search-UpdateGrid|/products/|/variants/|api.octane|api.laam)',text):
       snippet=text[max(0,match.start()-100):match.end()+180]
       if not re.search('token|secret|password|authorization|api.?key|bearer|email|phone',snippet,re.I):snippets.append(snippet[:450])
       if len(snippets)>=70:break
      records.append({'public_script':public_url(script),'bytes':size,'route_clues':snippets})
 except Exception as exc:records.append({'outcome':'diagnostic_stopped','error_type':type(exc).__name__})
 finally:session.close()
 return {'host':host,'responses':records}
def publish(data):
 payload=json.dumps(data,ensure_ascii=True,indent=2).encode()
 if len(payload)>2*1024**2:raise ValueError('Research report exceeds bounded public fixture size')
 with tempfile.TemporaryDirectory() as tmp:
  env=dict(os.environ,GIT_INDEX_FILE=str(Path(tmp)/'index'))
  def git(*args,input=None):return subprocess.run(['git',*args],input=input,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True).stdout.decode().strip()
  ref='refs/heads/source-research';parent=None
  if git('ls-remote','--heads','origin',ref):git('fetch','--depth=1','origin',ref);parent=git('rev-parse','FETCH_HEAD');git('read-tree',parent)
  else:git('read-tree','--empty')
  blob=git('hash-object','-w','--stdin',input=payload)
  for name in ('latest.json','runs/'+data['run_id']+'.json'):git('update-index','--add','--cacheinfo','100644,'+blob+','+name)
  args=['-c','user.name=github-actions[bot]','-c','user.email=41898282+github-actions[bot]@users.noreply.github.com','commit-tree',git('write-tree')]
  if parent:args+=['-p',parent]
  sha=git(*args,input=b'Public sanitized storefront adapter fixtures\n');git('push','origin',sha+':'+ref)
def main():
 run=os.environ.get('GITHUB_RUN_ID','')
 if not run.isdigit():raise ValueError('Research publication requires an Actions run identity')
 data={'run_id':run,'checked_utc':datetime.now(timezone.utc).isoformat(),'sources':[inspect(h) for h in HOSTS]};publish(data)
 print('Sanitized public source fixtures published; application fetching not started.')
if __name__=='__main__':main()
