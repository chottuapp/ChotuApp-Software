"""Resume the verified Sapphire checkpoint once, or report its existing active lane."""
import json,os,shutil,subprocess
from pathlib import Path
REPO='chottuapp/ChotuApp-Software';SOURCE='39406356796';LANE='solo-sapphire'
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
    state=json.loads(call('run','view',SOURCE,'--repo',REPO,'--json','status'))
    if state['status']!='completed':raise RuntimeError('Source still running; nothing dispatched')
    artifacts=json.loads(call('api','repos/'+REPO+'/actions/runs/'+SOURCE+'/artifacts?per_page=100'))['artifacts']
    if not any(a['name']=='chotuapp-checkpoint' and not a.get('expired') for a in artifacts):raise RuntimeError('Checkpoint unavailable; no fresh fallback attempted')
    print('Checkpoint available. Starting latest main; selected queue must contain only Sapphire.',flush=True)
    print(call('workflow','run','cloud-fetch.yml','--repo',REPO,'--ref','main','-f','resume_run_id='+SOURCE,'-f','partition_resume=true','-f','stores=Sapphire | https://sapphireonline.pk','-f','runner_group='+LANE,'-f','minutes=300','-f','save_checkpoint=true','-f','auto_continue_limit=6','-f','auto_continue_once=false'),flush=True)
    print('Sapphire resume requested. Cached work retained; full catalog coverage remains unverified. Send the new run URL.',flush=True)
if __name__=='__main__':main()
