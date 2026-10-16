"""Run fetching on a cloud runner without a web server or desktop window."""
import argparse,json,signal,sys,time,zipfile,os,sqlite3
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from runtime import CloudService


def parse_stores(text):
    if text.lstrip().startswith('['):return json.loads(text)
    result=[]
    for line in text.replace(';','\n').splitlines():
        if not line.strip():continue
        name,separator,url=line.partition('|')
        if not separator:raise ValueError('Use Name | https://website.com, separated by semicolons')
        result.append({'name':name.strip(),'url':url.strip()})
    return result


def checkpoint(data,destination,max_bytes=250*1024*1024):
    data=Path(data);destination=Path(destination);temporary=destination.with_suffix('.pending.zip')
    try:
        with zipfile.ZipFile(temporary,'w',zipfile.ZIP_DEFLATED) as archive:
            for folder in (data/'saved_runs',data/'runtime'/'source_pacing',data/'ANAS_DATA_FETCH'):
                for path in folder.rglob('*'):
                    if path.is_file() and not path.is_symlink() and path.name!='active.lock':archive.write(path,path.relative_to(data).as_posix())
            for name in ('template.xlsx','controls.json'):
                if (data/name).is_file():archive.write(data/name,name)
        if temporary.stat().st_size>max_bytes:raise ValueError('Checkpoint exceeds 250 MB; outputs remain available, but this run has no downloadable resume checkpoint')
        temporary.replace(destination)
    finally:temporary.unlink(missing_ok=True)


def _restore_unlocked(archive,data):
    data=Path(data).resolve();data.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(archive) as zipped:
        if sum(item.file_size for item in zipped.infolist())>4*1024**3:raise ValueError('Checkpoint exceeds 4 GB expanded size')
        for item in zipped.infolist():
            path=Path(item.filename)
            allowed=(path.parts[:1] in [('saved_runs',),('ANAS_DATA_FETCH',)] or path.parts[:2]==('runtime','source_pacing') or item.filename in ('template.xlsx','controls.json'))
            if not allowed or path.is_absolute() or '..' in path.parts or '\\' in item.filename or (item.external_attr>>16)&0o170000==0o120000:raise ValueError('Unsafe checkpoint entry')
            target=(data/path).resolve()
            if data not in target.parents:raise ValueError('Checkpoint path escaped data folder')
        for item in zipped.infolist():
            target=data/item.filename
            if item.is_dir():target.mkdir(parents=True,exist_ok=True)
            else:target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(zipped.read(item))

    database=data/'saved_runs'/'run_state.sqlite3'
    if database.exists():
        with sqlite3.connect(database) as db:
            row=db.execute('SELECT payload FROM state WHERE id=1').fetchone()
        state=json.loads(row[0]) if row else {}
        for site in state.get('sites',[]):
            output=site.get('output') or {};file=data/'ANAS_DATA_FETCH'/Path(output.get('path','')).name
            if file.is_file() and file.stat().st_size==output.get('size'):
                os.utime(file,ns=(file.stat().st_atime_ns,output['mtime_ns']))


def restore(archive,data):
    from resume_support import RunLease
    folder=Path(data)/'saved_runs';folder.mkdir(parents=True,exist_ok=True);lease=RunLease(folder);lease.acquire()
    try:_restore_unlocked(archive,data)
    finally:lease.release()


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--data',type=Path,default=Path('.cloud-data'));parser.add_argument('--stores',default='');parser.add_argument('--continue-saved',action='store_true');parser.add_argument('--minutes',type=int,default=285);parser.add_argument('--checkpoint',type=Path);parser.add_argument('--restore',type=Path)
    args=parser.parse_args()
    if not 1<=args.minutes<=300:parser.error('Minutes must be between 1 and 300')
    if args.restore:restore(args.restore,args.data)
    service=CloudService(args.data)
    def stop(*unused):service.control('stop')
    signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop)
    result=1
    try:
        service.start(parse_stores(args.stores),resume=args.continue_saved);deadline=time.monotonic()+args.minutes*60;seen=0
        while service.running:
            snapshot=service.snapshot()
            for message in snapshot['logs']:
                if message['id']>seen:print(message['text'],flush=True);seen=message['id']
            if time.monotonic()>=deadline:print('Cloud time budget reached; saving unfinished work.',flush=True);service.control('stop');break
            time.sleep(.5)
        service.close();state=service.store.load();result=0 if state and state['status']=='complete' else 2
        if args.checkpoint:
            try:checkpoint(args.data,args.checkpoint);print('Checkpoint saved:',args.checkpoint,flush=True)
            except ValueError as exc:print('CHECKPOINT NOT SAVED:',exc,flush=True);result=2
        print('Run complete. Excel files:',service.output,flush=True)
    finally:
        if service.running:service.close()
        elif service.lease.file:service.close()
    return result

if __name__=='__main__':sys.exit(main())
