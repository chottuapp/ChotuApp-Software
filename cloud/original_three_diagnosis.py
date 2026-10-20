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
code,out,err=call('run','list','--repo',REPO,'--workflow','cloud-fetch.yml','--limit','100','--json','databaseId,displayTitle,status,conclusion')
runs=json.loads(out) if not code else []
report['runs']=runs
failed=[r for r in runs if int(r['databaseId'])>=39450000000 and r.get('conclusion')=='failure'][:15]
for record in failed:
 store=record['displayTitle'];rid=str(record['databaseId'])
 code,out,err=call('run','view',rid,'--repo',REPO,'--json','status,conclusion,jobs,headSha')
 item={'store':store,'source_run':rid,'run':json.loads(out) if not code else {'error':redact(err)}}
 code,out,err=call('run','view',rid,'--repo',REPO,'--log-failed');lines=(out or err).splitlines();selected=set()
 for i,line in enumerate(lines):
  if re.search(r'EXCEPTION|Traceback|Error:|RuntimeError|FAILED:|##\[error\]|SOURCE PAUSED|ADAPTER ERROR',line):selected.update(range(max(0,i-12),min(len(lines),i+16)))
 item['failed_log_tail']=[redact(lines[i]) for i in sorted(selected)][-180:]
 report['failures'].append(item)
publish(report,branch='laam-repair-reports');print(json.dumps(report,indent=2))
