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
def main():
 request=json.loads((Path(__file__).parent/'inspect-stopped-request.json').read_text());targets=request.get('run_ids') or [request['run_id']]
 if not 1<=len(targets)<=3 or not all(str(x).isdigit() for x in targets):raise ValueError('Bounded numeric targets required')
 result={'run_id':os.environ['GITHUB_RUN_ID'],'checked_utc':datetime.now(timezone.utc).isoformat(),'targets':[]}
 for rid in map(str,targets):
  record={'target':rid}
  try:
   record['state']=json.loads(gh('run','view',rid,'--repo',REPO,'--json','status,conclusion,jobs,headSha,displayTitle'))
   try:record['failed_log']=evidence(gh('run','view',rid,'--repo',REPO,'--log-failed'))
   except subprocess.CalledProcessError as exc:record['log_unavailable']=redact(exc.stderr or '')[:1500]
   artifacts=json.loads(gh('api','repos/'+REPO+'/actions/runs/'+rid+'/artifacts'))['artifacts']
   record['artifacts']=[{k:a.get(k) for k in ('name','id','expired','size_in_bytes')} for a in artifacts]
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
