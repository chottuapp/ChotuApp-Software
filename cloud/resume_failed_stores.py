"""Owner-authorized saved continuation after reviewed LAAM and runner-transport failures."""
import json,os,re,subprocess,time
from pathlib import Path
from datetime import datetime,timezone
from diagnostics import redact
from source_research import publish
from runner_status import select_runs
REPO='chottuapp/ChotuApp-Software';CAMPAIGN='fresh804-20261021-a26dcd86'
def gh(*a):return subprocess.run(['gh',*a],capture_output=True,text=True,check=True,timeout=180).stdout
def checkpoint_parent(rid):
 checked=[]
 for _ in range(64):
  run=json.loads(gh('run','view',rid,'--repo',REPO,'--json','databaseId,status,displayTitle,conclusion'))
  if run['status']!='completed':raise ValueError('Source runner is still active; refusing a duplicate')
  artifacts=json.loads(gh('api','repos/'+REPO+'/actions/runs/'+rid+'/artifacts'))['artifacts'];checked.append(rid)
  if any(a['name']=='chotuapp-checkpoint' and not a.get('expired') for a in artifacts):return rid,checked
  parent=re.fullmatch(r'Automatic continuation of (\d+)',run['displayTitle'])
  if not parent:raise ValueError('No available checkpoint in completed continuation ancestry')
  rid=parent[1]
 raise ValueError('Checkpoint ancestry bound reached')
def main():
 request=json.loads(Path('cloud/resume-failed-stores-request.json').read_text())
 expected=request['stores']
 templates={'Gul Ahmed':{'url':'https://www.gulahmedshop.com','group':'audit804-'+CAMPAIGN+'-7-gul-ahmed','old_group':'audit804-'+CAMPAIGN+'-7','minutes':90},'LAAM':{'url':'https://laam.com','group':'audit804-'+CAMPAIGN+'-6-laam','old_group':'audit804-'+CAMPAIGN+'-6-laam','minutes':90}}
 if not 1<=len(expected)<=2 or len({s.get('name') for s in expected})!=len(expected):raise ValueError('Unreviewed recovery scope')
 for site in expected:
  template=templates.get(site.get('name'))
  if template is None or not str(site.get('failed_run','')).isdigit() or {k:site.get(k) for k in template}!=template or set(site)!={'name','failed_run',*template}:raise ValueError('Unreviewed recovery request')
 report={'run_id':os.environ['GITHUB_RUN_ID'],'checked_utc':datetime.now(timezone.utc).isoformat(),'stores':[]}
 def save():publish(report,branch='laam-repair-reports')
 save()
 for site in expected:
  record={'store':site['name'],'failed_run':site['failed_run'],'group':site['group']};report['stores'].append(record)
  try:
   recent=json.loads(gh('run','list','--repo',REPO,'--workflow','cloud-fetch.yml','--limit','100','--json','databaseId,displayTitle,status,conclusion'));lanes=select_runs(recent,CAMPAIGN)
   present=[r for r in lanes if r['lane'] in (site['group'],site['old_group'])]
   if any(r['status']!='completed' or int(r['databaseId'])>int(site['failed_run']) for r in present):record.update(status='newer_or_active_lane_retained',runs=present);save();continue
   if not any(str(r['databaseId'])==str(site['failed_run']) for r in present):raise ValueError('Failed source is outside the approved campaign lane')
   try:
    parent,checked=checkpoint_parent(site['failed_run']);record.update(checkpoint_parent=parent,checked_ancestry=checked)
   except ValueError as exc:
    if site['name']!='Gul Ahmed' or request.get('allow_fresh_gul_ahmed') is not True or str(exc)!='No available checkpoint in completed continuation ancestry':raise
    parent=None;record.update(recovery_mode='owner_authorized_fresh_after_missing_checkpoint',checkpoint_parent=None)

   if site['name']=='LAAM':
    import requests
    from bs4 import BeautifulSoup
    from urllib.robotparser import RobotFileParser
    import laam_source_support as source
    reader=source.PublicCatalog({'S':requests.Session(),'_chotu_wait':lambda:None,'_chotu_backoff':lambda n,r:time.sleep(n),'_chotu_debug_request':lambda *a:None,'_chotu_debug_response':lambda *a,**k:None},lambda _:None)
    robot=reader.read(source.BASE+'/robots.txt');reader.robots=RobotFileParser();reader.robots.parse(robot.text.splitlines());page=reader.read(source.BASE+'/products/airah-3')
    product=source.product_state(BeautifulSoup(page.text,'html.parser'),'airah-3',clothing_only=True,active_only=True,in_stock_only=True)
    record['live_adapter_check']={'product':product['handle'],'variants':len(product['variants']),'options':[d['name'] for d in product['options']],'status':'pass'}
   resume_fields=['-f','resume_run_id='+parent,'-f','partition_resume=true'] if parent else []
   output=gh('workflow','run','cloud-fetch.yml','--repo',REPO,'--ref','main',*resume_fields,'-f','runner_group='+site['group'],'-f','stores='+site['name']+' | '+site['url'],'-f','minutes='+str(site['minutes']),'-f','save_checkpoint=true','-f','auto_continue_limit=48','-f','auto_continue_once=false')
   record.update(status='saved_resume_requested' if parent else 'owner_authorized_fresh_requested',dispatch=output,minutes=site['minutes'])
  except Exception as exc:record.update(status='recovery_held',error=redact(str(exc))[:1800])
  save()
if __name__=='__main__':main()
