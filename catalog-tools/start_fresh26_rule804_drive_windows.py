"""Dispatch 26 fresh cloud stores, then copy only checked Rule 804 Excel files to Drive."""
import contextlib,ctypes,datetime,hashlib,json,os,re,shutil,subprocess,sys,tempfile,time,uuid
from pathlib import Path
REPO='chottuapp/ChotuApp-Software';LEGACY_FOLDER='ChotuApp 20-10-2026 Fresh';EXCLUDED={'LAAM','Khaadi','Sapphire'}

def daily_folder(now=None):
    pakistan=datetime.timezone(datetime.timedelta(hours=5))
    now=now or datetime.datetime.now(datetime.timezone.utc)
    return 'ChotuApp '+now.astimezone(pakistan).strftime('%d-%m-%Y')+' Fresh'

def activate_day(state,folder):
    if 'daily_uploads' not in state:
        state['daily_uploads']={LEGACY_FOLDER:dict(state.get('uploaded',{}))}
        state['daily_seen_artifacts']={LEGACY_FOLDER:dict(state.get('seen_artifacts',{}))}
    state['drive_folder']=folder
    state['uploaded']=state['daily_uploads'].setdefault(folder,{})
    state['seen_artifacts']=state.setdefault('daily_seen_artifacts',{}).setdefault(folder,{})

def rclone_path():
    rc=shutil.which('rclone')
    if rc:return rc
    choices=list((Path(os.environ['LOCALAPPDATA'])/'Microsoft/WinGet/Packages').glob('Rclone.Rclone_*/rclone-*-windows-amd64/rclone.exe'))
    if not choices:raise RuntimeError('Rclone executable not found')
    return str(sorted(choices)[-1])

def status_report():
    base=Path.home()/'Desktop/ANAS_DATA_FETCH/Fresh26_2026-10-20'
    path=base/'pipeline-state.json'
    if not path.is_file():print('No pipeline state found; no upload verified.');return 2
    state=json.loads(path.read_text(encoding='utf-8'));folder=state.get('drive_folder',LEGACY_FOLDER)
    print('Drive folder:',folder);print('Rule 804: uploader accepts processed artifacts only; bounded automated pass, review warnings may remain.')
    print('Previously checksum-verified uploads:',len(state.get('uploaded',{})),'/26')
    rc=rclone_path()
    listing=command([rc,'lsf','chotudrive:'+folder,'--files-only','--include','*.xlsx'],check=False)
    if listing.returncode==0:print('Excel files currently listed in Drive:',len([n for n in listing.stdout.splitlines() if n.lower().endswith('.xlsx')]))
    else:print('Drive listing unavailable:',listing.stderr.strip())
    with tempfile.TemporaryDirectory() as tmp:
        for store,sha in state.get('uploaded',{}).items():
            file=base/'Drive_Ready'/(store+'.xlsx')
            if not file.is_file() or hashlib.sha256(file.read_bytes()).hexdigest()!=sha:raise ValueError('Local reviewed file missing or changed: '+store)
            shutil.copy2(file,Path(tmp)/file.name)
        if state.get('uploaded'):
            subprocess.run([rc,'check',tmp,'chotudrive:'+folder,'--include','*.xlsx','--one-way'],check=True)
            print('CURRENT DRIVE CHECK PASSED:',len(state['uploaded']),'Rule 804 files; no differences.')
    return 0

@contextlib.contextmanager
def lease(path):
    path.parent.mkdir(parents=True,exist_ok=True);stream=path.open('a+b');locked=False
    try:
        stream.seek(0,2)
        if stream.tell()==0:stream.write(b'0');stream.flush()
        stream.seek(0)
        if os.name=='nt':
            import msvcrt
            msvcrt.locking(stream.fileno(),msvcrt.LK_NBLCK,1)
        else:
            import fcntl
            fcntl.flock(stream.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
        locked=True;yield
    finally:
        if locked:
            stream.seek(0)
            if os.name=='nt':
                import msvcrt
                msvcrt.locking(stream.fileno(),msvcrt.LK_UNLCK,1)
            else:
                import fcntl
                fcntl.flock(stream.fileno(),fcntl.LOCK_UN)
        stream.close()

def command(args,check=True,timeout=180):
    result=subprocess.run(args,capture_output=True,text=True,timeout=timeout)
    if check and result.returncode:raise RuntimeError(result.stderr.strip() or result.stdout.strip() or 'Command failed')
    return result

def save(path,data):
    tmp=path.with_suffix('.pending');tmp.write_text(json.dumps(data,indent=2),encoding='utf-8');tmp.replace(path)

def related(runs,groups):
    ids={str(r['databaseId']) for r in runs if r.get('displayTitle') in {'Cloud group '+g for g in groups}}
    for _ in runs:
        more={str(r['databaseId']) for r in runs if r.get('displayTitle','').startswith('Automatic continuation of ') and r['displayTitle'].split()[-1] in ids}
        if more<=ids:break
        ids.update(more)
    return [r for r in runs if str(r['databaseId']) in ids]

def checked_files(root,manifest):
    result=[]
    for item in manifest.get('files',[]):
        name=item['name'];store=item['store']
        if not item.get('rule804') or not re.fullmatch('[0-9a-f]{64}',str(item.get('pipeline_revision',''))) or not re.fullmatch('[0-9a-f]{64}',str(item.get('source_sha256',''))):raise ValueError('Missing Rule 804 processing evidence: '+name)
        if Path(name).name!=name or name!=store+'.xlsx' or store in EXCLUDED:raise ValueError('Unexpected workbook identity')
        matches=list(root.rglob(name))
        if len(matches)!=1 or hashlib.sha256(matches[0].read_bytes()).hexdigest()!=item['sha256']:raise ValueError('Rule 804 workbook checksum mismatch: '+name)
        result.append((item,matches[0]))
    return result

def pipeline():
    gh=shutil.which('gh') or str(Path(os.environ.get('ProgramFiles','C:/Program Files'))/'GitHub CLI/gh.exe')
    rc=rclone_path()
    remotes=command([rc,'listremotes']).stdout.splitlines()
    if 'chotudrive:' not in remotes:raise RuntimeError('Existing chotudrive remote unavailable; no fetching dispatched')
    base=Path.home()/'Desktop/ANAS_DATA_FETCH/Fresh26_2026-10-20';base.mkdir(parents=True,exist_ok=True);statepath=base/'pipeline-state.json';output=base/'Drive_Ready';output.mkdir(exist_ok=True)
    try:state=json.loads(statepath.read_text())
    except FileNotFoundError:state={'batch_key':'20261020-'+uuid.uuid4().hex[:12],'uploaded':{},'seen_artifacts':{}};save(statepath,state)
    def call(*args,timeout=180):return command([gh,*args],timeout=timeout).stdout
    awake=None
    if os.name=='nt':awake=ctypes.windll.kernel32.SetThreadExecutionState;awake(0x80000001)
    try:
        if not state.get('dispatcher'):
            runs=json.loads(call('run','list','--repo',REPO,'--workflow','cloud-fresh26.yml','--limit','50','--json','databaseId,displayTitle'))
            existing=[r for r in runs if r.get('displayTitle')=='Fresh26 '+state['batch_key']]
            if not existing:print(call('workflow','run','cloud-fresh26.yml','--repo',REPO,'--ref','main','-f','batch_key='+state['batch_key']),flush=True)
            for _ in range(20):
                runs=json.loads(call('run','list','--repo',REPO,'--workflow','cloud-fresh26.yml','--limit','50','--json','databaseId,displayTitle'))
                existing=[r for r in runs if r.get('displayTitle')=='Fresh26 '+state['batch_key']]
                if existing:state['dispatcher']=str(existing[0]['databaseId']);save(statepath,state);break
                time.sleep(3)
            if not state.get('dispatcher'):raise RuntimeError('Dispatch pending; rerun this helper to reconnect without creating a new batch')
        rootrun=state['dispatcher'];print('Fresh batch: https://github.com/'+REPO+'/actions/runs/'+rootrun,flush=True);print('Drive folder:',daily_folder(),'| Keep this helper open for Drive uploads. Cloud fetching continues independently.',flush=True)
        while not state.get('groups'):
            info=json.loads(call('run','view',rootrun,'--repo',REPO,'--json','status,conclusion'))
            with tempfile.TemporaryDirectory() as tmp:
                result=command([gh,'run','download',rootrun,'--repo',REPO,'--name','fresh26-plan','--dir',tmp],check=False)
                plan=next(Path(tmp).rglob('fetch-group-plan.json'),None)
                if result.returncode==0 and plan:
                    state['groups']=json.loads(plan.read_text())['groups']
                    stores=[s['name'] for g in state['groups'] for s in g['stores']]
                    if len(stores)!=26 or len(set(stores))!=26 or EXCLUDED&set(stores) or any(len(g['stores'])>3 for g in state['groups']):raise ValueError('Fresh store plan did not match requested scope')
                    state['expected_stores']=stores;save(statepath,state);break
            if info['status']=='completed':raise RuntimeError('Fresh dispatcher failed or no plan available. Inspect run '+rootrun+'; nothing was uploaded')
            print('Waiting for 26-store runner plan...',flush=True);time.sleep(30)
        stable=0
        while True:
            try:
                folder=daily_folder();activate_day(state,folder);save(statepath,state)
                allruns=json.loads(call('run','list','--repo',REPO,'--workflow','cloud-fetch.yml','--limit','100','--json','databaseId,displayTitle,status,conclusion'))
                runs=related(allruns,[g['runner_group'] for g in state['groups']]);active=sum(r['status']!='completed' for r in runs)
                for run in reversed(runs):
                    rid=str(run['databaseId']);artifacts=json.loads(call('api','repos/'+REPO+'/actions/runs/'+rid+'/artifacts?per_page=100'))['artifacts'];items=[a for a in artifacts if a['name']=='chotuapp-rule804-files' and not a.get('expired')]
                    if not items:continue
                    artifact=items[0]
                    if state['seen_artifacts'].get(rid)==artifact['id']:continue
                    with tempfile.TemporaryDirectory() as tmp:
                        result=command([gh,'run','download',rid,'--repo',REPO,'--name','chotuapp-rule804-files','--dir',tmp],check=False,timeout=600)
                        manifests=list(Path(tmp).rglob('manifest.json'))
                        if result.returncode or len(manifests)!=1:continue
                        manifest=json.loads(manifests[0].read_text());batch=[]
                        for record,file in checked_files(Path(tmp),manifest):
                            if record['store'] not in state['expected_stores']:raise ValueError('Unexpected store outside fresh batch')
                            if state['uploaded'].get(record['store'])==record['sha256']:continue
                            destination=output/record['name'];shutil.copy2(file,destination);batch.append(record)
                        if batch:
                            print('Uploading',len(batch),'checked Excel files...',flush=True)
                            with tempfile.TemporaryDirectory() as stage:
                                for record in batch:shutil.copy2(output/record['name'],Path(stage)/record['name'])
                                subprocess.run([rc,'copy',stage,'chotudrive:'+folder,'--include','*.xlsx','--checksum','--progress'],check=True)
                                subprocess.run([rc,'check',stage,'chotudrive:'+folder,'--include','*.xlsx','--one-way'],check=True)
                            for record in batch:state['uploaded'][record['store']]=record['sha256']
                            state['last_verified_at']=datetime.datetime.now(datetime.timezone.utc).isoformat();save(statepath,state)
                            print('VERIFIED: Rule 804 applied before upload;',len(batch),'files checked in',folder,flush=True)
                        if manifest.get('held'):print('RULE804 HELD FOR REVIEW:',json.dumps(manifest['held']),flush=True)
                        state['seen_artifacts'][rid]=artifact['id'];save(statepath,state)
                print(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),'| fresh active/queued:',active,'| Drive verified:',len(state['uploaded']),'/26',flush=True)
                if len(state['uploaded'])==26:print('COMPLETE: 26 fresh Rule 804 Excel workbooks uploaded and checksum-verified. Excluded stores untouched. No reports uploaded.',flush=True);return 0
                # A continuation can appear shortly after its parent finishes.
                stable=stable+1 if runs and not active else 0
                if stable>=3:
                    missing=sorted(set(state['expected_stores'])-set(state['uploaded']));print('Fresh cloud runs finished; remaining stores need review:',', '.join(missing),flush=True);return 2
            except (OSError,RuntimeError,ValueError,subprocess.SubprocessError) as exc:
                print('PIPELINE WAIT:',str(exc),'| Verified files retained; retrying in 60s.',flush=True)
            time.sleep(60)
    except KeyboardInterrupt:print('Drive helper stopped. Cloud fetch runs were not cancelled. Run this same helper to resume syncing.',flush=True);return 130
    finally:
        if awake:awake(0x80000000)
def main():
    if '--status' in sys.argv:return status_report()
    base=Path.home()/'Desktop/ANAS_DATA_FETCH/Fresh26_2026-10-20';base.mkdir(parents=True,exist_ok=True)
    if '--resume-only' in sys.argv and not (base/'pipeline-state.json').is_file():
        print('Existing batch state missing; no new fetch dispatched.');return 2
    try:
        with lease(base/'pipeline.lock'):return pipeline()
    except OSError as exc:
        print('Fresh pipeline already running or lock unavailable:',str(exc),flush=True);return 2
if __name__=='__main__':sys.exit(main())
