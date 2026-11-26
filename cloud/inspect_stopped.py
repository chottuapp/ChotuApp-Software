"""Bounded credential-redacted failure evidence; no checkpoint extraction or worker mutation."""
import json,os,subprocess,tempfile,re
from pathlib import Path
from datetime import datetime,timezone
from diagnostics import redact
from source_research import publish
REPO='chottuapp/ChotuApp-Software'
def gh(*args):return subprocess.run(['gh',*args],capture_output=True,text=True,check=True,timeout=180).stdout
def evidence(text):
 lines=text.splitlines();indices=set()
 for i,line in enumerate(lines):
  if re.search(r'Traceback|(?:Error|Exception):|FAILED:|SOURCE PAUSED|SOURCE BLOCKED|exit code|No continuation:|RUN SUMMARY|Killed|out of memory',line,re.I):indices.update(range(max(0,i-7),min(len(lines),i+12)))
 return '\n'.join(redact(lines[i]) for i in sorted(indices))[-65000:]
def checkpoint_product(rid,request,run):
 import sqlite3,zipfile,zlib
 from download_checkpoint import download
 if run.get('status')!='completed' or not re.fullmatch(r'Cloud group audit804-[a-z0-9-]+',run.get('displayTitle','')):raise ValueError('Expected a stopped fresh-group checkpoint')
 store=request['store'];ident=str(request['product_id'])
 registry=json.loads(Path('cloud/fetch-update-release.json').read_text())['fresh_stores']
 site=next((row for row in registry if row['name']==store),None)
 if not site or not ident.isdigit():raise ValueError('Invalid checkpoint product request')
 from locked_store_rules import owner_paused
 if owner_paused(store,site['url']):raise ValueError('Owner-paused checkpoint scope')
 from urllib.parse import urlsplit
 url=site['url'].rstrip('/')+'/wp-json/wc/store/v1/products/'+ident
 with tempfile.TemporaryDirectory() as tmp:
  folder=Path(tmp);download(rid,REPO,folder/'download',attempts=2,deadline_seconds=180)
  archives=list((folder/'download').rglob('checkpoint.zip'))
  if len(archives)!=1:raise ValueError('Expected one intact checkpoint zip')
  matches=[]
  with zipfile.ZipFile(archives[0]) as archive:
   entries=[file for file in archive.infolist() if re.fullmatch(r'saved_runs/[a-zA-Z0-9_-]+/\d+/api\.sqlite3',file.filename)]
   if len(entries)>3 or sum(file.file_size for file in entries)>128*1024*1024:raise ValueError('Checkpoint evidence bound exceeded')
   for file in entries:
    database=folder/'checkpoint-api.sqlite3';database.write_bytes(archive.read(file))
    with sqlite3.connect(database.as_uri()+'?mode=ro',uri=True) as db:
     row=db.execute('SELECT payload FROM responses WHERE url=?',(url,)).fetchone()
    if row:matches.append(json.loads(zlib.decompress(row[0])))
   if len(matches)!=1:raise ValueError('Exact cached product response unavailable')
   raw=matches[0]
   permalink=raw.get('permalink','')
   parsed=urlsplit(permalink)
   if str(raw.get('id'))!=ident or parsed.scheme!='https' or parsed.netloc!=urlsplit(url).netloc or parsed.query or parsed.fragment:raise ValueError('Cached product identity mismatch')
   facts={key:raw.get(key) for key in ('id','name','permalink','type','prices','is_purchasable','is_in_stock','has_options','variations','attributes')}
   pages=[file for file in archive.infolist() if re.fullmatch(r'saved_runs/[a-zA-Z0-9_-]+/\d+/pages\.sqlite3',file.filename)]
   if len(pages)>3 or sum(file.file_size for file in pages)>768*1024*1024:raise ValueError('Saved page evidence bound exceeded')
   from resume_support import ResponseCache
   from bs4 import BeautifulSoup
   facts['saved_public_page_found']=False
   facts['saved_public_page_variants']=[]
   for file in pages:
    database=folder/'checkpoint-pages.sqlite3';database.write_bytes(archive.read(file))
    cache=ResponseCache(database)
    try:
     response=cache.get(permalink) or cache.get(permalink.rstrip('/'))
     if response is None or response.url.rstrip('/')!=permalink.rstrip('/'):continue
     soup=BeautifulSoup(response.text,'html.parser')
     canonical=soup.select_one('link[rel=canonical][href]')
     if not canonical or canonical['href'].rstrip('/')!=permalink.rstrip('/'):continue
     facts['saved_public_page_found']=True
     for form in soup.select('form.variations_form[data-product_id][data-product_variations]'):
      if form['data-product_id']!=ident:continue
      variants=json.loads(form['data-product_variations'])
      if isinstance(variants,list):
       facts['saved_public_page_variants'].extend({key:v.get(key) for key in ('variation_id','attributes','sku','display_price','display_regular_price','is_in_stock','is_purchasable')} for v in variants[:100])
    finally:cache.close()
   return facts

def main():
 request=json.loads((Path(__file__).parent/'inspect-stopped-request.json').read_text())
 if os.environ.get('SOURCE_INSPECT_RUNS'):
  request={'run_ids':[v.strip() for v in os.environ['SOURCE_INSPECT_RUNS'].split(',')]}
 targets=request.get('run_ids') or [request['run_id']]
 if not 1<=len(targets)<=3 or not all(str(x).isdigit() for x in targets):raise ValueError('Bounded numeric targets required')
 result={'run_id':os.environ['GITHUB_RUN_ID'],'checked_utc':datetime.now(timezone.utc).isoformat(),'targets':[]}
 for rid in map(str,targets):
  record={'target':rid}
  try:
   record['state']=json.loads(gh('run','view',rid,'--repo',REPO,'--json','status,conclusion,jobs,headSha,displayTitle'))
   if request.get('checkpoint_product'):
    record['checkpoint_product']=checkpoint_product(rid,request['checkpoint_product'],record['state'])
   try:record['failed_log']=evidence(gh('run','view',rid,'--repo',REPO,'--log-failed'))
   except subprocess.CalledProcessError as exc:record['log_unavailable']=redact(exc.stderr or '')[:1500]
   artifacts=json.loads(gh('api','repos/'+REPO+'/actions/runs/'+rid+'/artifacts'))['artifacts']
   record['artifacts']=[{k:a.get(k) for k in ('name','id','expired','size_in_bytes')} for a in artifacts]
   if request.get('include_summary') is True:
    with tempfile.TemporaryDirectory() as folder:
     gh('run','download',rid,'--repo',REPO,'--name','chotuapp-excel-files','--dir',folder)
     files=list(Path(folder).rglob('run-summary.json'))
     if len(files)==1:
      raw=json.loads(files[0].read_text());record['summary']={k:raw.get(k) for k in ('runner_group','status','stop_reason','checkpoint','auto_continue_limit','continuation_index','stalled_runs')}
      record['summary']['stores']=[{k:s.get(k) for k in ('name','status','products')} for s in raw.get('stores',[])]
    from resume_failed_stores import checkpoint_parent
    try:parent,checked=checkpoint_parent(rid);record['available_checkpoint_ancestor']={'run_id':parent,'checked':checked}
    except ValueError as exc:record['checkpoint_ancestor_error']=redact(str(exc))
   record['annotations']=[]
   for job in record['state'].get('jobs',[]):
    if job.get('conclusion')!='failure':continue
    detail=json.loads(gh('api','repos/'+REPO+'/actions/jobs/'+str(job['databaseId'])))
    check=detail.get('check_run_url','')
    if check.startswith('https://api.github.com/repos/'+REPO+'/check-runs/'):
     items=json.loads(gh('api',check.removeprefix('https://api.github.com/')+'/annotations'))
     record['annotations'] += [{'level':a.get('annotation_level'),'message':redact(a.get('message',''))[:4500]} for a in items[:15]]

   if any(a['name']=='chotuapp-live-logs' and not a.get('expired') for a in artifacts):
    with tempfile.TemporaryDirectory() as folder:
     gh('run','download',rid,'--repo',REPO,'--name','chotuapp-live-logs','--dir',folder)
     for name in ('console-tail.txt','store-status.txt','fetch-log.txt'):
      files=list(Path(folder).rglob(name))
      if files:record[name]='\n'.join(redact(l) for l in files[0].read_text(errors='replace').splitlines()[-180:])[-26000:]
  except Exception as exc:record['diagnostic_error']=redact(str(exc))[:1000]
  result['targets'].append(record)
 if re.fullmatch(r'[a-z0-9-]{1,120}',str(request.get('public_laam_handle',''))):
  handle=request['public_laam_handle']
  try:
   import requests,time
   import laam_source_support as source
   from bs4 import BeautifulSoup
   from urllib.robotparser import RobotFileParser
   from unittest.mock import patch
   reader=source.PublicCatalog({'S':requests.Session(),'_chotu_wait':lambda:None,'_chotu_backoff':lambda seconds,reason:time.sleep(seconds),'_chotu_debug_request':lambda *a:None,'_chotu_debug_response':lambda *a,**k:None},lambda _:None)
   robots=reader.read(source.BASE+'/robots.txt');reader.robots=RobotFileParser();reader.robots.parse(robots.text.splitlines())
   page=reader.read(source.BASE+'/products/'+handle)
   def capture(raw,handle,**kwargs):
    return {k:raw.get(k) for k in ('id','handle','title','status','stock_status','node_l2','node_l3','options','media','images','image','featured_image')} | {'variants':[{k:v.get(k) for k in ('id','shopify_id','title','option1','option2','option3','price','compare_at_price','stock_status','inventory_quantity')} for v in raw.get('variants',[])]}
   with patch.object(source,'normalize',side_effect=capture):result['laam_public_variant_evidence']=source.product_state(BeautifulSoup(page.text,'html.parser'),handle,clothing_only=True,active_only=True)
  except Exception as exc:result['laam_probe_error']=redact(str(exc))[:1200]
 publish(result,branch='stopped-fetch-reports')
if __name__=='__main__':main()
