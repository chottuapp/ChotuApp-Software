"""Supervise the approved Khaadi local worker; never invent a parser repair."""
import contextlib,hashlib,json,os,re,subprocess,sys,time,urllib.request,threading,datetime,shutil,base64
from pathlib import Path
REPO='https://raw.githubusercontent.com/chottuapp/ChotuApp-Software/'
FEED=REPO+'main/cloud/recovery-release.json'

@contextlib.contextmanager
def keep_awake():
    api=None
    if os.name=='nt':
        import ctypes
        api=ctypes.windll.kernel32.SetThreadExecutionState
        if not api(0x80000001):print('Automatic sleep prevention unavailable; keep PC awake.',flush=True)
    try:yield
    finally:
        if api:api(0x80000000)

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

def occupied(path):
    try:
        with lease(path):return False
    except OSError:return True

def release_spec(data):
    spec=data.get('khaadi_worker',{})
    if data.get('schema')!=1 or not re.fullmatch('[0-9a-f]{40}',str(spec.get('commit',''))) or not re.fullmatch('[0-9a-f]{64}',str(spec.get('sha256',''))):raise ValueError('Invalid reviewed recovery release')
    return spec

def transient(error):
    # Unknown/parser/currency/price/stock failures require a newly published repair.
    return ('SOURCE PAUSED:' in error or bool(re.search(r'curl.*\((?:5|6|7|18|28|52|55|56)\)',error,re.I)))

def action(code,status,revision,attempted):
    if code in (130,-2,-1073741510) or status.get('status')=='paused':return 'manual_stop'
    if code==0 and status.get('status')=='exported_review_required':return 'complete'
    if revision!=attempted:return 'new_release'
    if transient(str(status.get('error',''))):return 'retry'
    return 'wait_for_fix'

def read_json(path):
    try:return json.loads(path.read_text(encoding='utf-8'))
    except (OSError,ValueError):return {}

def local_report(data):
    status=read_json(data/'local-status.json');live=occupied(data/'active.lock')
    event=str(status.get('last_event',''))
    if '\\Users\\' in event:event='Local export event recorded'
    progress=status.get('last_progress_epoch')
    return {'store':'Khaadi','execution':'Windows local','observed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'worker_active':live,'status':('stopped' if status.get('status')=='running' and not live else status.get('status','unknown')),'worker_updated':status.get('updated'),'last_event':event[:1200],'error':str(status.get('error',''))[:700],'progress_age_seconds':max(0,round(time.time()-progress)) if isinstance(progress,(int,float)) else None}

def publish_local_report(data):
    gh=shutil.which('gh') or str(Path(os.environ.get('ProgramFiles','C:/Program Files'))/'GitHub CLI/gh.exe')
    repo='repos/chottuapp/ChotuApp-Software';branch='local-run-status'
    def api(endpoint,method=None,payload=None):
        args=[gh,'api',repo+'/'+endpoint]
        if method:args+=['--method',method]
        if payload is not None:args+=['--input','-']
        result=subprocess.run(args,input=json.dumps(payload) if payload is not None else None,capture_output=True,text=True,timeout=60)
        if result.returncode:raise RuntimeError('Local status upload unavailable; local fetch unchanged')
        return json.loads(result.stdout) if result.stdout.strip() else {}
    try:api('git/ref/heads/'+branch)
    except RuntimeError:
        main=api('git/ref/heads/main');api('git/refs','POST',{'ref':'refs/heads/'+branch,'sha':main['object']['sha']})
    payload={'message':'Update credential-free Khaadi local heartbeat','branch':branch,'content':base64.b64encode(json.dumps(local_report(data),indent=2).encode()).decode()}
    try:payload['sha']=api('contents/local/khaadi.json?ref='+branch)['sha']
    except RuntimeError:pass
    api('contents/local/khaadi.json','PUT',payload)

@contextlib.contextmanager
def local_reporting(data):
    stop=threading.Event()
    def loop():
        while not stop.is_set():
            try:publish_local_report(data)
            except (OSError,ValueError,RuntimeError,subprocess.SubprocessError):pass
            stop.wait(60)
    thread=threading.Thread(target=loop,daemon=True);thread.start()
    try:yield
    finally:
        stop.set();thread.join(timeout=2)
        try:publish_local_report(data)
        except (OSError,ValueError,RuntimeError,subprocess.SubprocessError):pass

def supervisor(data,hours=24):
    data.mkdir(parents=True,exist_ok=True);deadline=time.monotonic()+hours*3600;attempted=None;last_code=None;attempt=0;observed_existing=False
    def report(state,**extra):
        payload=dict(status=state,updated=time.strftime('%Y-%m-%d %H:%M:%S'),**extra);(data/'recovery-status.json').write_text(json.dumps(payload,indent=2),encoding='utf-8');print('AUTO RECOVERY:',state,extra,flush=True)
    try:
        with lease(data/'recovery-supervisor.lock'),keep_awake(),local_reporting(data):
            while time.monotonic()<deadline:
                if occupied(data/'active.lock'):
                    observed_existing=True;report('existing_fetch_running');time.sleep(60);continue
                try:
                    request=urllib.request.Request(FEED+'?check='+str(time.time_ns()),headers={'Cache-Control':'no-cache','Pragma':'no-cache'})
                    raw=urllib.request.urlopen(request,timeout=45).read(65537)
                    if len(raw)>65536:raise ValueError('Release metadata too large')
                    spec=release_spec(json.loads(raw));revision=spec['commit']
                except (OSError,ValueError) as exc:
                    report('release_check_wait',detail=str(exc));time.sleep(60);continue
                status=read_json(data/'local-status.json')
                if status.get('status')=='exported_review_required' or (observed_existing and status.get('status')=='paused'):
                    report('complete' if status['status']=='exported_review_required' else 'manual_stop');return 0
                decision='new_release' if attempted is None else action(last_code,status,revision,attempted)
                if decision in ('manual_stop','complete'):report(decision);return 0
                if decision=='wait_for_fix':
                    report('waiting_for_published_fix',error=status.get('error','Unknown worker failure'));time.sleep(300);continue
                if decision=='retry':
                    report('temporary_error_cooldown',seconds=min(900,60*2**min(attempt,4)));time.sleep(min(900,60*2**min(attempt,4)))
                    if time.monotonic()>=deadline:break
                worker=data/('recovery-worker-'+revision+'.py')
                try:
                    if not worker.exists() or hashlib.sha256(worker.read_bytes()).hexdigest()!=spec['sha256']:
                        payload=urllib.request.urlopen(REPO+revision+'/catalog-tools/start_khaadi_local_fetch_windows.py',timeout=60).read(1024*1024+1)
                        if len(payload)>1024*1024 or hashlib.sha256(payload).hexdigest()!=spec['sha256']:raise ValueError('Worker checksum mismatch; nothing executed')
                        worker.write_bytes(payload)
                except (OSError,ValueError) as exc:
                    report('worker_download_wait',detail=str(exc));time.sleep(60);continue
                if occupied(data/'active.lock'):continue
                report('starting_saved_fetch',release=revision);attempted=revision;attempt+=1
                last_code=subprocess.run([sys.executable,str(worker)]).returncode
            report('supervision_window_finished',hours=hours);return 2
    except KeyboardInterrupt:
        report('manual_stop');return 130
    except OSError as exc:
        print('Recovery supervisor already active or lock unavailable:',exc,flush=True);return 2

def main():
    print('Khaadi recovery supervisor: temporary retries and reviewed GitHub updates; Ctrl+C stops supervision. Keep this CMD and PC awake. Window: 24 hours.',flush=True)
    return supervisor(Path.home()/'Desktop/ANAS_DATA_FETCH/Khaadi_Local')
if __name__=='__main__':sys.exit(main())
