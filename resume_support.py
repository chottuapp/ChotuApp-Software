"""Durable selected-store runs; additive UI/runtime support for existing extractor."""
import contextlib
import copy
import queue
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import tempfile
import threading
import time
import uuid


class RunStore:
    def __init__(self, root):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.database = self.root / 'run_state.sqlite3'
        self.lock = threading.RLock()
        self.ui_snapshot = None
        with self.connect() as db:
            db.execute('CREATE TABLE IF NOT EXISTS state (id INTEGER PRIMARY KEY, payload TEXT NOT NULL)')

    @contextlib.contextmanager
    def connect(self):
        db = sqlite3.connect(self.database, timeout=30)
        db.execute('PRAGMA synchronous=FULL')
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def load(self):
        with self.lock, self.connect() as db:
            row = db.execute('SELECT payload FROM state WHERE id=1').fetchone()
            state = json.loads(row[0]) if row else None
            self.ui_snapshot = copy.deepcopy(state)
            return state

    def save(self, state):
        with self.lock, self.connect() as db:
            db.execute('INSERT OR REPLACE INTO state VALUES(1,?)', (json.dumps(state),))
        self.ui_snapshot = copy.deepcopy(state)

    def update(self, mutate):
        with self.lock:
            state = self.load()
            if state:
                mutate(state)
                self.save(state)

    def fresh(self, sites, template):
        run_id = uuid.uuid4().hex
        folder = self.root / run_id
        folder.mkdir()
        snapshot = folder / 'template.xlsx'
        shutil.copy2(template, snapshot)
        with snapshot.open('r+b') as stream:
            stream.flush();os.fsync(stream.fileno())
        state = {'id':run_id, 'created':time.time(), 'status':'incomplete',
                 'template':str(snapshot.resolve()), 'original_template':str(Path(template).resolve()),
                 'sites':[dict(site, status='pending', progress=0, detail='Waiting', output=None, reviewed=False)
                          for site in sites]}
        self.save(state)
        return state

    @staticmethod
    def output_valid(site):
        output = site.get('output')
        if not output:
            return False
        try:
            stat = Path(output['path']).stat()
            return stat.st_size == output['size'] and stat.st_mtime_ns == output['mtime_ns']
        except (OSError, KeyError):
            return False

    def pending(self, state):
        return [i for i,site in enumerate(state['sites'])
                if site.get('status') != 'done' or not self.output_valid(site)]


class RunLease:
    """Prevent two application processes from writing the same saved run."""
    def __init__(self, root):
        self.path=Path(root)/'active.lock'; self.file=None
    def acquire(self):
        self.file=open(self.path,'a+b')
        self.file.seek(0,2)
        if self.file.tell()==0:self.file.write(b'0');self.file.flush()
        self.file.seek(0)
        try:
            if os.name=='nt':
                import msvcrt
                msvcrt.locking(self.file.fileno(),msvcrt.LK_NBLCK,1)
            else:
                import fcntl
                fcntl.flock(self.file.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
        except OSError:
            self.file.close();self.file=None
            raise RuntimeError('Another ChotuApp process is running this queue. Close the extra app first.')
    def release(self):
        if self.file:
            try:
                if os.name=='nt':
                    import msvcrt
                    self.file.seek(0);msvcrt.locking(self.file.fileno(),msvcrt.LK_UNLCK,1)
                else:
                    import fcntl
                    fcntl.flock(self.file.fileno(),fcntl.LOCK_UN)
            finally:self.file.close();self.file=None


class ResponseCache:
    def __init__(self, path):
        self.db=sqlite3.connect(path,timeout=30)
        self.db.execute('PRAGMA synchronous=FULL')
        self.db.execute('CREATE TABLE IF NOT EXISTS pages(url TEXT PRIMARY KEY, final_url TEXT, body BLOB, encoding TEXT, content_type TEXT, checksum TEXT)')
        self.db.commit()
    def get(self,url):
        row=self.db.execute('SELECT final_url,body,encoding,content_type,checksum FROM pages WHERE url=?',(url,)).fetchone()
        if not row:return None
        final,body,encoding,ctype,checksum=row
        if hashlib.sha256(body).hexdigest()!=checksum:
            self.db.execute('DELETE FROM pages WHERE url=?',(url,));self.db.commit();return None
        import requests
        response=requests.Response();response.status_code=200;response.url=final
        response._content=body;response.encoding=encoding
        if ctype:response.headers['Content-Type']=ctype
        return response
    def put(self,url,response):
        # Never checkpoint 403/429, partial failures, credentials or cookies.
        if response.status_code!=200:return
        body=response.content
        from urllib.parse import urlsplit
        if urlsplit(url).path.endswith(('.json','.js')):
            try:
                if not isinstance(response.json(),(dict,list)):return
            except (ValueError,TypeError):return
        if b'cf-chl-' in body or b'<title>Just a moment' in body:
            return
        self.db.execute('INSERT OR REPLACE INTO pages VALUES(?,?,?,?,?,?)',
                        (url,response.url,body,response.encoding,response.headers.get('Content-Type'),hashlib.sha256(body).hexdigest()))
        self.db.commit()
    def close(self):self.db.close()


class SessionProxy:
    def __init__(self,session,tls,pause):self.session=session;self.tls=tls;self.pause=pause
    def __getattr__(self,name):return getattr(self.session,name)
    def get(self,url,**kwargs):
        cache=getattr(self.tls,'saved_response_cache',None)
        if not cache or kwargs.get('params') or kwargs.get('stream') or kwargs.get('auth'):
            return self.session.get(url,**kwargs)
        from urllib.parse import urlsplit
        parsed=urlsplit(url)
        if parsed.username or parsed.password:return self.session.get(url,**kwargs)
        self.pause()
        response=cache.get(url)
        if response is not None:
            callback=getattr(self.tls,'saved_run_note',None)
            if callback:callback('SAVED RESPONSE: '+url)
            return response
        response=self.session.get(url,**kwargs)
        cache.put(url,response)
        return response


class EventProxy:
    def __init__(self,queue,app):self.queue=queue;self.app=app
    def __getattr__(self,name):return getattr(self.queue,name)
    def get_nowait(self):
        # Yield to Tk even when cached responses flood the event queue.
        if getattr(self, "batch_remaining", 1) <= 0 or time.monotonic() > getattr(self, "batch_deadline", float("inf")):
            raise queue.Empty
        self.batch_remaining = getattr(self, "batch_remaining", 1) - 1
        item=self.queue.get_nowait()
        if isinstance(item,tuple) and len(item)==3 and item[0]=='__STORE_STATUS__':
            self.app.set_live_status(item[1],item[2])
            return ('__DEBUG__',item[2])
        return item

    def put(self,item,*args,**kwargs):
        if getattr(self.app,'_saved_run_active',False):
            attempt=getattr(self.app,'_source_attempt',None)
            if attempt is not None and isinstance(item,str) and item.startswith('FAILED:') and 'SOURCE PAUSED:' in item:
                attempt['paused']=True;attempt['detail']=item.split('SOURCE PAUSED:',1)[1].strip()
                gate=self.app._source_gate()
                if gate is not None:attempt['retry_at']=gate.cooldown
                else:
                    import re
                    match=re.search(r'after at least ([0-9.]+)s',item)
                    attempt['retry_at']=time.monotonic()+(float(match.group(1)) if match else 60)
                item='WEBSITE COOLDOWN: '+item.removeprefix('FAILED: ')
            if isinstance(item,tuple) and len(item)==3 and item[0]=='__JOB_RESULT__' and not item[1]:
                if attempt is not None and attempt.get('paused'):
                    self.app._save_run_event(('__SOURCE_PAUSED__',attempt['retry_at'],attempt['detail']))
                    return self.queue.put(('__DEBUG__','Website cooldown — saved requests retained; other stores continue'),*args,**kwargs)
                self.app._non_source_failed=True
            if isinstance(item,str) and item.startswith('FRESH FETCH:') and getattr(self.app,'_resuming_saved',False):
                item='CONTINUE SAVED RUN: previous successful responses reused; unfinished requests retried.'
            elif isinstance(item,str) and item.startswith('CHECKPOINT:'):
                item=item.split(' (',1)[0]+' (durable saved run)'
            elif isinstance(item,str) and item.startswith('__CHOTU_PROGRESS__|'):
                _,pct,detail=item.split('|',2)
                floor=getattr(self.app,'_saved_progress_floor',0)
                if int(pct)<floor:
                    item='__CHOTU_PROGRESS__|'+str(floor)+'|Restoring saved responses: '+detail
        self.app._save_run_event(item)
        return self.queue.put(item,*args,**kwargs)


class ChangedLabel:
    """Avoid redrawing an unchanged dashboard counter for every log line."""
    def __init__(self, widget):
        self.widget=widget
        self.previous=None
    def configure(self, **kwargs):
        if kwargs != self.previous:
            self.widget.configure(**kwargs)
            self.previous=dict(kwargs)
    def __getattr__(self, name):
        return getattr(self.widget, name)


def enable_resume(g):
    App=g['App'];tls=g['_chotu_tls'];messagebox=g['messagebox']
    original_init=App.__init__;original_launch=App._launch_jobs
    original_poll=App.poll
    original_session_factory=g['requests'].Session
    # Session-level cache also covers storefront image, ranking and audit pages.
    g['S']=SessionProxy(g['S'],tls,g['_chotu_wait'])
    def session_factory(*args,**kwargs):
        return SessionProxy(original_session_factory(*args,**kwargs),tls,g['_chotu_wait'])
    g['requests'].Session=session_factory

    def open_checkpoint(base,name):
        path=getattr(tls,'saved_api_path',None)
        if path is None:return original_open(base,name)
        db=sqlite3.connect(path,timeout=30);db.execute('PRAGMA synchronous=FULL')
        db.execute('CREATE TABLE IF NOT EXISTS responses(url TEXT PRIMARY KEY,payload BLOB NOT NULL)');db.commit()
        tls.db=db;tls.checkpoint_path=Path(path)
        note=getattr(tls,'saved_run_note',None)
        if note:note('SAVED RUN: completed requests are durable; an incomplete request will be retried.')
        return Path(path)
    original_open=g['_chotu_open_checkpoint'];g['_chotu_open_checkpoint']=open_checkpoint

    def init(self,root):
        original_init(self,root)
        self.saved_runs=RunStore(Path(g['__file__']).resolve().parent/'saved_runs')
        self._saved_run_active=False
        self._saved_store_index=None
        self._saved_lease=None
        self.saved_runs.load()  # Initial read before any worker can hold the lock.
        self._source_gate=lambda:getattr(tls,'fast_gate',None)
        self._source_auto_retry_limit=2
        self._source_auto_wait_limit=120
        self._source_attempt=None;self._source_final_paused=False;self._non_source_failed=False
        self.events=EventProxy(self.events,self)
        for key, widget in self.metric_values.items():
            self.metric_values[key]=ChangedLabel(widget)
        import customtkinter as ctk
        self.saved_controls=ctk.CTkFrame(root,fg_color='#10271b',corner_radius=8)
        self.saved_controls.pack(side='top',fill='x',padx=18,pady=(2,4))
        self.fresh_run_button=ctk.CTkButton(self.saved_controls,text='New Fresh Run (selected)',width=215,height=38,command=self.start_selected)
        self.fresh_run_button.pack(side='left',padx=8,pady=5)
        self.continue_run_button=ctk.CTkButton(self.saved_controls,text='Continue Saved Run',width=205,height=38,command=self.continue_saved_run)
        self.continue_run_button.pack(side='left',padx=8,pady=5)
        self.saved_run_label=ctk.CTkLabel(self.saved_controls,text='',anchor='w',wraplength=370)
        self.saved_run_label.pack(side='left',fill='x',expand=True,padx=10)
        # Reserve the fixed controls before allocating remaining page space.
        self._wheel_workspace.pack_forget();self._wheel_workspace.pack(fill='both',expand=True)
        if hasattr(self,'_tag_wheel_widgets'):self._tag_wheel_widgets(self.saved_controls)
        root.title(root.title()+' | Saved Runs')
        self.refresh_saved_controls()
        root.after(1000,self._saved_run_ui_tick)

    def refresh_controls(self):
        state=copy.deepcopy(self.saved_runs.ui_snapshot)
        if self.running:
            self.fresh_run_button.configure(state='disabled');self.continue_run_button.configure(state='disabled')
            if state:
                saved=sum(site.get('status')=='done' for site in state['sites'])
                self.saved_run_label.configure(text=f"Files saved: {saved}/{len(state['sites'])} — ANAS_DATA_FETCH (each store saved immediately)")
            return
        pending=self.saved_runs.pending(state) if state else []
        self.fresh_run_button.configure(state='normal')
        self.continue_run_button.configure(state='normal' if pending else 'disabled')
        if pending:
            done=len(state['sites'])-len(pending)
            details=state['sites'][pending[0]]
            self.saved_run_label.configure(text=f"Saved: {done}/{len(state['sites'])} stores complete; {details.get('progress',0)}% — {details.get('detail','Waiting')}")
        else:self.saved_run_label.configure(text='No incomplete saved run' if not state else 'Saved run completed')

    def poll(self):
        self.events.batch_remaining=40
        self.events.batch_deadline=time.monotonic()+0.020
        was_running=self.running
        result=original_poll(self)
        if was_running and not self.running and self._source_final_paused and not self._non_source_failed:
            self.set_live_status('review','Website cooldown — saved work retained')
            state=self.saved_runs.ui_snapshot or {}
            sites=state.get('sites',[])
            complete=sum(site.get('status')=='done' for site in sites)
            self.progress_value.set(int(100*complete/max(1,len(sites))))
            self.progress_label.configure(text=f'Saved {complete}/{len(sites)} stores — website cooldown; Continue Saved Run later')
        return result

    def ui_tick(self):
        self.refresh_saved_controls()
        self.root.after(1000,self._saved_run_ui_tick)

    def record_event(self,item):
        if not getattr(self,'_saved_run_active',False) or self._saved_store_index is None:return
        index=self._saved_store_index
        def update(state):
            site=state['sites'][index]
            if isinstance(item,tuple) and len(item)==3 and item[0]=='__SOURCE_PAUSED__':
                site.update(status='source_paused',detail='Website cooldown — '+str(item[2]),retry_after_epoch=time.time()+max(0,item[1]-time.monotonic()))
            elif isinstance(item,str) and item.startswith('__CHOTU_PROGRESS__|'):
                _,pct,detail=item.split('|',2);site.update(progress=int(pct),detail=detail)
            elif isinstance(item,str) and ('SAVED REVIEW EXCEL:' in item or 'REVIEW REQUIRED:' in item):
                site['reviewed']=True
            elif isinstance(item,tuple) and len(item)==3 and item[0]=='__JOB_RESULT__':
                ok=item[1];site['status']='done' if ok else 'failed'
                if ok:
                    import re
                    name=re.sub(r'[^\w .-]','',site['name']).strip() or 'Shopify'
                    output=Path(g['OUT'])/(name+'.xlsx')
                    if output.is_file():
                        stat=output.stat();site['output']={'path':str(output.resolve()),'size':stat.st_size,'mtime_ns':stat.st_mtime_ns}
                    site['progress']=100
        if (isinstance(item,tuple) and len(item)==3 and item[0]=='__SOURCE_PAUSED__') or isinstance(item,str) and (item.startswith('__CHOTU_PROGRESS__|') or 'SAVED REVIEW EXCEL:' in item or 'REVIEW REQUIRED:' in item) or isinstance(item,tuple) and len(item)==3 and item[0]=='__JOB_RESULT__':
            self.saved_runs.update(update)
            if isinstance(item,tuple) and len(item)==3 and item[0]=='__JOB_RESULT__' and item[1]:
                state=self.saved_runs.load()
                output=state['sites'][index].get('output') if state else None
                if output:
                    self.events.queue.put('FILE SAVED NOW: '+output['path']+' — remaining stores continue separately')

    def launch(self,chosen,template,saved_state=None):
        if self.running or not chosen:return
        lease=RunLease(self.saved_runs.root)
        try:
            lease.acquire()
            state=saved_state or self.saved_runs.fresh(chosen,template)
            pending=self.saved_runs.pending(state)
            if not pending:lease.release();self.refresh_saved_controls();return
            if not Path(state['template']).is_file():raise RuntimeError('Saved template snapshot is missing. Start a new fresh run with your template.')
        except Exception as exc:
            lease.release();messagebox.showerror('Saved run',str(exc));return
        self._source_attempt=None;self._source_final_paused=False;self._non_source_failed=False
        self._saved_lease=lease;self._saved_run_active=True;self._resuming_saved=bool(saved_state);self.running=True
        self.job_reviewed=any(site.get('reviewed',False) for site in state['sites']);self.job_failed=False;self.job_completed=0;self.job_expected=len(pending)
        self.refresh.configure(state='disabled');self.refresh_selected.configure(state='disabled')
        self.refresh_saved_controls();self.logbox.delete('1.0','end')
        first=state['sites'][pending[0]]
        self.progress_value.set(first.get('progress',0))
        self.progress_label.configure(text=('Continuing saved run' if saved_state else 'New fresh run')+' — '+str(first.get('progress',0))+'%')
        g['_chotu_pause_gate'].set();self.pause_button.configure(state='normal',text='⏸ Pause')
        self._ui_started=time.monotonic()
        self._ui_products=0;self._ui_collections=0;self._ui_request_count=0;self._ui_429_count=0
        self.set_live_status('working',f'{len(pending)} remaining selected store(s)')
        def worker():
            ready=list(pending);waiting={};attempts={};last_wait_message=None
            try:
                while ready or waiting:
                    if ready:index=ready.pop(0)
                    else:
                        index=min(waiting,key=waiting.get)
                        remaining=waiting[index]-time.monotonic()
                        if remaining>0:
                            bucket=int(remaining/5)
                            if (index,bucket)!=last_wait_message:
                                if last_wait_message is None or last_wait_message[0]!=index:
                                    g['_chotu_debug_stage']('Website cooldown — '+state['sites'][index]['name'])
                                last_wait_message=(index,bucket)
                                self.events.put(('__STORE_STATUS__','working','WEBSITE COOLDOWN: '+state['sites'][index]['name']+' — retry in '+str(int(remaining+1))+'s'))
                            g['_chotu_wait']();time.sleep(min(.25,remaining));continue
                        waiting.pop(index)
                    self._saved_store_index=index
                    current=self.saved_runs.load();site=current['sites'][index]
                    attempts[index]=attempts.get(index,0)+1
                    self._source_attempt={'paused':False}
                    self._saved_progress_floor=site.get('progress',0) if saved_state or attempts[index]>1 else 0
                    def mark(s):s['sites'][index]['status']='running';s['status']='incomplete'
                    self.saved_runs.update(mark)
                    folder=self.saved_runs.root/state['id']/str(index);folder.mkdir(exist_ok=True)
                    tls.saved_api_path=folder/'api.sqlite3'
                    tls.saved_response_cache=ResponseCache(folder/'pages.sqlite3')
                    tls.saved_run_note=lambda text:self.events.put(('__DEBUG__',text))
                    self.events.put(('__STORE_STATUS__','working',site['name']+(' — retrying saved requests' if attempts[index]>1 else '')))
                    self.events.put(('CONTINUE SAVED RUN: ' if saved_state or attempts[index]>1 else 'NEW FRESH RUN: ')+site['name'])
                    try:self._run_checked(site,state['template'])
                    finally:
                        tls.saved_response_cache.close();tls.saved_response_cache=None;tls.saved_api_path=None;tls.saved_run_note=None
                    attempt=self._source_attempt
                    if attempt.get('paused'):
                        remaining=max(0,attempt['retry_at']-time.monotonic())
                        if attempts[index]<=self._source_auto_retry_limit and remaining<=self._source_auto_wait_limit:
                            waiting[index]=attempt['retry_at']+1.0  # avoid retrying on the cooldown boundary
                            self.events.put('WEBSITE COOLDOWN: '+site['name']+' — saved; retry queued after cooldown. Other stores continue.')
                        else:
                            self._source_final_paused=True
                            self.events.queue.put(('__JOB_RESULT__',False,site['name']))
                            self.events.put('WEBSITE COOLDOWN: '+site['name']+' — automatic retry limit reached or server delay is too long; Continue Saved Run later.')
                def finish(s):s['status']='complete' if not self.saved_runs.pending(s) else 'incomplete'
                self.saved_runs.update(finish)
            except Exception as exc:
                self._source_attempt=None
                self.events.put('FAILED: saved-run worker: '+str(exc));self.events.put(('__JOB_RESULT__',False,'Worker'))
            finally:
                self._source_attempt=None;self._saved_run_active=False;self._saved_store_index=None
                lease.release();self._saved_lease=None;self.events.put('__DONE__')
        threading.Thread(target=worker,daemon=True).start()

    def continue_run(self):
        if self.running:return
        state=self.saved_runs.load()
        if not state or not self.saved_runs.pending(state):
            messagebox.showinfo('Saved run','No incomplete saved run is available.');return
        self.template.set(state['original_template'])
        # Restore exactly the saved selection, even if current checkboxes differ.
        urls={site['url'] for site in state['sites']}
        for site in state['sites']:
            if not any(existing['url']==site['url'] for existing in self.sites):self.sites.append({'name':site['name'],'url':site['url']})
        self.redraw()
        for url,var in self.store_checks.items():var.set(url in urls)
        self._selection_changed()
        self._launch_jobs(state['sites'],state['template'],saved_state=state)

    def close(self):
        if self.running and not messagebox.askyesno('Extraction running','Close now? Saved requests and selected stores remain on disk. Continue Saved Run will retry the in-flight request next time.'):
            return
        g['_chotu_pause_gate'].set();self.root.destroy()

    # Local saved pages need no network pacing. Keep all real-request waits,
    # Pause handling, source verification and rate-limit backoff unchanged.
    original_backoff=g['_chotu_backoff']
    original_cover=g.get('storefront_cover')
    def backoff(seconds,reason='Retry'):
        if reason=='Image pacing' and getattr(tls,'replaying_saved_image',False):
            g['_chotu_wait']()
            return
        return original_backoff(seconds,reason)
    if original_cover:
        def cover(base,product,pictures,log):
            cache=getattr(tls,'saved_response_cache',None)
            url=base.rstrip('/')+'/products/'+product['handle']
            previous=getattr(tls,'replaying_saved_image',False)
            tls.replaying_saved_image=cache is not None and cache.get(url) is not None
            try:return original_cover(base,product,pictures,log)
            finally:tls.replaying_saved_image=previous
        g['storefront_cover']=cover
        g['_chotu_backoff']=backoff

    App.__init__=init;App._launch_jobs=launch;App.continue_saved_run=continue_run
    App.refresh_saved_controls=refresh_controls;App._saved_run_ui_tick=ui_tick
    App._save_run_event=record_event;App.close=close;App.poll=poll
