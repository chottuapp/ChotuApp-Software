"""Keep one local cloud-sync window running and refresh its helper at safe process boundaries."""
import argparse,os,re,runpy,subprocess,sys,tempfile,time,urllib.request
from pathlib import Path


def refresh_helper(gh,repo,target,last_revision=None):
    result=subprocess.run([gh,'api','repos/'+repo+'/commits/main','--jq','.sha'],capture_output=True,text=True,timeout=30,check=True)
    revision=result.stdout.strip()
    if not re.fullmatch('[0-9a-f]{40}',revision):raise ValueError('Invalid source revision')
    if revision==last_revision:return revision,False
    url='https://raw.githubusercontent.com/'+repo+'/'+revision+'/cloud_sync_windows.py'
    with urllib.request.urlopen(url,timeout=30) as response:payload=response.read(1024*1024+1)
    if len(payload)>1024*1024:raise ValueError('Sync helper exceeds download limit')
    compile(payload,str(target),'exec')
    if target.is_file() and target.read_bytes()==payload:return revision,False
    target.parent.mkdir(parents=True,exist_ok=True);fd,name=tempfile.mkstemp(prefix='.sync-update-',suffix='.py',dir=target.parent)
    try:
        with os.fdopen(fd,'wb') as stream:stream.write(payload)
        os.replace(name,target)
    finally:Path(name).unlink(missing_ok=True)
    return revision,True


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--run',required=True);parser.add_argument('--repo',default='chottuapp/ChotuApp-Software');parser.add_argument('--update-interval',type=int,default=900);args=parser.parse_args()
    if not re.fullmatch('[0-9]+',args.run) or not re.fullmatch('[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+',args.repo):parser.error('Invalid run or repository')
    if args.update_interval<300:parser.error('Update interval must be at least 300 seconds')
    target=Path(__file__).resolve().with_name('cloud_sync_windows.py')
    if not target.is_file():raise RuntimeError('Download cloud_sync_windows.py alongside this launcher first.')
    gh=runpy.run_path(str(target))['find_gh']();revision=None;child=None
    print('Live sync with automatic helper updates. Cloud fetching is independent of this window.',flush=True)
    try:
        while True:
            try:revision,changed=refresh_helper(gh,args.repo,target,revision)
            except (OSError,ValueError,SyntaxError,subprocess.SubprocessError) as exc:changed=False;print('Update check unavailable; keeping installed helper: '+str(exc),flush=True)
            if changed and child and child.poll() is None:
                # Sync writes downloads atomically and persists artifact IDs. Restarting
                # only this local child is recoverable; the cloud run is never stopped.
                child.terminate();child.wait(timeout=15);child=None
            if child is None:
                options={'creationflags':subprocess.CREATE_NEW_PROCESS_GROUP} if os.name=='nt' else {'start_new_session':True}
                child=subprocess.Popen([sys.executable,'-u',str(target),'--run',args.run,'--repo',args.repo],stdin=subprocess.DEVNULL,**options)
            deadline=time.monotonic()+args.update_interval
            while time.monotonic()<deadline:
                if child.poll() is not None:
                    if child.returncode==0:return
                    print('Local helper exited; retrying in 30 seconds. Cloud run was not cancelled.',flush=True)
                    child=None;time.sleep(30);break
                time.sleep(1)
    except KeyboardInterrupt:print('Local live sync stopped. Cloud run was not cancelled.',flush=True)
    finally:
        if child and child.poll() is None:child.terminate();child.wait(timeout=15)

if __name__=='__main__':main()
