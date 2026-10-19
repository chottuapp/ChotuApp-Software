"""Bounded, robots-aware official product evidence capture; never changes catalog facts."""
import concurrent.futures,hashlib,json,re,time,urllib.request,urllib.parse,urllib.robotparser
from collections import defaultdict
from datetime import datetime,timezone
from pathlib import Path
AGENT='ChotuAppRule804/1.0'
ALLOWED={'rawayat.com.pk','seran.com.pk','outfitters.com.pk','junaidjamshed.com','zellbury.com','bonanzasatrangi.com'}
class Redirect(urllib.request.HTTPRedirectHandler):
 def redirect_request(self,req,fp,code,msg,headers,newurl):
  a=urllib.parse.urlsplit(req.full_url);b=urllib.parse.urlsplit(newurl)
  if b.scheme!='https' or a.hostname.removeprefix('www.')!=b.hostname.removeprefix('www.'):raise ValueError('Unreviewed external redirect')
  return super().redirect_request(req,fp,code,msg,headers,newurl)
opener=urllib.request.build_opener(Redirect)
def get(url):
 p=urllib.parse.urlsplit(url)
 if p.scheme!='https' or p.username or p.password or p.port not in (None,443) or p.hostname.removeprefix('www.') not in ALLOWED:raise ValueError('Not an approved official product host')
 with opener.open(urllib.request.Request(url,headers={'User-Agent':AGENT}),timeout=25) as response:
  raw=response.read(2*1024*1024+1)
  if len(raw)>2*1024*1024:raise ValueError('Response exceeds 2MB capture limit')
  return raw

def host_capture(group):
 results=[];host=urllib.parse.urlsplit(group[0]['source_url']).netloc
 try:
  robots=get('https://'+host+'/robots.txt').decode('utf-8','replace');policy=urllib.robotparser.RobotFileParser();policy.parse(robots.splitlines());delay=max(1,policy.crawl_delay(AGENT) or policy.crawl_delay('*') or 1)
 except Exception as error:return [{'source_url':r['source_url'],'error':'Robots policy unavailable: '+str(error)} for r in group]
 if delay>30:return [{'source_url':r['source_url'],'error':'Crawl delay exceeds this bounded job: '+str(delay)} for r in group]
 for item in group:
  url=item['source_url'];js=url.rstrip('/')+'.js';entry={'source_url':url,'request_url':js,'checked_at_utc':datetime.now(timezone.utc).isoformat()}
  try:
   if not policy.can_fetch(AGENT,js):raise ValueError('robots.txt disallows product JSON')
   time.sleep(delay);raw=get(js);product=json.loads(raw)
   if product.get('handle')!=urllib.parse.urlsplit(url).path.rstrip('/').split('/')[-1]:raise ValueError('Product handle mismatch')
   entry.update({'response_sha256':hashlib.sha256(raw).hexdigest(),'source_product_id':product.get('id'),'title':product.get('title'),'product_type':product.get('type') or product.get('product_type'),'vendor':product.get('vendor'),'tags':product.get('tags'),'body_html':product.get('description') or product.get('body_html'),'images':product.get('images',[])[:3],'options':product.get('options')})
  except Exception as error:entry['error']=str(error)
  results.append(entry);print(url+' '+('ERROR '+entry['error'] if 'error' in entry else 'captured'),flush=True)
 return results

def main():
 root=Path('catalog-inputs/rule804-20261020-completion');jobs=json.loads((root/'jobs.json').read_text());groups=defaultdict(dict)
 for job in jobs:groups[urllib.parse.urlsplit(job['source_url']).hostname][job['source_url']]=job
 output=[]
 with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
  for result in pool.map(host_capture,[list(v.values()) for v in groups.values()]):output.extend(result)
 (root/'source-evidence.json').write_text(json.dumps({'captured_at_utc':datetime.now(timezone.utc).isoformat(),'requested_products':len(jobs),'unique_urls':len(output),'results':output},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
