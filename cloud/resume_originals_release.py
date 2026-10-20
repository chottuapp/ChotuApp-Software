"""Resume explicitly selected original checkpoints after regression/source validation."""
import json,os,subprocess,time
from pathlib import Path
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
        if any(r['status']!='completed' and str(r['databaseId']) in ids for r in runs):report['sources'].append({'name':site['name'],'status':'already_active'});continue
        artifacts=json.loads(gh('api','repos/'+REPO+'/actions/runs/'+site['parent']+'/artifacts?per_page=100'))['artifacts']
        if not any(a['name']=='chotuapp-checkpoint' and not a.get('expired') for a in artifacts):report['sources'].append({'name':site['name'],'status':'checkpoint_unavailable'});continue
        if site['name']=='Sapphire':
            from sapphire_probe import main as probe
            if probe()!=0:report['sources'].append({'name':site['name'],'status':'source_check_failed'});continue
        gh('workflow','run','cloud-fetch.yml','--repo',REPO,'--ref','main','-f','resume_run_id='+site['parent'],'-f','partition_resume=true','-f','runner_group='+site['group'],'-f','stores='+site['name']+' | '+site['url'],'-f','minutes=300','-f','save_checkpoint=true','-f','auto_continue_limit=6','-f','auto_continue_once=false')
        record={'name':site['name'],'status':'resume_requested','parent':site['parent']}
        for _ in range(10):
            recent=json.loads(gh('run','list','--repo',REPO,'--workflow','cloud-fetch.yml','--limit','30','--json','databaseId,displayTitle,status'))
            new=[r for r in recent if str(r['databaseId']) not in ids and r['displayTitle']=='Cloud group '+site['group']]
            if new:record['run_id']=str(new[0]['databaseId']);record['run_status']=new[0]['status'];break
            time.sleep(3)
        report['sources'].append(record)
    publish(report,branch='fetch-update-reports');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
