"""Save and stop the one legacy fetch, then dispatch groups from its checkpoint."""
import argparse,json,os,shutil,subprocess,time
from pathlib import Path
REPO='chottuapp/ChotuApp-Software'

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--resume-run');args=parser.parse_args()
    exe=shutil.which('gh') or str(Path(os.environ.get('ProgramFiles','C:/Program Files'))/'GitHub CLI'/'gh.exe')
    def gh(*parts):return subprocess.run([exe,*parts],capture_output=True,text=True,check=True,timeout=180).stdout
    runs=json.loads(gh('run','list','--repo',REPO,'--workflow','cloud-fetch.yml','--limit','100','--json','databaseId,displayTitle,status'))
    grouped={str(r['databaseId']) for r in runs if r['displayTitle'].startswith('Cloud group ')}
    for _ in range(len(runs)):
        added={str(r['databaseId']) for r in runs if r['displayTitle'].startswith('Automatic continuation of ') and r['displayTitle'].split()[-1] in grouped}
        if added<=grouped:break
        grouped.update(added)
    active=[r for r in runs if r['status']!='completed']
    if any(str(r['databaseId']) in grouped for r in active):raise SystemExit('Grouped runners are already active. No duplicate launch attempted.')
    if len(active)>1:raise SystemExit('More than one legacy run is active. Send the run list before migration; nothing stopped.')
    if args.resume_run:
        if not args.resume_run.isdigit():raise SystemExit('Numeric parent run required')
        if active:raise SystemExit('Fetching is still active; omit --resume-run to save and stop it safely')
        source=args.resume_run
    elif active:
        source=str(active[0]['databaseId'])
        print('Saving checkpoint and stopping legacy run '+source+' ...',flush=True)
        print(gh('workflow','run','cloud-stop.yml','--repo',REPO,'--ref','main','-f','run_id='+source),flush=True)
    else:
        if not runs or str(runs[0]['databaseId']) in grouped:raise SystemExit('No legacy parent available. Nothing changed.')
        source=str(runs[0]['databaseId'])
    deadline=time.monotonic()+20*60
    while True:
        state=json.loads(gh('run','view',source,'--repo',REPO,'--json','status,conclusion'))
        if state['status']=='completed':break
        if time.monotonic()>deadline:raise SystemExit('Still saving/stopping; no new runners started. Retry later to preserve the checkpoint.')
        print('Waiting for checkpoint and final uploads: '+source+' ('+state['status']+')',flush=True);time.sleep(15)
    artifacts=json.loads(gh('api','repos/'+REPO+'/actions/runs/'+source+'/artifacts?per_page=100')).get('artifacts',[])
    if not any(a['name']=='chotuapp-checkpoint' and not a.get('expired') for a in artifacts):raise SystemExit('No saved checkpoint on '+source+'. No fresh restart or duplicate work attempted; send this output.')
    print('Checkpoint ready. Starting groups of at most five unfinished stores...',flush=True)
    print(gh('workflow','run','cloud-fetch-groups.yml','--repo',REPO,'--ref','main','-f','resume_run_id='+source),flush=True)
    print('GROUP DISPATCH REQUESTED. Existing completed stores stay in parent '+source+'. Send the workflow URL above to inspect the new runner IDs.',flush=True)
if __name__=='__main__':main()
