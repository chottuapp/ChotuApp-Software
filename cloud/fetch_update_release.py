"""Publish validation outcome and resume the explicitly selected saved fetch once."""
import argparse,json,os,re,subprocess
from datetime import datetime,timezone
from pathlib import Path
from source_research import publish
REPO='chottuapp/ChotuApp-Software'
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
        result=subprocess.run(['gh','workflow','run','cloud-fetch.yml','--repo',REPO,'--ref','main','-f','stores='+'; '.join(site['name']+' | '+site['url'] for site in sites),'-f','minutes=300','-f','save_checkpoint=true','-f','auto_continue_limit=6','-f','auto_continue_once=false'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,timeout=60)
        report['dispatch']='requested' if result.returncode==0 else 'failed'
        # Do not publish arbitrary CLI errors or credentials.
        match=re.search(r'https://github.com/chottuapp/ChotuApp-Software/actions/runs/([0-9]+)',result.stdout)
        if match:report['fetch_run_id']=match[1];report['fetch_url']=match[0]
    publish(report,branch='fetch-update-reports')
    print(json.dumps(report,indent=2))
    if args.validation!='success' or report['dispatch']=='failed':raise SystemExit(1)
if __name__=='__main__':main()
