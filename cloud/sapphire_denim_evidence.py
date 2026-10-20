"""Collect public denim selection evidence without guessing unavailable combinations."""
import sys,os,json,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import requests
from bs4 import BeautifulSoup
from urllib.robotparser import RobotFileParser
from sapphire_source_support import PublicCatalog,BASE,AGENT,inspect_page,variant_url,primary_nodes
from source_research import publish
from diagnostics import redact
session=requests.Session();session.headers['User-Agent']=AGENT
source=PublicCatalog({'S':session,'_chotu_wait':lambda:None,'_chotu_debug_request':lambda *a:None,'_chotu_debug_response':lambda *a,**k:None,'_chotu_backoff':lambda delay,*a:time.sleep(delay)},print)
report={'run_id':os.environ['GITHUB_RUN_ID'],'kind':'sapphire_denim_selection','pages':[]}
try:
 robots=source.read(BASE+'/robots.txt');source.robot=RobotFileParser();source.robot.parse(robots.text.splitlines())
 url=BASE+'/collections/western-wear/products/WDNMV0726002.html';master=inspect_page(source.read(url).text,url)
 for fit in master['fits']:
  for size in master['sizes']:
   selected=variant_url(url,dict(size,fixed_options={fit['parameter']:fit['value']}));response=source.read(selected);soup=BeautifulSoup(response.text,'html.parser');main=soup.select_one('.product-wrapper')
   item={'url':selected,'requested_fit':fit,'requested_size':size}
   try:item['parsed']=inspect_page(response.text,selected)
   except Exception as exc:item['error']=redact(str(exc))
   if main:
    item['primary_scope']=str(BeautifulSoup('<div></div>','html.parser'))
    item['controls']=[str(n) for n in primary_nodes(main,'[data-attr] input.options-select')]
    item['button']=[str(n) for n in primary_nodes(main,'button.add-to-cart[data-gtmga4data]')]
    item['pid']=main.get('data-pid');item['master']=main.get('data-master-id')
   report['pages'].append(item)
except Exception as exc:report['error']=redact(str(exc))
finally:
 source.close();session.close();publish(report,branch='laam-repair-reports')
