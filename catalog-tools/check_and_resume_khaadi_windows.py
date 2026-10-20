"""Resume the verified Khaadi checkpoint once, or report its existing active lane."""
import json,os,shutil,subprocess,time,tempfile
from pathlib import Path
REPO='chottuapp/ChotuApp-Software';SOURCE='39400071124';LANE='solo-khaadi'
def main():
    gh=shutil.which('gh') or str(Path(os.environ.get('ProgramFiles','C:/Program Files'))/'GitHub CLI'/'gh.exe')
    def call(*args):
        result=subprocess.run([gh,*args],capture_output=True,text=True,timeout=180)
        if result.returncode:raise RuntimeError(result.stderr or result.stdout)
        return result.stdout
    runs=json.loads(call('run','list','--repo',REPO,'--workflow','cloud-fetch.yml','--limit','100','--json','databaseId,displayTitle,status'))
    own={str(r['databaseId']) for r in runs if r['displayTitle']=='Cloud group '+LANE}
    for _ in runs:
        added={str(r['databaseId']) for r in runs if r['displayTitle'].startswith('Automatic continuation of ') and r['displayTitle'].split()[-1] in own}
        if added<=own:break
        own.update(added)
    active=[r for r in runs if str(r['databaseId']) in own and r['status']!='completed']
    if active:
        for r in active:print('Already active; no duplicate started: https://github.com/'+REPO+'/actions/runs/'+str(r['databaseId']),flush=True)
        print('Send this output; existing fetching was not stopped.',flush=True);return
    workflow='cloud-khaadi-check.yml'
    previous={r['databaseId'] for r in json.loads(call('run','list','--repo',REPO,'--workflow',workflow,'--limit','20','--json','databaseId'))}
    print('Testing Khaadi public size pages on GitHub before resume...',flush=True)
    print(call('workflow','run',workflow,'--repo',REPO,'--ref','main'),flush=True)
    probe=None
    for _ in range(20):
        candidates=json.loads(call('run','list','--repo',REPO,'--workflow',workflow,'--limit','20','--json','databaseId'))
        fresh=[r['databaseId'] for r in candidates if r['databaseId'] not in previous]
        if len(fresh)>1:raise RuntimeError('Multiple new source checks found; no duplicate fetching dispatched')
        if fresh:probe=str(fresh[0]);break
        time.sleep(3)
    if not probe:raise RuntimeError('Source check dispatch not yet visible; fetching not started')
    print('Source check: https://github.com/'+REPO+'/actions/runs/'+probe,flush=True)
    subprocess.run([gh,'run','watch',probe,'--repo',REPO,'--exit-status'],check=True)
    with tempfile.TemporaryDirectory() as tmp:
        call('run','download',probe,'--repo',REPO,'--name','khaadi-public-route-check','--dir',tmp)
        paths=list(Path(tmp).rglob('khaadi-public-route.json'))
        if len(paths)!=1 or not json.loads(paths[0].read_text()).get('sample_verified'):raise RuntimeError('Pakistan public size route not verified; fetching not started')
    print('Cloud sample verified. Resuming saved Khaadi checkpoint.',flush=True)
    state=json.loads(call('run','view',SOURCE,'--repo',REPO,'--json','status'))
    if state['status']!='completed':raise RuntimeError('Source still running; nothing dispatched')
    artifacts=json.loads(call('api','repos/'+REPO+'/actions/runs/'+SOURCE+'/artifacts?per_page=100'))['artifacts']
    if not any(a['name']=='chotuapp-checkpoint' and not a.get('expired') for a in artifacts):raise RuntimeError('Checkpoint unavailable; no fresh fallback attempted')
    print('Checkpoint available. Starting latest main; selected queue must contain only Khaadi.',flush=True)
    print(call('workflow','run','cloud-fetch.yml','--repo',REPO,'--ref','main','-f','resume_run_id='+SOURCE,'-f','partition_resume=true','-f','stores=Khaadi | https://pk.khaadi.com','-f','runner_group='+LANE,'-f','minutes=300','-f','save_checkpoint=true','-f','auto_continue_limit=6','-f','auto_continue_once=false'),flush=True)
    print('Khaadi resume requested. Cached work retained; full catalog coverage remains unverified. Send the new run URL.',flush=True)
if __name__=='__main__':main()
