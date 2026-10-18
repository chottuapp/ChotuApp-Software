"""Publish validation outcome and resume the explicitly selected saved fetch once."""
import argparse,json,os,re,subprocess,time
from datetime import datetime,timezone
from pathlib import Path
from source_research import publish
REPO='chottuapp/ChotuApp-Software'
def stop_previous(run_id):
    if not str(run_id).isdigit():raise ValueError('Numeric previous run required')
    def state():
        result=subprocess.run(['gh','run','view',str(run_id),'--repo',REPO,'--json','status'],capture_output=True,text=True,check=True,timeout=30)
        return json.loads(result.stdout)['status']
    if state()=='completed':return
    subprocess.run(['gh','workflow','run','cloud-stop.yml','--repo',REPO,'--ref','main','-f','run_id='+str(run_id)],capture_output=True,text=True,check=True,timeout=60)
    for _ in range(12):
        time.sleep(10)
        if state()=='completed':return
    # The user requested a fresh run; stop the superseded run if graceful shutdown stalls.
    subprocess.run(['gh','run','cancel',str(run_id),'--repo',REPO],capture_output=True,text=True,check=True,timeout=60)
    for _ in range(12):
        time.sleep(5)
        if state()=='completed':return
    raise RuntimeError('Previous run is still active; fresh dispatch withheld')

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--validation',required=True);args=parser.parse_args()
    run=os.environ.get('GITHUB_RUN_ID','');sha=os.environ.get('GITHUB_SHA','')
    if not run.isdigit() or not re.fullmatch('[a-f0-9]{40}',sha):raise ValueError('Actions identity required')
    marker=json.loads((Path(__file__).parent/'fetch-update-release.json').read_text())
    if marker.get('minutes')!=300 or marker.get('auto_continue_limit')!=6 or len(marker.get('fresh_stores',[]))!=29:raise ValueError('Unexpected fresh release request')
    from runtime import validate_site
    sites=[validate_site(site,resolve=False) for site in marker['fresh_stores']]
    if any('watchcentre.pk' in site['url'] for site in sites):raise ValueError('Excluded store')
    report={'run_id':run,'source_commit':sha,'checked_utc':datetime.now(timezone.utc).isoformat(),'validation':args.validation,'fresh_store_count':len(sites),'dispatch':'not_requested'}
    if args.validation=='success':
        previous=marker.get('stop_previous_run_id')
        if previous:
            try:stop_previous(previous)
            except Exception:
                report['dispatch']='failed';report['reason']='Previous run stop could not be confirmed';publish(report,branch='fetch-update-reports');raise SystemExit(1)
            report['previous_run_stopped']=previous
        result=subprocess.run(['gh','workflow','run','cloud-fetch.yml','--repo',REPO,'--ref','main','-f','stores='+'; '.join(site['name']+' | '+site['url'] for site in sites),'-f','minutes=300','-f','save_checkpoint=true','-f','auto_continue_limit=6','-f','auto_continue_once=false'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,timeout=60)
        report['dispatch']='requested' if result.returncode==0 else 'failed'
        # Do not publish arbitrary CLI errors or credentials.
        match=re.search(r'https://github.com/chottuapp/ChotuApp-Software/actions/runs/([0-9]+)',result.stdout)
        if match:report['fetch_run_id']=match[1];report['fetch_url']=match[0]
    publish(report,branch='fetch-update-reports')
    print(json.dumps(report,indent=2))
    if args.validation!='success' or report['dispatch']=='failed':raise SystemExit(1)
if __name__=='__main__':main()
