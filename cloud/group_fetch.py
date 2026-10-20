"""Dispatch at most three distinct storefronts per independently resumable runner."""
import json,os,re,subprocess,tempfile
from pathlib import Path
from urllib.parse import urlsplit

def host(site):return (urlsplit(str(site['url'])).hostname or '').lower().removeprefix('www.')
def groups(sites,completed=()):
    from runtime import validate_site
    cleaned=[validate_site(s,resolve=False) for s in sites]
    if not 1<=len(cleaned)<=30:raise ValueError('Select 1 to 30 stores')
    if len({host(s) for s in cleaned})!=len(cleaned):raise ValueError('A website must appear in exactly one group')
    if len({s['name'].casefold() for s in cleaned})!=len(cleaned):raise ValueError('Store names must be distinct')
    known={s['name'] for s in cleaned};completed=set(completed)
    if not completed<=known:raise ValueError('Saved stores do not match the supplied store list')
    remaining=[s for s in cleaned if s['name'] not in completed]
    return [remaining[i:i+3] for i in range(0,len(remaining),3)]

def gh(*args):return subprocess.run(['gh',*args],capture_output=True,text=True,check=True,timeout=600).stdout

def main():
    from cli import parse_stores
    repo=os.environ['GITHUB_REPOSITORY'];identity=os.environ['GITHUB_RUN_ID'];source=os.environ.get('RESUME_RUN_ID','').strip()
    if not identity.isdigit() or (source and not source.isdigit()):raise ValueError('Numeric run IDs required')
    # A single dispatcher is serialized by its workflow. Existing standalone/group runs must save and stop first.
    runs=json.loads(gh('run','list','--repo',repo,'--workflow','cloud-fetch.yml','--limit','100','--json','displayTitle,status,databaseId'))
    label=('fresh26-' if os.environ.get('CLOUD_FRESH_EXCLUDING_THREE')=='true' else 'batch-')+identity
    prefix='Cloud group '+label+'-'
    own={str(r['databaseId']) for r in runs if r['displayTitle'].startswith(prefix)}
    for _ in range(len(runs)):
        added={str(r['databaseId']) for r in runs if (m:=re.fullmatch(r'Automatic continuation of (\d+)',r['displayTitle'])) and m.group(1) in own}
        if added<=own:break
        own.update(added)
    foreign=[r for r in runs if r['status']!='completed' and str(r['databaseId']) not in own]
    if os.environ.get('CLOUD_FRESH_EXCLUDING_THREE')=='true':
        excluded={str(r['databaseId']) for r in runs if r['displayTitle'] in ('Cloud group solo-laam','Cloud group solo-khaadi','Cloud group solo-sapphire')}
        for _ in runs:
            more={str(r['databaseId']) for r in runs if r['displayTitle'].startswith('Automatic continuation of ') and r['displayTitle'].split()[-1] in excluded}
            if more<=excluded:break
            excluded.update(more)
        foreign=[r for r in foreign if str(r['databaseId']) not in excluded]
    if foreign:raise ValueError('Save and stop existing fetching before repartitioning. Active run IDs: '+', '.join(str(r['databaseId']) for r in foreign))
    text=os.environ.get('CLOUD_STORES','').strip();completed=[]
    if source:
        run=json.loads(gh('api','repos/'+repo+'/actions/runs/'+source))
        if run.get('status')!='completed':raise ValueError('Resume parent must finish saving its checkpoint before grouping')
        artifacts=json.loads(gh('api','repos/'+repo+'/actions/runs/'+source+'/artifacts?per_page=100'))
        if not any(x['name']=='chotuapp-checkpoint' and not x.get('expired') for x in artifacts.get('artifacts',[])):raise ValueError('Parent has no saved checkpoint; nothing dispatched')
        with tempfile.TemporaryDirectory() as temp:
            gh('run','download',source,'--repo',repo,'--name','chotuapp-excel-files','--dir',temp)
            summary=json.loads((Path(temp)/'run-summary.json').read_text())
            completed=[s['name'] for s in summary['stores'] if s.get('status')=='done' and s.get('file') and (Path(temp)/Path(s['file']).name).is_file()]
        registry=json.loads((Path(__file__).parent/'fetch-update-release.json').read_text())['fresh_stores']
        names={s['name'] for s in summary['stores']}
        sites=parse_stores(text) if text else [s for s in registry if s['name'] in names]
        if {s['name'] for s in sites}!=names:raise ValueError('Supply the exact saved store list for this custom parent')
    else:
        sites=parse_stores(text) if text else json.loads((Path(__file__).parent/'fetch-update-release.json').read_text())['fresh_stores']
    if os.environ.get('CLOUD_FRESH_EXCLUDING_THREE')=='true':
        if source:raise ValueError('Fresh batch must start without a resume parent')
        sites=[s for s in sites if host(s) not in {'laam.com','khaadi.com','pk.khaadi.com','sapphireonline.pk','pk.sapphireonline.pk'}]
        if len(sites)!=26:raise ValueError('Expected exactly 26 registered fresh stores after excluding LAAM, Khaadi and Sapphire')
    plan=groups(sites,completed)
    report={'source_run':source,'completed_retained_in_parent':completed,'groups':[]}
    for index,stores in enumerate(plan,1):
        lane=label+'-'+str(index);title='Cloud group '+lane
        item={'runner_group':lane,'stores':stores,'status':'already_dispatched' if any(r['displayTitle']==title for r in runs) else 'pending'};report['groups'].append(item)
        if item['status']=='pending':
            gh('workflow','run','cloud-fetch.yml','--repo',repo,'--ref','main','-f','stores='+json.dumps(stores,separators=(',',':')),'-f','runner_group='+lane,'-f','resume_run_id='+source,'-f','partition_resume='+str(bool(source)).lower(),'-f','minutes=300','-f','save_checkpoint=true','-f','auto_continue_limit=6','-f','auto_continue_once=false')
            item['status']='dispatched'
        Path('fetch-group-plan.json').write_text(json.dumps(report,indent=2))
        print(title+': '+', '.join(s['name'] for s in stores)+' — '+item['status'],flush=True)
    Path('fetch-group-plan.json').write_text(json.dumps(report,indent=2))
    if os.environ.get('GITHUB_STEP_SUMMARY'):
        with open(os.environ['GITHUB_STEP_SUMMARY'],'a') as f:f.write('## Three-store runner groups\n\n'+str(len(completed))+' completed stores retained in parent; '+str(len(plan))+' runner groups dispatched.\n\n'+ '\n'.join('- '+r['runner_group']+': '+', '.join(s['name'] for s in r['stores']) for r in report['groups']))
    if not plan:print('All saved stores are complete; no duplicate work dispatched.')
if __name__=='__main__':main()
