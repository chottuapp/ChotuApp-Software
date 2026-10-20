"""Run Khaadi's public catalog locally, retaining verified work for resume."""
import hashlib,importlib.util,json,subprocess,sys,time,urllib.request,threading,os
from pathlib import Path
REVISION='c0fc74c'
FILES={'main.py': '31dfcc3547c65eb3615f6e167cbdb61d2a4aea366b53f3a2ccb042ac7ca77b01', 'khaadi_source_support.py': '276040f29967b11e3a48e57e53c2597839b2b9c832125106600edabf157205a5', 'laam_source_support.py': '690bd35e36bf07373ed72c7c6b3d9f27e9952a2f7142da30696d7917346b7ab0', 'resume_support.py': 'cc2eff15ee524963643f096eb165fe463404715ca0627990ea5c820520b47fcf', 'ranking_support.py': '6a4199a0fd90f1afc74e8e2b5b3327ebd69fe47bdd8d2263e869facc5fbf5953', 'website_order_support.py': '7c5bd0ce3cb4e6990f706cfc0b4d11add0620236da12950db213ef5a0c38cc5d', 'website_category_support.py': '65dfda24fc281d3f986293421977ee9f3d758d375099fc005242677cac268cfc', 'subcategory_inference_support.py': 'bf22deacee7287fb9803a88df64a63e5255a36c8b2720ec4f74c7176e3cc13a2', 'complete_description_support.py': '5db0a81dc00d53296d432e6eecca717cbd74a54a3721b24347787ad496b8f470', 'catalog-tools/check_khaadi_local_adapter_windows.py': '1cb937d8715a98fbc33a827f4400e02740ca9d08ecc81407e12b3c650543c4d1', 'importer-files/Chotu_Products_Import_Template_Discount_Tags.xlsx': '541b348dce523bd2e06679347afdcf7abe33e94aebf58dc6e09042b803fb3774'}

def disable_quick_edit():
    """Prevent Windows console text selection from suspending the fetch."""
    if os.name!='nt':return
    import ctypes
    api=ctypes.windll.kernel32;handle=api.GetStdHandle(-10);mode=ctypes.c_ulong()
    if api.GetConsoleMode(handle,ctypes.byref(mode)):
        api.SetConsoleMode(handle,(mode.value | 0x0080) & ~0x0040)


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec);sys.modules[name]=module;spec.loader.exec_module(module);return module

def fetch(root,data,session=None):
    sys.path.insert(0,str(root));data.mkdir(parents=True,exist_ok=True)
    from resume_support import ResponseCache,RunLease
    import khaadi_source_support as source
    local=load('khaadi_local_transport',root/'catalog-tools/check_khaadi_local_adapter_windows.py')
    engine=load('khaadi_local_engine',root/'main.py')
    lease=RunLease(data);lease.acquire();cache=ResponseCache(data/'pages.sqlite3')
    raw=session or local.CurlSession()
    class CachedCurl:
        def get(self,url,**kwargs):
            response=cache.get(url)
            if response is not None:return response
            response=raw.get(url,**kwargs)
            response.encoding='utf-8';response.headers={'Content-Type':'text/html; charset=utf-8'}
            from urllib.parse import urlsplit
            if urlsplit(response.url).hostname=='pk.khaadi.com':cache.put(url,response)
            return response
        def get_fresh(self,url,**kwargs):return raw.get(url,**kwargs)
    logpath=data/'fetch-log.txt';status=data/'local-status.json'
    last_heartbeat=[0.0];state_lock=threading.RLock();stop_heartbeat=threading.Event()
    latest_event=['Starting'];latest_progress=[time.time()]
    def log(message):
        line=time.strftime('%Y-%m-%d %H:%M:%S')+' '+str(message)
        latest_event[0]=str(message);latest_progress[0]=time.time()
        with logpath.open('a',encoding='utf-8') as stream:stream.write(line+'\n')
        print(line,flush=True)
        if time.monotonic()-last_heartbeat[0]>=30:
            last_heartbeat[0]=time.monotonic()
            try:
                record=json.loads(status.read_text())
                if record.get('status')=='running':state('running',last_event=str(message))
            except (OSError,ValueError):pass
    def state(value,**extra):
        with state_lock:
            temporary=status.with_suffix('.pending');temporary.write_text(json.dumps(dict(status=value,worker_pid=os.getpid(),updated=time.strftime('%Y-%m-%d %H:%M:%S'),last_progress_epoch=latest_progress[0],**extra),indent=2),encoding='utf-8');temporary.replace(status)
    def heartbeat():
        while not stop_heartbeat.wait(30):
            try:
                with state_lock:
                    record=json.loads(status.read_text(encoding='utf-8'))
                    if record.get('status')=='running':
                        state('running',last_event=latest_event[0],progress_age_seconds=round(time.time()-latest_progress[0]))
            except (OSError,ValueError):pass
    pulse=threading.Thread(target=heartbeat,daemon=True);pulse.start()
    try:
        engine.OUT=data/'files';engine.OUT.mkdir(exist_ok=True);engine.S=CachedCurl()
        engine._chotu_tls.saved_api_path=data/'api.sqlite3';engine._chotu_tls.saved_response_cache=cache
        engine._chotu_debug_request=lambda url,attempt:log('PUBLIC GET attempt='+str(attempt)+' '+url)
        engine._chotu_debug_response=lambda code,size,**kwargs:log('HTTP '+str(code)+' bytes='+str(size)+(' CACHE' if kwargs.get('cached') else ''))
        engine._chotu_debug_stage=lambda text:log('STAGE: '+text)
        source.enable_khaadi_source(vars(engine))
        state('running');log('KHAADI LOCAL FETCH STARTED. Saved responses/products reused. Keep CMD open and PC awake; Ctrl+C stops local fetch.')
        engine._chotuapp_run_site_original(source.BASE,'Khaadi',root/'importer-files/Chotu_Products_Import_Template_Discount_Tags.xlsx',log)
        files=list(engine.OUT.glob('*.xlsx'))
        if not files:raise RuntimeError('No Excel workbook produced')
        state('exported_review_required',files=[str(p) for p in files],full_catalog_verified=False)
        log('SAVED REVIEW WORKBOOK: '+str(files[0]));log('Full catalog coverage remains unverified. No Rule 804 applied and no Google Drive upload performed.')
        return 0
    except KeyboardInterrupt:
        state('paused',reason='Stopped locally; saved verified work retained');log('PAUSED. Run this same helper again to resume saved work.');return 130
    except Exception as exc:
        import traceback
        log(traceback.format_exc())
        state('failed_resume_available',error=str(exc));log('FETCH STOPPED: '+str(exc));log('Saved work retained. Send the last 30 lines of fetch-log.txt; no source data guessed.');return 2
    finally:
        stop_heartbeat.set();pulse.join(timeout=2);cache.close();lease.release()

def main():
    disable_quick_edit()
    missing=[]
    for module,package in [('bs4','beautifulsoup4'),('openpyxl','openpyxl'),('requests','requests')]:
        if importlib.util.find_spec(module) is None:missing.append(package)
    if missing:subprocess.run([sys.executable,'-m','pip','install',*missing],check=True)
    desktop=Path.home()/'Desktop';data=desktop/'ANAS_DATA_FETCH'/'Khaadi_Local';root=data/'software';root.mkdir(parents=True,exist_ok=True)
    for name,expected in FILES.items():
        path=root/name
        if path.exists() and hashlib.sha256(path.read_bytes()).hexdigest()==expected:continue
        print('Preparing:',name,flush=True);payload=urllib.request.urlopen('https://raw.githubusercontent.com/chottuapp/ChotuApp-Software/'+REVISION+'/'+name,timeout=60).read()
        if hashlib.sha256(payload).hexdigest()!=expected:raise RuntimeError('Source verification failed: '+name)
        path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(payload)
    return fetch(root,data)
if __name__=='__main__':sys.exit(main())
