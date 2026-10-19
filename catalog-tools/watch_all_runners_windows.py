"""One read-only live report for all active ChotuApp fetch runners."""
import argparse,concurrent.futures,json,os,re,shutil,subprocess,tempfile,time
from datetime import datetime,timezone
from pathlib import Path
REPO='chottuapp/ChotuApp-Software'

def report_age(text,now=None):
    match=re.search(r'^Updated \(UTC\):\s*(.+)$',text,re.M)
    if not match:return None
    try:
        stamp=datetime.fromisoformat(match.group(1).strip().replace('Z','+00:00'))
        if stamp.tzinfo is None:return None
        return max(0,((now or datetime.now(timezone.utc))-stamp).total_seconds())
    except ValueError:return None

def stores(text):
    section=text.partition('STORE STATUS')[2];result=[]
    for line in section.splitlines():
        if not line.strip():continue
        if not line.startswith((' ','\t')) and ': ' in line:
            name,status=line.split(': ',1)
            if status.strip() in {'done','running','pending','source_paused','blocked','failed','cancelled'}:result.append({'name':name,'status':status.strip(),'details':[]})
        elif result and ('Stage:' in line or 'tasks;' in line or 'ETA for this stage' in line):result[-1]['details'].append(line.strip())
    return result

def render(run,text,previous=None,now=None):
    now=now or datetime.now(timezone.utc);items=stores(text)
    lines=['RUN '+str(run['databaseId'])+' | '+run['status']+' | '+str(run.get('conclusion') or '')+' | '+run['displayTitle']]
    age=report_age(text,now)
    lines.append('Snapshot age: '+('unknown' if age is None else str(int(age))+'s')+(' - OLD SNAPSHOT; live log check needed' if age is not None and age>720 else ''))
    if items:lines.append('Group exports: '+str(sum(s['status']=='done' for s in items))+'/'+str(len(items)))
    else:lines.append('Store report unavailable; setup/restore may still be running.')
    for item in items:
        lines.append('  '+item['name']+': '+item['status']+(' | '+' | '.join(item['details']) if item['details'] else ''))
    signature=tuple((i['name'],i['status'],tuple(re.sub(r'; sample age .*$', '',d) for d in i['details'] if 'ETA for this stage' not in d)) for i in items)
    since=now.timestamp()
    if previous and previous[0]==signature:
        since=previous[1]
        if now.timestamp()-since>=900 and any(i['status']=='running' for i in items):lines.append('No reported stage/count change for 15+ minutes; inspect latest logs. This alone does not prove a hang.')
    return '\n'.join(lines),(signature,since)

def main():
    p=argparse.ArgumentParser();p.add_argument('--once',action='store_true');p.add_argument('--interval',type=int,default=60);args=p.parse_args()
    if not 30<=args.interval<=3600:p.error('Interval must be 30 to 3600 seconds')
    exe=shutil.which('gh') or str(Path(os.environ.get('ProgramFiles','C:/Program Files'))/'GitHub CLI'/'gh.exe')
    def gh(*parts):
        r=subprocess.run([exe,*parts],capture_output=True,text=True,timeout=45)
        if r.returncode:raise RuntimeError((r.stderr or r.stdout or 'GitHub request failed').strip()[:350])
        return r.stdout
    cache={};history={};tracked={};output=Path.home()/'Desktop'/'Cloud_All_Runners_Report.txt'
    def snapshot(run):
        identity=str(run['databaseId'])
        try:
            artifacts=json.loads(gh('api','repos/'+REPO+'/actions/runs/'+identity+'/artifacts?per_page=100')).get('artifacts',[])
            artifact=next((a for a in artifacts if a['name']=='chotuapp-live-logs' and not a.get('expired')),None)
            if not artifact:return identity,None,'Waiting for first published snapshot (setup/restore may still be active).'
            if identity in cache and cache[identity][0]==artifact['id']:return identity,cache[identity][1],None
            with tempfile.TemporaryDirectory(prefix='chotu-runner-report-') as tmp:
                gh('run','download',identity,'--repo',REPO,'--name','chotuapp-live-logs','--dir',tmp)
                path=next(Path(tmp).rglob('store-status.txt'),None)
                if path is None:return identity,None,'Published artifact has no store-status.txt yet.'
                text=path.read_text(encoding='utf-8',errors='replace');cache[identity]=(artifact['id'],text);return identity,text,None
        except (RuntimeError,subprocess.SubprocessError,OSError,ValueError,KeyError) as exc:
            saved=cache.get(identity)
            return identity,saved[1] if saved else None,'Report refresh failed (not proof the cloud stopped): '+str(exc)
    print('Combined runner monitor. Refresh '+str(args.interval)+'s. Ctrl+C closes this monitor only.',flush=True)
    try:
        while True:
            try:
                runs=json.loads(gh('run','list','--repo',REPO,'--workflow','cloud-fetch.yml','--limit','100','--json','databaseId,displayTitle,status,conclusion'))
                now=datetime.now(timezone.utc)
                for r in runs:
                    if r['status']!='completed':tracked[str(r['databaseId'])]=now.timestamp()
                visible=[r for r in runs if r['status']!='completed' or now.timestamp()-tracked.get(str(r['databaseId']),0)<600]
                lines=['CHOTUAPP ALL RUNNERS | '+now.astimezone().strftime('%Y-%m-%d %H:%M:%S %z'),'Active/queued runs: '+str(sum(r['status']!='completed' for r in runs))]
                if not visible:lines.append('No active fetch runs reported by GitHub. Recent runs: '+', '.join(str(r['databaseId'])+' '+r['status']+'/'+str(r.get('conclusion') or '') for r in runs[:3]))
                if visible:print('Checking '+str(len(visible))+' runner reports...',flush=True)
                with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
                    results=list(pool.map(snapshot,visible))
                for run,(identity,text,error) in zip(visible,results):
                    if text:
                        rendered,history[identity]=render(run,text,history.get(identity),now);lines.extend(['',rendered])
                    else:lines.extend(['','RUN '+identity+' | '+run['status']+' | '+run['displayTitle']])
                    if error:lines.append(error)
                report='\n'.join(lines);print('\n'+report+'\n',flush=True)
                if output.parent.is_dir():output.write_text(report,encoding='utf-8')
            except (RuntimeError,subprocess.SubprocessError,OSError,ValueError,KeyError) as exc:print('Status unavailable; cloud state not confirmed: '+str(exc),flush=True)
            if args.once:return
            time.sleep(args.interval)
    except KeyboardInterrupt:print('Combined monitor closed. Cloud runs continue.',flush=True)
if __name__=='__main__':main()
