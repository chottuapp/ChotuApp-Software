"""Copy only verified completed files; do not stop or restart active extraction."""
import argparse,datetime,hashlib,json,os,shutil,sqlite3,time
from pathlib import Path
from diagnostics import atomic_json,build_report


def saved_state(data):
    database=Path(data)/'saved_runs'/'run_state.sqlite3'
    if not database.exists():return {}
    try:
        with sqlite3.connect(database.resolve().as_uri()+'?mode=ro',uri=True,timeout=30) as db:row=db.execute('SELECT payload FROM state WHERE id=1').fetchone()
    except sqlite3.OperationalError:return {}
    return json.loads(row[0]) if row else {}


def snapshot(data):
    data=Path(data).resolve();state=saved_state(data);exports=data/'live-excel';exports.mkdir(exist_ok=True);copied=[]
    for site in state.get('sites',[]):
        record=site.get('output') or {};source=Path(record.get('path',''))
        if site.get('status')!='done' or not source.is_file() or source.resolve().parent!=(data/'ANAS_DATA_FETCH').resolve():continue
        stat=source.stat()
        if stat.st_size!=record.get('size') or stat.st_mtime_ns!=record.get('mtime_ns'):continue
        destination=exports/source.name
        if not destination.exists() or destination.stat().st_size!=stat.st_size or destination.stat().st_mtime_ns!=stat.st_mtime_ns:
            temporary=destination.with_suffix('.pending');shutil.copy2(source,temporary);os.replace(temporary,destination)
        copied.append({'name':source.name,'size':stat.st_size,'mtime_ns':stat.st_mtime_ns})
        safe=source.stem;audits=data/'ANAS_DATA_FETCH'/'audits'/safe
        if audits.is_dir():
            for report in audits.glob('*.csv'):
                if report.is_symlink():continue
                dest=exports/'audits'/safe/report.name;dest.parent.mkdir(parents=True,exist_ok=True)
                temporary=dest.with_suffix('.pending');shutil.copy2(report,temporary);os.replace(temporary,dest)

    signature=hashlib.sha256(json.dumps(copied,sort_keys=True).encode()).hexdigest();previous=data/'live-files-signature.json'
    try:old=json.loads(previous.read_text()).get('signature')
    except (OSError,ValueError):old=None
    changed=bool(copied) and signature!=old
    atomic_json(previous,{'signature':signature})
    build_report(data,data/'live-diagnostics')
    from diagnostics import redact,safe_text
    status_lines=[
        'Updated (UTC): '+datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'Saved Excel files: '+str(len(copied)),
        'Saved means exported; review/audit warnings must still be checked.',
        '',
        'SAVED FILES',
    ]
    status_lines.extend(str(index)+'. '+safe_text(item['name'],200) for index,item in enumerate(copied,1))
    if not copied:status_lines.append('None yet.')
    status_lines.extend(['','STORE STATUS'])
    try:telemetry=json.loads((data/'telemetry.json').read_text()).get('stores',{})
    except (OSError,ValueError):telemetry={}
    for site in state.get('sites',[]):
        status_lines.append(redact(safe_text(site.get('name','Store'))+': '+safe_text(site.get('status','unknown'))))
        stats=telemetry.get(site.get('name'),{});progress=stats.get('task_progress',{})
        if stats.get('current_stage') and site.get('status')!='done':status_lines.append('  Stage: '+safe_text(stats['current_stage']))
        if progress and site.get('status')!='done':
            age=max(0,int(time.time()-progress['updated_epoch']))
            status_lines.append('  '+safe_text(progress.get('stage'))+': '+str(progress.get('done'))+'/'+str(progress.get('total'))+' tasks; sample age '+str(age)+'s')
            eta=progress.get('eta_seconds')
            if site.get('status')=='running' and eta is not None and age<180:
                status_lines.append('  Approximate ETA for this stage only: '+str(round(eta/60,1))+' minutes; excludes later processing/audits')
            else:status_lines.append('  ETA unavailable or sample stale; not an overall completion estimate.')
        if stats.get('last_success_epoch'):
            stamp=datetime.datetime.fromtimestamp(stats['last_success_epoch'],datetime.timezone.utc).isoformat()
            status_lines.append('  Last successful HTTP response (UTC): '+stamp)
    (data/'live-diagnostics'/'store-status.txt').write_text('\n'.join(status_lines)+'\n',encoding='utf-8')
    if (data/'console.txt').is_file():
        # Export messages are already retained in fetch-full.log; include a tail for startup failures too.
        from diagnostics import redact
        lines=(data/'console.txt').read_text(encoding='utf-8',errors='replace').splitlines()
        (data/'live-diagnostics'/'console-tail.txt').write_text('\n'.join(redact(line) for line in lines[-80:]),encoding='utf-8')
    return {'finished':(data/'background-result.json').exists(),'files_changed':changed,'completed_files':len(copied)}


def wait_and_snapshot(data,seconds=300):
    data=Path(data);deadline=time.monotonic()+seconds;next_control_check=0
    while not (data/'background-result.json').exists() and time.monotonic()<deadline:
        if time.monotonic()>=next_control_check:
            from remote_control import check_stop_request
            check_stop_request(data);next_control_check=time.monotonic()+30
        try:
            process=json.loads((data/'background-process.json').read_text());os.kill(int(process['pid']),0)
        except ProcessLookupError:
            atomic_json(data/'background-result.json',{'exit_code':1,'reason':'Supervisor exited unexpectedly'});break
        except (OSError,ValueError,KeyError):pass
        time.sleep(min(2,max(0,deadline-time.monotonic())))
    result=snapshot(data)
    print('Live snapshot:',json.dumps(result),flush=True)
    state=saved_state(data)
    for site in state.get('sites',[]):print(site.get('name','Store')+': '+str(site.get('status'))+' — '+str(site.get('progress',0))+'%',flush=True)
    if os.environ.get('GITHUB_OUTPUT'):
        with Path(os.environ['GITHUB_OUTPUT']).open('a') as stream:
            for key,value in result.items():stream.write(key+'='+str(value).lower()+'\n')
    return result

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--data',type=Path,required=True);parser.add_argument('--seconds',type=int,default=300);args=parser.parse_args();wait_and_snapshot(args.data,args.seconds)
