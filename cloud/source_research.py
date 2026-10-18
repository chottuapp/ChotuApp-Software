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
 candidates=soup.select('main, [role=main], .page, .product-detail, .search-results')
 return str(candidates[0] if candidates else soup)[:65000]
def describe(text,url):
 soup=BeautifulSoup(text,'html.parser');links=[]
 for a in soup.find_all('a',href=True):
  u=public_url(urljoin(url,a['href']));label=a.get_text(' ',strip=True)[:90]
  if u and not re.search(r'login|account|register|logout|checkout|cart|mailto|tel:|javascript:',u,re.I) and not any(x['url']==u for x in links):links.append({'url':u,'text':label})
 return {'url':public_url(url),'page':inspect_page(text,url),'links':links[:350],'visible_html':clean_html(text)}
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
  if status==200:robots=RobotFileParser();robots.parse(body.decode('utf-8',errors='replace').splitlines())
  if status in (401,403,429,503):raise RuntimeError('Source robots request denied or limited')
  home=get('https://'+host+'/')
  if home and home.get('status')==200:
   canonical=urlsplit(home['final_url']).hostname
   # Follow real navigation only; never guess product/category API routes.
   links=[x['url'] for x in home.get('links',[]) if urlsplit(x['url']).hostname==canonical and urlsplit(x['url']).path not in ('','/')]
   categories=[u for u in links if not re.search(r'privacy|terms|contact|about|shipping|return|faq|stores?|careers|track|polic|country',u,re.I)]
   for url in categories[:2]:
    page=get(url)
    if not page or page.get('status')!=200:continue
    products=[x['url'] for x in page.get('links',[]) if urlsplit(x['url']).hostname==canonical and ('/products/' in x['url'] or re.search(r'/[^/]+\.html$',urlsplit(x['url']).path)) and x['url']!=url]
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
      for match in re.finditer(r'https?://[^\s"\x27`<>]+|/api/[^\s"\x27`<>]+|(?:graphql|baseURL|baseUrl|Search-Show|Product-Variation|Search-UpdateGrid)',text):
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
