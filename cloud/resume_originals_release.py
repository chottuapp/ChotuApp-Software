"""Resume explicitly selected original checkpoints after regression/source validation."""
import json,os,subprocess,time,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from source_research import publish
from runner_identity import validate_runner_sources
REPO='chottuapp/ChotuApp-Software'
def gh(*args):return subprocess.run(['gh',*args],capture_output=True,text=True,check=True,timeout=180).stdout

def main():
    marker=json.loads((Path(__file__).parent/'originals-resume-release.json').read_text());report={'run_id':os.environ['GITHUB_RUN_ID'],'sources':[]}
    for site in marker['sources']:
        validate_runner_sources({'sites':[{'name':site['name'],'url':site['url']}]},site['group'])
        runs=json.loads(gh('run','list','--repo',REPO,'--workflow','cloud-fetch.yml','--limit','100','--json','databaseId,displayTitle,status'))
        ids={str(r['databaseId']) for r in runs if r['displayTitle']=='Cloud group '+site['group']}
        for _ in runs:
            more={str(r['databaseId']) for r in runs if r['displayTitle'].startswith('Automatic continuation of ') and r['displayTitle'].split()[-1] in ids}
            if more<=ids:break
            ids.update(more)
        if site.get('observe_only'):
            selected=[r for r in runs if str(r['databaseId']) in ids]
            report['sources'].append({'name':site['name'],'status':'observed','run_id':str(selected[0]['databaseId']) if selected else None});continue
        if any(r['status']!='completed' and str(r['databaseId']) in ids for r in runs):
            current=next(r for r in runs if r['status']!='completed' and str(r['databaseId']) in ids)
            report['sources'].append({'name':site['name'],'status':'already_active','run_id':str(current['databaseId'])});continue
        artifacts=json.loads(gh('api','repos/'+REPO+'/actions/runs/'+site['parent']+'/artifacts?per_page=100'))['artifacts']
        if not any(a['name']=='chotuapp-checkpoint' and not a.get('expired') for a in artifacts):report['sources'].append({'name':site['name'],'status':'checkpoint_unavailable'});continue
        if site['name']=='Sapphire':
            from sapphire_probe import main as probe
            if probe()!=0:report['sources'].append({'name':site['name'],'status':'source_check_failed'});continue
        if site['name']=='LAAM':
            import requests
            from urllib.robotparser import RobotFileParser
            from bs4 import BeautifulSoup,SoupStrainer
            from laam_source_support import PublicCatalog,product_state,ConfirmedOutOfStock,BASE
            session=requests.Session();session.headers['User-Agent']='ChotuAppCatalogRefresh'
            source=PublicCatalog({'S':session,'_chotu_wait':lambda:None,'_chotu_backoff':lambda delay,*args:time.sleep(delay),'_chotu_debug_request':lambda *a:None,'_chotu_debug_response':lambda *a,**k:None},print)
            robot=source.read(BASE+'/robots.txt');source.robots=RobotFileParser();source.robots.parse(robot.text.splitlines());handle='1864-paradise-blue-embroidered-organza-stitched-0';page=source.read(BASE+'/products/'+handle)
            try:product_state(BeautifulSoup(page.text,'html.parser',parse_only=SoupStrainer('script')),handle)
            except ConfirmedOutOfStock:print('LAAM LIVE SAMPLE: confirmed empty zero-stock product safely excluded; no variants invented.')
            finally:source.close();session.close()
        gh('workflow','run','cloud-fetch.yml','--repo',REPO,'--ref','main','-f','resume_run_id='+site['parent'],'-f','partition_resume=true','-f','runner_group='+site['group'],'-f','stores='+site['name']+' | '+site['url'],'-f','minutes=300','-f','save_checkpoint=true','-f','auto_continue_limit=6','-f','auto_continue_once=false')
        record={'name':site['name'],'status':'resume_requested','parent':site['parent']}
        for _ in range(10):
            recent=json.loads(gh('run','list','--repo',REPO,'--workflow','cloud-fetch.yml','--limit','30','--json','databaseId,displayTitle,status'))
            new=[r for r in recent if str(r['databaseId']) not in ids and r['displayTitle']=='Cloud group '+site['group']]
            if new:record['run_id']=str(new[0]['databaseId']);record['run_status']=new[0]['status'];break
            time.sleep(3)
        report['sources'].append(record)
    from diagnostics import redact
    import tempfile
    for record in report['sources']:
        rid=record.get('run_id')
        if not rid:continue
        for attempt in range(6):
            with tempfile.TemporaryDirectory() as tmp:
                result=subprocess.run(['gh','run','download',rid,'--repo',REPO,'--name','chotuapp-live-logs','--dir',tmp],capture_output=True,text=True,timeout=120)
                paths=list(Path(tmp).rglob('store-status.txt'))
                if result.returncode==0 and paths:record['snapshot']=redact(paths[0].read_text(encoding='utf-8',errors='replace')[-14000:]);break
            status=json.loads(gh('run','view',rid,'--repo',REPO,'--json','status,conclusion'));record['current_run']=status
            if status['status']=='completed':
                failed=subprocess.run(['gh','run','view',rid,'--repo',REPO,'--log-failed'],capture_output=True,text=True,timeout=120)
                lines=failed.stdout.splitlines();record['error_context']=[redact(l) for l in lines if any(w in l for w in ('EXCEPTION','Error:','FAILED:','SOURCE BLOCKED','SOURCE PAUSED','##[error]'))][:30];break
            time.sleep(10)
    publish(report,branch='fetch-update-reports');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
