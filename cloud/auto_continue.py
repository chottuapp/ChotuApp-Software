"""Checkpoint continuations with an explicit chain limit and no-progress guard."""
import argparse,json,os,subprocess,tempfile,time
from pathlib import Path
from continuation_policy import budget, recoverable, integer

# User explicitly authorized one additional 300-minute run for this active run.
AUTHORIZED_EXISTING_RUNS={'38970499270'}

def run_minutes(summary):
    # Approved fresh campaign: longer segments reduce repeated restore/cache replay.
    request=json.loads((Path(__file__).parent/'audit804-release.json').read_text())
    prefix='audit804-'+str(request.get('campaign_id',''))+'-'
    if request.get('fetch_segment_minutes')==300 and str(summary.get('runner_group','')).startswith(prefix):return 300
    value=integer(summary.get('continuation_minutes',300),default=300,maximum=300)
    return value if value>=30 else 300

def eligible(run,repo,summary,console,checkpoint):
    if run.get('event')!='workflow_dispatch' or run.get('head_branch')!='main' or run.get('head_repository',{}).get('full_name')!=repo:return False
    if run.get('conclusion')=='cancelled' or not checkpoint:return False
    limit,index=budget(summary)
    authorized=(str(run.get('id')) in AUTHORIZED_EXISTING_RUNS or limit>index) and integer(summary.get('stalled_runs',0),default=2,maximum=2)<2
    timed_out=summary.get('stop_reason')=='time_budget' or ('Cloud time budget reached; saving unfinished work.' in console and not summary.get('stop_reason'))
    cooldown=summary.get('stop_reason')=='source_cooldown' and any(s.get('status')=='source_paused' for s in summary.get('stores',[]))
    ready=any(recoverable(s) and (s.get('status')!='source_paused' or float(s.get('retry_after_epoch',0) or 0)<=time.time()+900) for s in summary.get('stores',[]))
    return ready and authorized and (timed_out or cooldown) and summary.get('checkpoint')=='saved' and summary.get('status')!='complete' and any(recoverable(s) for s in summary.get('stores',[]))

def gh(*args):
    result=subprocess.run(['gh',*args],capture_output=True,text=True,check=True,timeout=180)
    return result.stdout

def current_run_context():
    identity=os.environ.get('GITHUB_RUN_ID','');repo=os.environ.get('GITHUB_REPOSITORY','')
    if not identity.isdigit() or os.environ.get('GITHUB_EVENT_NAME')!='workflow_dispatch':raise ValueError('Current main-branch dispatch identity required')
    data=Path(os.environ.get('CHOTUAPP_CLOUD_DATA','.cloud-data'))
    try:phase=json.loads((data/'fetch-phase.json').read_text())
    except (OSError,ValueError):return None,None
    if phase.get('phase')!='finished' or phase.get('checkpoint')!='saved':return None,None
    run=json.loads(gh('api','repos/'+repo+'/actions/runs/'+identity))
    if str(run.get('id'))!=identity or run.get('head_sha')!=os.environ.get('GITHUB_SHA'):raise ValueError('Current run identity does not match the checked-out release')
    summary=json.loads((data/'ANAS_DATA_FETCH'/'run-summary.json').read_text())
    return run,summary

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--current-run',action='store_true');args=parser.parse_args()
    repo=os.environ['GITHUB_REPOSITORY'];summary=None
    if args.current_run:
        run,summary=current_run_context()
        if run is None:print('No continuation: current fetch has no completed saved checkpoint.');return
    else:
        event=json.loads(Path(os.environ['GITHUB_EVENT_PATH']).read_text());run=event['workflow_run']
    identity=str(run['id'])
    if run.get('event')!='workflow_dispatch' or run.get('head_branch')!='main' or run.get('head_repository',{}).get('full_name')!=repo:
        print('No continuation: source is not a trusted main-branch dispatch.');return
    if run.get('conclusion')=='cancelled':print('No continuation: manually cancelled.');return
    artifacts=json.loads(gh('api','repos/'+repo+'/actions/runs/'+identity+'/artifacts?per_page=100')).get('artifacts',[])
    checkpoint=any(a.get('name')=='chotuapp-checkpoint' and not a.get('expired') for a in artifacts)
    if not checkpoint:print('No continuation: no downloadable checkpoint.');return
    console=''
    if summary is None:
        with tempfile.TemporaryDirectory(prefix='chotu-auto-') as tmp:
            root=Path(tmp);exports=root/'exports';logs=root/'logs'
            gh('run','download',identity,'--repo',repo,'--name','chotuapp-excel-files','--dir',str(exports))
            summary=json.loads((exports/'run-summary.json').read_text())
            if not summary.get('stop_reason'):
                gh('run','download',identity,'--repo',repo,'--name','chotuapp-live-logs','--dir',str(logs))
                console=(logs/'console-tail.txt').read_text(encoding='utf-8',errors='replace')
    if not eligible(run,repo,summary,console,checkpoint):print('No continuation: completed, stopped manually, unauthorized or not a time-budget stop.');return
    name='Automatic continuation of '+identity
    previous=json.loads(gh('run','list','--repo',repo,'--workflow','cloud-fetch.yml','--limit','100','--json','displayTitle'))
    if any(item.get('displayTitle')==name for item in previous):print('Continuation already exists; duplicate dispatch skipped.');return
    limit,index=budget(summary)
    if str(run.get('id')) in AUTHORIZED_EXISTING_RUNS and not limit:limit=1
    gh('workflow','run','cloud-fetch.yml','--repo',repo,'--ref','main','-f','runner_group='+str(summary.get('runner_group','')),'-f','resume_run_id='+identity,'-f','minutes='+str(run_minutes(summary)),'-f','save_checkpoint=true','-f','auto_continue_once=false','-f','continuation_parent='+identity,'-f','auto_continue_limit='+str(limit),'-f','continuation_index='+str(index+1),'-f','previous_progress='+str(summary.get('progress_token','')),'-f','stalled_runs='+str(summary.get('stalled_runs',0)))
    print('Submitted continuation '+str(index+1)+'/'+str(limit)+' of '+identity+'; checkpoint and progress guards remain enabled.')

if __name__=='__main__':main()
