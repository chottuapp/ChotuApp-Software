"""Add isolated two-store scheduling without replacing fetching modules or saved data."""
import argparse,ast,datetime,os,shutil,tempfile,sys
from pathlib import Path
HOOK='\n# CHOTUAPP_PARALLEL_STORES_V1\nfrom parallel_store_support import enable_parallel_stores as _enable_parallel_stores\n_enable_parallel_stores(globals())\n\n'

def transform(source):
    ast.parse(source)
    if '# CHOTUAPP_PARALLEL_STORES_V1' in source:return source
    if '# CHOTUAPP_DURABLE_RUNS_V1' not in source or '# CHOTUAPP_CONTROLLED_FAST_V1' not in source:raise RuntimeError('This update requires the existing Saved Runs and Fast Fetch installation. No files changed.')
    points=[source.find(x) for x in ("if __name__=='__main__':",'if __name__ == "__main__":',"if __name__ == '__main__':")];points=[x for x in points if x>=0]
    if not points:raise RuntimeError('Startup entry point missing')
    i=min(points);result=source[:i]+HOOK+source[i:];compile(result,'main.py','exec');return result

def atomic(path,data):
    fd,name=tempfile.mkstemp(prefix='.parallel-stores-',dir=path.parent)
    try:
        with os.fdopen(fd,'wb') as stream:stream.write(data);stream.flush();os.fsync(stream.fileno())
        os.replace(name,path)
    finally:Path(name).unlink(missing_ok=True)

def install(target):
    target=Path(target).resolve();main=target/'main.py';original=main.read_bytes()
    source=transform(original.decode('utf-8-sig')).encode()
    if original.startswith(b'\xef\xbb\xbf'):source=b'\xef\xbb\xbf'+source
    root=Path(__file__).resolve().parent
    payloads={name:(root/name).read_bytes() for name in ('parallel_store_support.py','store_process_worker.py','software_revision_support.py')}
    payloads['main.py']=source
    for name,data in payloads.items():compile(data,name,'exec')
    # Never alter a program while its Saved Runs queue is actively fetching.
    sys.path.insert(0,str(target))
    from resume_support import RunLease
    lease=RunLease(target/'saved_runs');lease.path.parent.mkdir(parents=True,exist_ok=True);lease.acquire()
    try:
        backup=target/'backups'/('before_parallel_stores_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f'));backup.mkdir(parents=True)
        for name in payloads:
            path=target/name
            if path.exists():
                shutil.copy2(path,backup/name)
                if path.read_bytes()!=(backup/name).read_bytes():raise RuntimeError('Backup verification failed')
        if main.read_bytes()!=original:raise RuntimeError('Source changed during installation')
        for name,data in payloads.items():atomic(target/name,data)
    finally:lease.release()
    print('SUCCESS: Parallel Stores installed — up to 2 different websites together.')
    print('Existing buttons, source pacing, cooldowns, price checks, exports and saved runs retained.')
    print('Each child store process is capped at 2 HTTP preload workers; recent-throttle single-worker settings remain.')
    print('Restart and Continue Saved Run, or select stores and New Fresh Run.')
    print('Backup:',backup)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--target',type=Path,default=Path.home()/'Desktop'/'ChotuApp_Software');args=parser.parse_args()
    try:install(args.target)
    except Exception as exc:parser.exit(1,'Parallel Stores update stopped: '+str(exc)+'\n')
