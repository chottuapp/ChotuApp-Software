"""Resume only the two authorized saved lanes after a tested published repair."""
import json,os,re,subprocess,tempfile
from pathlib import Path
from auto_continue import run_minutes
from resume_failed_stores import checkpoint_parent
from continuation_policy import budget
REPO='chottuapp/ChotuApp-Software'
def gh(*args):return subprocess.run(['gh',*args],capture_output=True,text=True,check=True,timeout=180).stdout

def descendants(runs,root):
    selected={str(root)}
    for _ in runs:
        more={str(r['databaseId']) for r in runs if r.get('displayTitle','').startswith('Automatic continuation of ') and r['displayTitle'].split()[-1] in selected}
        if more<=selected:break
        selected.update(more)
    return [r for r in runs if str(r['databaseId']) in selected]

def may_recover(run,summary,release,checkpoint=True):
    if run.get('event')!='workflow_dispatch' or run.get('head_branch')!='main' or run.get('head_repository',{}).get('full_name')!=REPO:return False
    if summary.get('stop_reason')=='stop_requested' or summary.get('status')=='complete' or summary.get('checkpoint')!='saved':return False
    if run.get('conclusion') in ('cancelled','success') or run.get('status')!='completed' or not checkpoint:return False
    limit,index=budget(summary)
    return (summary.get('stop_reason') not in ('time_budget','source_cooldown') and limit>index and summary.get('stalled_runs',0)<2 and run.get('head_sha')!=release and any(s.get('status') in ('failed','blocked') for s in summary.get('stores',[])))

def host_interrupted(run):
    if run.get('conclusion')=='timed_out':return True
    jobs=json.loads(gh('api','repos/'+REPO+'/actions/runs/'+str(run['id'])+'/jobs?per_page=100')).get('jobs',[])
    for job in jobs:
        if job.get('conclusion')!='failure':continue
        check=job.get('check_run_url','');prefix='https://api.github.com/repos/'+REPO+'/check-runs/'
        if not check.startswith(prefix):continue
        annotations=json.loads(gh('api',check.removeprefix('https://api.github.com/')+'/annotations'))
        if any('hosted runner lost communication with the server' in str(a.get('message','')).lower() for a in annotations):return True
    return False

def transport_recoverable(summary,checked):
    limit,index=budget(summary)
    return (len(checked)<=3 and summary.get('checkpoint')=='saved' and summary.get('stop_reason')!='stop_requested'
            and summary.get('status')!='complete' and limit>index and summary.get('stalled_runs',0)<2)

def reviewed_adapter_changed(run,lane,root=Path(__file__).resolve().parents[1]):
    import hashlib
    head=run.get('head_sha','')
    if not re.fullmatch('[a-f0-9]{40}',head):return False
    names=['main.py']+(['laam_source_support.py'] if lane['name']=='LAAM' else [])
    for name in names:
        previous=json.loads(gh('api','repos/'+REPO+'/contents/'+name+'?ref='+head))
        content=(root/name).read_bytes();current=hashlib.sha1(b'blob '+str(len(content)).encode()+b'\0'+content).hexdigest()
        if previous.get('sha')!=current:return True
    return False

def main():
    marker=json.loads((Path(__file__).parent/'recovery-release.json').read_text());release=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
    if marker.get('schema')!=1 or not re.fullmatch('[a-f0-9]{40}',release):raise ValueError('Reviewed software commit required')
    runs=json.loads(gh('run','list','--repo',REPO,'--workflow','cloud-fetch.yml','--limit','100','--json','databaseId,displayTitle,status,conclusion,headSha'))
    for lane in marker['cloud_lanes']:
        if lane.get('enabled') is False:print(lane['group']+': source repair pending; unchanged');continue
        roots={str(lane['root_run_id'])}|{str(r['databaseId']) for r in runs if r.get('displayTitle')=='Cloud group '+lane['group'] and int(r['databaseId'])>=int(lane['root_run_id'])}
        identities={str(r['databaseId']) for root in roots for r in descendants(runs,root)}
        chain=[r for r in runs if str(r['databaseId']) in identities]
        if not chain or any(r['status']!='completed' for r in chain):print(lane['group']+': active or not found; unchanged');continue
        latest=chain[0];identity=str(latest['databaseId']);run=json.loads(gh('api','repos/'+REPO+'/actions/runs/'+identity))
        if run.get('event')!='workflow_dispatch' or run.get('head_branch')!='main' or run.get('head_repository',{}).get('full_name')!=REPO:continue
        # A separately resumed same lane is also active: never start a competing worker.
        if any(r['status']!='completed' and r.get('displayTitle')=='Cloud group '+lane['group'] for r in runs):continue
        artifacts=json.loads(gh('api','repos/'+REPO+'/actions/runs/'+identity+'/artifacts?per_page=100'))['artifacts']
        resume_identity=identity;transport=False;checked=[]
        if not any(a['name']=='chotuapp-checkpoint' and not a.get('expired') for a in artifacts):
            if not host_interrupted(run):print(identity+': no usable checkpoint; source/adapter failure requires review');continue
            try:resume_identity,checked=checkpoint_parent(identity)
            except ValueError:print(identity+': no intact saved ancestor; no fresh fetch started');continue
            if resume_identity not in identities:print(identity+': checkpoint outside approved lane');continue
            transport=True
        if any(r.get('displayTitle')=='Automatic continuation of '+identity for r in runs):continue
        with tempfile.TemporaryDirectory() as tmp:
            gh('run','download',resume_identity,'--repo',REPO,'--name','chotuapp-excel-files','--dir',tmp)
            paths=list(Path(tmp).rglob('run-summary.json'))
            if len(paths)!=1:continue
            summary=json.loads(paths[0].read_text())
        if summary.get('runner_group')!=lane['group'] or {s.get('name') for s in summary.get('stores',[])}!={lane['name']}:print(identity+': source identity mismatch; unchanged');continue
        if not (transport_recoverable(summary,checked) if transport else may_recover(run,summary,release)):print(identity+': waiting, stopped, complete or budget exhausted');continue
        limit,index=budget(summary)
        if transport:index=max(index,len(chain)-1)
        if index>=limit:print(identity+': recovery chain budget exhausted');continue
        gh('workflow','run','cloud-fetch.yml','--repo',REPO,'--ref','main','-f','resume_run_id='+resume_identity,'-f','partition_resume=true','-f','stores='+lane['name']+' | '+lane['url'],'-f','runner_group='+lane['group'],'-f','minutes='+str(run_minutes(summary)),'-f','save_checkpoint=true','-f','auto_continue_limit='+str(limit),'-f','continuation_index='+str(index+1),'-f','continuation_parent='+identity,'-f','previous_progress='+str(summary.get('progress_token','')),'-f','stalled_runs='+str(summary.get('stalled_runs',0)))
        print(lane['group']+': checkpoint resume dispatched after tested release; parent '+identity)
if __name__=='__main__':main()
