"""Download cloud logs and completed Excel snapshots using the user's GitHub CLI login."""
import argparse,datetime,hashlib,json,os,re,shutil,subprocess,sys,tempfile,time
from pathlib import Path


def find_gh():
    result=shutil.which('gh')
    if result:return result
    for key in ('ProgramFiles','ProgramFiles(x86)','LOCALAPPDATA'):
        if not os.environ.get(key):continue
        for relative in ('GitHub CLI/gh.exe','Programs/GitHub CLI/gh.exe'):
            path=Path(os.environ[key])/relative
            if path.is_file():return str(path)
    raise RuntimeError('GitHub CLI not found. Install GitHub.cli and log in first.')


def atomic_copy(source,destination):
    destination=Path(destination);destination.parent.mkdir(parents=True,exist_ok=True)
    if destination.exists() and hashlib.sha256(destination.read_bytes()).digest()==hashlib.sha256(Path(source).read_bytes()).digest():return False
    if destination.exists() and destination.suffix.lower() in ('.xlsx','.csv'):
        backup=destination.parent/'previous-cloud-files';backup.mkdir(exist_ok=True)
        stamp=hashlib.sha256(destination.read_bytes()).hexdigest()[:16];copy=backup/(destination.stem+'_'+stamp+destination.suffix)
        if not copy.exists():shutil.copy2(destination,copy)
    fd,name=tempfile.mkstemp(prefix='.cloud-sync-',dir=destination.parent);os.close(fd)
    try:shutil.copyfile(source,name);os.replace(name,destination)
    finally:Path(name).unlink(missing_ok=True)
    return True


class Sync:
    def __init__(self,gh,repo,run,folder,call=None):
        self.gh=gh;self.repo=repo;self.run=run;self.folder=Path(folder);self.folder.mkdir(parents=True,exist_ok=True);(self.folder/'logs').mkdir(exist_ok=True)
        self.state_file=self.folder/'.cloud-sync-state.json';self.call_override=call
        try:self.seen=json.loads(self.state_file.read_text()).get('artifacts',{})
        except (OSError,ValueError):self.seen={}
    def call(self,args):
        if self.call_override:return self.call_override(args)
        result=subprocess.run([self.gh,*args],stdout=subprocess.PIPE,stderr=subprocess.PIPE,encoding='utf-8',errors='replace')
        if result.returncode:raise RuntimeError(result.stderr.strip() or 'GitHub request failed')
        return result.stdout
    def tick(self):
        status=json.loads(self.call(['run','view',self.run,'--repo',self.repo,'--json','status,conclusion']))
        artifacts=json.loads(self.call(['api','repos/'+self.repo+'/actions/runs/'+self.run+'/artifacts?per_page=100'])).get('artifacts',[])
        allowed={'chotuapp-live-logs','chotuapp-diagnostics','chotuapp-excel-files'}
        for artifact in sorted(artifacts,key=lambda x:int(x.get('id',0))):
            name=artifact.get('name');identity=str(artifact.get('id'))
            if name not in allowed or artifact.get('expired') or self.seen.get(name)==identity:continue
            with tempfile.TemporaryDirectory(prefix='chotu-cloud-download-') as temp:
                # Download by artifact ID: a newer live snapshot may replace the old name during polling.
                archive=Path(temp)/'artifact.zip'
                if self.call_override:
                    self.call(['run','download',self.run,'--repo',self.repo,'--name',name,'--dir',temp])
                else:
                    with archive.open('wb') as stream:
                        result=subprocess.run([self.gh,'api','repos/'+self.repo+'/actions/artifacts/'+identity+'/zip'],stdout=stream,stderr=subprocess.PIPE)
                    if result.returncode:raise RuntimeError(result.stderr.decode('utf-8',errors='replace'))
                    import zipfile
                    with zipfile.ZipFile(archive) as zipped:
                        if sum(item.file_size for item in zipped.infolist())>1024**3:raise RuntimeError('Artifact exceeds 1 GB expanded limit')
                        for item in zipped.infolist():
                            path=Path(item.filename)
                            if path.is_absolute() or '..' in path.parts or '\\' in item.filename or (item.external_attr>>16)&0o170000==0o120000:raise RuntimeError('Unsafe artifact entry')
                        zipped.extractall(temp)
                count=0
                for path in Path(temp).rglob('*'):
                    if not path.is_file() or path.suffix.lower() not in ('.xlsx','.csv','.json','.txt','.log'):continue
                    relative=path.relative_to(temp)
                    destination=self.folder/relative if name=='chotuapp-excel-files' else self.folder/'logs'/relative
                    if atomic_copy(path,destination):count+=1
                self.seen[name]=identity;print('Saved '+name+': '+str(count)+' new/updated files.',flush=True)
        if not self.seen:print('No downloadable snapshot yet. Older workflow versions publish files/logs only after fetching finishes.',flush=True)
        self.state_file.write_text(json.dumps({'artifacts':self.seen}),encoding='utf-8')
        text='Updated: '+datetime.datetime.now().astimezone().isoformat()+'\nRun: '+self.run+'\nStatus: '+str(status.get('status'))+'\nConclusion: '+str(status.get('conclusion'))+'\n'
        (self.folder/'logs'/'status.txt').write_text(text,encoding='utf-8');print(text.strip(),flush=True)
        if status.get('status')=='completed':
            try:
                full=self.call(['run','view',self.run,'--repo',self.repo,'--log']);(self.folder/'logs'/'github-full-log.txt').write_text(full,encoding='utf-8')
            except RuntimeError as exc:
                print('Full GitHub log not available yet; will retry: '+str(exc),flush=True);return False
            return True
        return False


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--run',required=True);parser.add_argument('--repo',default='chottuapp/ChotuApp-Software');parser.add_argument('--folder',type=Path);parser.add_argument('--interval',type=int,default=60);args=parser.parse_args()
    if not re.fullmatch(r'\d+',args.run) or not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+',args.repo):parser.error('Invalid run ID or repository')
    if args.interval<30:parser.error('Polling interval must be at least 30 seconds')
    folder=args.folder or Path.home()/'Desktop'/'ANAS_DATA_FETCH'/('Cloud_'+args.run)
    sync=Sync(find_gh(),args.repo,args.run,folder);print('Files: '+str(folder)+'\nLogs: '+str(folder/'logs')+'\nKeep this CMD open for local downloads. Ctrl+C stops sync only; cloud fetching continues.',flush=True)
    try:
        while True:
            try:
                if sync.tick():print('Cloud run finished; available files and logs downloaded.',flush=True);return
            except (RuntimeError,ValueError,OSError) as exc:print('Sync will retry: '+str(exc),flush=True)
            time.sleep(args.interval)
    except KeyboardInterrupt:print('\nLocal sync stopped. Cloud run was not cancelled.')

if __name__=='__main__':main()
