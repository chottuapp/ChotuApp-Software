"""Restore before optional browser installation; keep the supervisor from restoring twice."""
import argparse,json,os
from pathlib import Path
from cli import restore
from diagnostics import atomic_json
from resume_support import RunStore

def prepare(archive,data,source_run):
    data=Path(data).resolve()
    if not str(source_run).isdigit():raise ValueError('Resume source run must contain digits only')
    ready=data/'restore-ready.json';ready.unlink(missing_ok=True)
    restore(archive,data)
    state=RunStore(data/'saved_runs').load()
    if not state or not state.get('sites'):raise ValueError('Checkpoint has no saved store queue')
    if os.environ.get('CLOUD_PARTITION_RESUME')=='true':
        from partition_resume import partition
        from cli import parse_stores
        state=partition(data,parse_stores(os.environ.get('CLOUD_STORES','')))
    from runner_identity import validate_runner_sources
    validate_runner_sources(state,os.environ.get('CLOUD_RUNNER_GROUP',''))
    from urllib.parse import urlsplit
    def complete(site):
        output=site.get('output') or {};file=data/'ANAS_DATA_FETCH'/Path(output.get('path','')).name
        return site.get('status')=='done' and RunStore.output_valid(dict(site,output=dict(output,path=str(file))))
    needs_browser=any(not complete(site) and (urlsplit(str(site.get('url',''))).hostname or '').lower().removeprefix('www.')=='czone.com.pk' for site in state['sites'])
    atomic_json(ready,{'source_run':str(source_run),'state_id':state.get('id')})
    print('Resume checkpoint restored; '+str(sum(complete(s) for s in state['sites']))+' completed stores retained. Czone browser needed: '+str(needs_browser).lower()+'.',flush=True)
    return needs_browser

def prepared(data,source_run):
    data=Path(data)
    try:
        marker=json.loads((data/'restore-ready.json').read_text());state=RunStore(data/'saved_runs').load()
        return marker.get('source_run')==str(source_run) and bool(state) and marker.get('state_id')==state.get('id')
    except (OSError,ValueError):return False

def main():
    p=argparse.ArgumentParser();p.add_argument('--archive',type=Path,required=True);p.add_argument('--data',type=Path,required=True);a=p.parse_args()
    needs=prepare(a.archive,a.data,os.environ.get('RESUME_RUN_ID',''))
    if os.environ.get('GITHUB_ENV'):
        with open(os.environ['GITHUB_ENV'],'a') as stream:stream.write('CLOUD_NEEDS_CZONE_BROWSER='+str(needs).lower()+'\n')
if __name__=='__main__':main()
