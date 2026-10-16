"""One authorized continuation after a time-budget stop, never an endless restart loop."""
import json,os,subprocess,tempfile
from pathlib import Path

# User explicitly authorized one additional 300-minute run for this active run.
AUTHORIZED_EXISTING_RUNS={'38970499270'}

def eligible(run,repo,summary,console,checkpoint):
    if run.get('event')!='workflow_dispatch' or run.get('head_branch')!='main' or run.get('head_repository',{}).get('full_name')!=repo:return False
    if run.get('conclusion')=='cancelled' or not checkpoint:return False
    authorized=str(run.get('id')) in AUTHORIZED_EXISTING_RUNS or summary.get('auto_continue_once') is True
    timed_out=summary.get('stop_reason')=='time_budget' or ('Cloud time budget reached; saving unfinished work.' in console and not summary.get('stop_reason'))
    return authorized and timed_out and summary.get('checkpoint')=='saved' and summary.get('status')!='complete' and any(s.get('status')!='done' for s in summary.get('stores',[]))

def gh(*args):
    result=subprocess.run(['gh',*args],capture_output=True,text=True,check=True,timeout=180)
    return result.stdout

def main():
    event=json.loads(Path(os.environ['GITHUB_EVENT_PATH']).read_text());run=event['workflow_run'];repo=os.environ['GITHUB_REPOSITORY'];identity=str(run['id'])
    if run.get('event')!='workflow_dispatch' or run.get('head_branch')!='main' or run.get('head_repository',{}).get('full_name')!=repo:
        print('No continuation: source is not a trusted main-branch dispatch.');return
    if run.get('conclusion')=='cancelled':print('No continuation: manually cancelled.');return
    artifacts=json.loads(gh('api','repos/'+repo+'/actions/runs/'+identity+'/artifacts?per_page=100')).get('artifacts',[])
    checkpoint=any(a.get('name')=='chotuapp-checkpoint' and not a.get('expired') for a in artifacts)
    if not checkpoint:print('No continuation: no downloadable checkpoint.');return
    with tempfile.TemporaryDirectory(prefix='chotu-auto-') as tmp:
        root=Path(tmp);exports=root/'exports';logs=root/'logs'
        gh('run','download',identity,'--repo',repo,'--name','chotuapp-excel-files','--dir',str(exports))
        summary=json.loads((exports/'run-summary.json').read_text())
        console=''
        if not summary.get('stop_reason'):
            gh('run','download',identity,'--repo',repo,'--name','chotuapp-live-logs','--dir',str(logs))
            console=(logs/'console-tail.txt').read_text(encoding='utf-8',errors='replace')
        if not eligible(run,repo,summary,console,checkpoint):print('No continuation: completed, stopped manually, unauthorized or not a time-budget stop.');return
    name='Automatic continuation of '+identity
    previous=json.loads(gh('run','list','--repo',repo,'--workflow','cloud-fetch.yml','--limit','100','--json','displayTitle'))
    if any(item.get('displayTitle')==name for item in previous):print('Continuation already exists; duplicate dispatch skipped.');return
    gh('workflow','run','cloud-fetch.yml','--repo',repo,'--ref','main','-f','resume_run_id='+identity,'-f','minutes=300','-f','save_checkpoint=true','-f','auto_continue_once=false','-f','continuation_parent='+identity)
    print('Submitted one additional 300-minute continuation of '+identity+'. Child will not automatically chain again.')

if __name__=='__main__':main()
