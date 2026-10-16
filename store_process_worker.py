"""One isolated store attempt. Parent owns queue state; child owns HTTP/cache/export globals."""
import importlib.util,json,os,re,sys,threading,time,traceback
from pathlib import Path
from types import SimpleNamespace


def main():
    request=json.loads(sys.stdin.readline());folder=Path(request['folder']);folder.mkdir(parents=True,exist_ok=True)
    engine=Path(request['engine']).resolve();sys.path.insert(0,str(engine.parent))
    spec=importlib.util.spec_from_file_location('_chotu_isolated_engine',engine)
    module=importlib.util.module_from_spec(spec);exec(compile(engine.read_bytes(),str(engine),'exec'),module.__dict__);g=module.__dict__
    from resume_support import ResponseCache
    tls=g['_chotu_tls'];abort=threading.Event();write_lock=threading.Lock()
    def emit(kind,**data):
        with write_lock:
            sys.stdout.write(json.dumps(dict(type=kind,**data),ensure_ascii=True)+'\n');sys.stdout.flush()
    from software_revision_support import prepare_revision
    revision,previous=prepare_revision(engine,folder)
    tls.software_revision=revision
    emit('version',revision=revision,previous=previous)
    emit('log',text='SOFTWARE VERSION: '+revision+' — installed code loaded'+('; updated checks will revalidate saved responses' if previous and previous!=revision else ''))
    original_wait=g['_chotu_wait']
    def wait():
        if abort.is_set():raise RuntimeError('Store worker stopped; successful checkpoints retained')
        original_wait()
        if abort.is_set():raise RuntimeError('Store worker stopped; successful checkpoints retained')
    g['_chotu_wait']=wait
    def controls():
        try:
            for line in sys.stdin:
                command=json.loads(line).get('command')
                if command=='pause':g['_chotu_pause_gate'].clear()
                elif command=='resume':g['_chotu_pause_gate'].set()
                elif command=='stop':abort.set();g['_chotu_pause_gate'].set();return
        finally:abort.set();g['_chotu_pause_gate'].set()
    threading.Thread(target=controls,daemon=True).start()
    old_open=g['_chotu_open_checkpoint']
    def opened(base,name):
        result=old_open(base,name)
        # Two stores can run together; avoid multiplying five workers per store.
        tls.fast_worker_count=min(2,getattr(tls,'fast_worker_count',1))
        return result
    g['_chotu_open_checkpoint']=opened
    result={'ok':False,'reviewed':False,'paused':False,'blocked':False,'retry_after_epoch':0,'detail':''};announced=[]
    class Events:
        def put(self,item):
            if isinstance(item,tuple) and item[0]=='__JOB_RESULT__':result['ok']=bool(item[1]);return
            if isinstance(item,tuple) and item[0]=='__DEBUG__':emit('debug',text=str(item[1]));return
            text=str(item)
            if 'SAVED REVIEW EXCEL:' in text or text.startswith('COMPLETED: '):announced.append(text)
            if 'SAVED REVIEW EXCEL:' in text or 'REVIEW REQUIRED:' in text:result['reviewed']=True
            if text.startswith('FAILED:'):
                result['detail']=text
                result['blocked']='SOURCE BLOCKED:' in text
                if 'SOURCE PAUSED:' in text:
                    result['paused']=True;gate=getattr(tls,'fast_gate',None)
                    match=re.search(r'after at least ([0-9.]+)s',text)
                    delay=max(1,gate.cooldown-time.monotonic()) if gate else float(match[1]) if match else 60
                    result['retry_after_epoch']=time.time()+delay
            if text.startswith('FRESH FETCH:') and request.get('resuming'):
                text='CONTINUE SAVED RUN: successful responses reused; unfinished requests retried.'
            emit('log',text=text)
    g['OUT']=Path(request['output_root']);g['OUT'].mkdir(parents=True,exist_ok=True)
    events=Events();app=SimpleNamespace(events=events,_output_snapshot=g['App']._output_snapshot)
    tls.saved_api_path=folder/'api.sqlite3';tls.saved_response_cache=ResponseCache(folder/'pages.sqlite3')
    tls.saved_run_note=lambda text:emit('debug',text=text)
    try:
        g['App']._run_checked(app,request['site'],request['template'])
        if result['ok'] and not announced:
            result.update(ok=False,detail='Child did not announce an exported workbook')
    except Exception as exc:
        result.update(ok=False,detail=str(exc));emit('debug',text=traceback.format_exc())
    finally:
        tls.saved_response_cache.close();tls.saved_response_cache=None
    emit('result',**result)
    return 0 if result['ok'] else 2

if __name__=='__main__':
    try:sys.exit(main())
    except Exception:
        print(json.dumps({'type':'result','ok':False,'reviewed':False,'paused':False,'detail':traceback.format_exc()}),flush=True);sys.exit(2)
