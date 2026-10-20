"""Collect bounded, redacted original-lane failures using Actions' existing token."""
import json,os,subprocess,re,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from diagnostics import redact
from source_research import publish,public_product_state
from bs4 import BeautifulSoup,SoupStrainer
import requests,time
from urllib.robotparser import RobotFileParser
from laam_source_support import PublicCatalog,BASE
REPO='chottuapp/ChotuApp-Software'
def call(*args):
 r=subprocess.run(['gh',*args],capture_output=True,text=True,timeout=180)
 return r.returncode,r.stdout,r.stderr
report={'run_id':os.environ['GITHUB_RUN_ID'],'failures':[]}
for store,rid in [('LAAM','39410937297'),('Sapphire','39414516183')]:
 code,out,err=call('run','view',rid,'--repo',REPO,'--json','status,conclusion,jobs,headSha')
 item={'store':store,'source_run':rid,'run':json.loads(out) if not code else {'error':redact(err)}}
 code,out,err=call('run','view',rid,'--repo',REPO,'--log-failed');lines=(out or err).splitlines();selected=set()
 for i,line in enumerate(lines):
  if re.search(r'EXCEPTION|Traceback|Error:|RuntimeError|FAILED:|##\[error\]|SOURCE PAUSED|ADAPTER ERROR',line):selected.update(range(max(0,i-12),min(len(lines),i+16)))
 item['failed_log_tail']=[redact(lines[i]) for i in sorted(selected)[:320]] or [redact(line) for line in lines[-80:]]
 report['failures'].append(item)
try:
 session=requests.Session();session.headers['User-Agent']='ChotuAppCatalogRefresh'
 source=PublicCatalog({'S':session,'_chotu_wait':lambda:None,'_chotu_backoff':lambda delay,*args:time.sleep(delay),'_chotu_debug_request':lambda *args:None,'_chotu_debug_response':lambda *args,**kwargs:None},print)
 robots=source.read(BASE+'/robots.txt');source.robots=RobotFileParser();source.robots.parse(robots.text.splitlines())
 handle='1864-paradise-blue-embroidered-organza-stitched-0';page=source.read(BASE+'/products/'+handle)
 report['laam_failing_product']=[p for p in public_product_state(BeautifulSoup(page.text,'html.parser',parse_only=SoupStrainer('script'))) if p.get('handle')==handle]
 session.close();source.close()
except Exception as exc:report['laam_source_evidence_error']=redact(str(exc))
publish(report,branch='laam-repair-reports');print(json.dumps(report,indent=2))
