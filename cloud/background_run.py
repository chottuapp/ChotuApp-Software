"""One continuous extractor while workflow steps publish periodic snapshots."""
import json,os,signal,subprocess,sys,time,traceback
from pathlib import Path
from diagnostics import atomic_json


def launch(data):
    data=Path(data).resolve();data.mkdir(parents=True,exist_ok=True)
    result=data/'background-result.json';result.unlink(missing_ok=True);(data/'stop-request').unlink(missing_ok=True)
    with (data/'launcher.log').open('ab') as stream:
        process=subprocess.Popen([sys.executable,str(Path(__file__).resolve()),'supervise',str(data)],stdin=subprocess.DEVNULL,stdout=stream,stderr=subprocess.STDOUT,start_new_session=True)
    atomic_json(data/'background-process.json',{'pid':process.pid});print('Continuous cloud fetch started; snapshots will be uploaded periodically.',flush=True)


def supervise(data):
    data=Path(data).resolve();args=[sys.executable,str(Path(__file__).with_name('cli.py')),'--data',str(data),'--minutes',os.environ['CLOUD_MINUTES']]
    if os.environ.get('RESUME_RUN_ID'):
        from prepare_resume import prepared
        if prepared(data,os.environ['RESUME_RUN_ID']):args+=['--continue-saved']
        else:args+=['--restore',str(Path(os.environ['RUNNER_TEMP'])/'chotu-restore'),'--continue-saved']
    else:args+=['--stores',os.environ.get('CLOUD_STORES','')]
    if os.environ.get('SAVE_CHECKPOINT')=='true':args+=['--checkpoint',str(Path.cwd()/'checkpoint.zip')]
    process=None
    def stop(*args):
        if process and process.poll() is None:process.terminate()
    signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop)
    code=1
    try:
        with (data/'console.txt').open('ab') as stream:
            process=subprocess.Popen(args,stdin=subprocess.DEVNULL,stdout=stream,stderr=subprocess.STDOUT)
            requested=False
            while process.poll() is None:
                if (data/'stop-request').exists() and not requested:requested=True;stop()
                time.sleep(.5)
            code=process.returncode
    except Exception:
        with (data/'console.txt').open('a',encoding='utf-8') as stream:stream.write(traceback.format_exc())
    finally:atomic_json(data/'background-result.json',{'exit_code':code})
    return code


def finish(data,timeout=900,poll=.5):
    data=Path(data);path=data/'background-result.json';deadline=time.monotonic()+timeout;next_report=0
    try:phase=json.loads((data/'fetch-phase.json').read_text()).get('phase')
    except (OSError,ValueError):phase=None
    if not path.exists() and phase not in ('stopping','checkpoint','finished'):(data/'stop-request').touch()
    while not path.exists() and time.monotonic()<deadline:
        if time.monotonic()>=next_report:
            try:phase=json.loads((data/'fetch-phase.json').read_text()).get('phase','unknown')
            except (OSError,ValueError):phase='unknown'
            print('Waiting for extraction/checkpoint finalization; phase='+str(phase)+'. Workflow will not upload early.',flush=True);next_report=time.monotonic()+15
        time.sleep(poll)
    # Surface the real CLI outcome in the workflow log, including checkpoint failures.
    if (data/'console.txt').is_file():
        from diagnostics import redact
        from collections import deque
        with (data/'console.txt').open(encoding='utf-8',errors='replace') as stream:tail=deque(stream,maxlen=80)
        for line in tail:print(redact(line.rstrip()),flush=True)
    if not path.exists():
        print('FINALIZATION TIMEOUT: no supervisor result after '+str(timeout)+' seconds; checkpoint upload is not confirmed.',flush=True)
        return 2
    return json.loads(path.read_text())['exit_code']

if __name__=='__main__':
    mode=sys.argv[1];data=Path(sys.argv[2])
    if mode=='start':launch(data)
    elif mode=='supervise':sys.exit(supervise(data))
    elif mode=='finish':sys.exit(finish(data))
