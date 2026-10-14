"""Bounded per-store preloading; preserve canonical extraction and durable caches."""
import email.utils
import json
import os
import tempfile
from urllib.parse import urlparse
import datetime
from pathlib import Path
import sqlite3
import threading
import time


class RequestGate:
    def __init__(self, pause, log, baseline=0.25, state_path=None, error_factory=RuntimeError):
        self.pause=pause;self.log=log;self.baseline=baseline;self.interval=baseline
        self.lock=threading.Lock();self.next_start=0.0;self.cooldown=0.0;self.limited=False
        self.state_path=Path(state_path) if state_path else None;self.error_factory=error_factory
        if self.state_path:
            try:
                state=json.loads(self.state_path.read_text())
                self.baseline=max(baseline,min(3.0,float(state.get('min_spacing',baseline))))
                self.interval=self.baseline
                remaining=float(state.get('retry_after_epoch',0))-time.time()
                if remaining>0:self.cooldown=time.monotonic()+remaining;self.limited=True
            except (OSError,ValueError,TypeError):pass
    def blocked_error(self):
        remaining=max(1,int(self.cooldown-time.monotonic()+0.99))
        return self.error_factory(f'SOURCE PAUSED: website rate limit; retry this saved store after at least {remaining}s. Checkpoint retained; other stores can proceed.')
    def persist_block(self,delay):
        if not self.state_path:return
        self.state_path.parent.mkdir(parents=True,exist_ok=True);temporary=None
        try:
            state={'retry_after_epoch':time.time()+delay,'min_spacing':min(3.0,max(1.0,self.baseline*1.5))}
            with tempfile.NamedTemporaryFile(dir=self.state_path.parent,mode='w',delete=False) as stream:
                temporary=Path(stream.name);json.dump(state,stream);stream.flush();os.fsync(stream.fileno())
            os.replace(temporary,self.state_path)
        except OSError as exc:self.log('FAST FETCH: could not persist source cooldown: '+str(exc))
        finally:
            if temporary:temporary.unlink(missing_ok=True)
    def wait(self,preload=False):
        while True:
            self.pause()
            with self.lock:
                if self.limited:raise self.blocked_error()
                now=time.monotonic();remaining=max(self.next_start,self.cooldown)-now
                if remaining<=0:
                    self.next_start=now+self.interval;return
            time.sleep(min(0.1,remaining))
    def response(self,response):
        if response.status_code in (429,503):
            raw=response.headers.get('Retry-After','').strip();delay=60.0
            try:delay=max(delay,float(raw))
            except ValueError:
                try:delay=max(delay,(email.utils.parsedate_to_datetime(raw)-datetime.datetime.now(datetime.timezone.utc)).total_seconds())
                except (ValueError,TypeError,OverflowError):pass
            with self.lock:
                self.interval=min(12.0,max(2.5,self.interval*1.8));self.cooldown=max(self.cooldown,time.monotonic()+delay);self.limited=True
            self.persist_block(delay)
            self.log(f'FAST FETCH: HTTP {response.status_code}; store paused, checkpoint retained, cooldown {delay:.0f}s; no repeated blocked requests')
        elif response.status_code==200:
            with self.lock:self.interval=max(self.baseline,self.interval*0.98)


class GatedSession:
    def __init__(self,session,tls,pause):self.session=session;self.tls=tls;self.pause=pause
    def __getattr__(self,name):return getattr(self.session,name)
    def get(self,url,**kwargs):
        gate=getattr(self.tls,'fast_gate',None)
        if not gate:return self.session.get(url,**kwargs)
        cache=getattr(self.tls,'saved_response_cache',None)
        if cache is not None and not any(kwargs.get(k) for k in ('params','stream','auth')) and cache.get(url) is not None:
            return self.session.get(url,**kwargs)
        gate.wait(getattr(self.tls,'fast_preloading',False))
        response=self.session.get(url,**kwargs);gate.response(response);return response


class ThreadSession:
    def __init__(self,session,tls):self.session=session;self.tls=tls
    def __getattr__(self,name):return getattr(self.session,name)
    def get(self,url,**kwargs):
        return getattr(self.tls,'fast_session',self.session).get(url,**kwargs)


def enable_fast_fetch(g):
    if g.get('_chotu_fast_fetch_enabled'):return
    from resume_support import ResponseCache
    tls=g['_chotu_tls'];factory=g['requests'].Session
    original_init=g['App'].__init__
    def init(self,root):
        original_init(self,root)
        root.title(root.title()+' | Fast Fetch (2 workers)')
    g['App'].__init__=init
    def session_factory(*args,**kwargs):return GatedSession(factory(*args,**kwargs),tls,g['_chotu_wait'])
    g['requests'].Session=session_factory
    g['S']=ThreadSession(GatedSession(g['S'],tls,g['_chotu_wait']),tls)
    old_open=g['_chotu_open_checkpoint'];old_close=g['_chotu_close_checkpoint']
    old_discover=g['discover'];old_collections=g['collections'];old_backoff=g['_chotu_backoff']
    old_debug_request=g['_chotu_debug_request'];old_debug_response=g['_chotu_debug_response']

    def debug_request(url,attempt):
        if not getattr(tls,'fast_preloading',False):return old_debug_request(url,attempt)
        tls.fast_http_start=(url,time.monotonic())
        g['_chotu_debug']('HTTP START attempt='+str(attempt)+' '+url)
    def debug_response(status,size=0,cached=False):
        if not getattr(tls,'fast_preloading',False):return old_debug_response(status,size,cached)
        url,started=getattr(tls,'fast_http_start',('',time.monotonic()))
        g['_chotu_debug']('HTTP END status='+str(status)+' elapsed='+format(time.monotonic()-started,'.1f')+'s bytes='+str(size)+' '+url)
    g['_chotu_debug_request']=debug_request;g['_chotu_debug_response']=debug_response

    def open_checkpoint(base,name):
        result=old_open(base,name)
        host=(urlparse(base).hostname or 'unknown').lower().removeprefix('www.')
        floor=1.0 if host=='elitecosmeticspk.com' else 0.25
        state_path=Path(g['__file__']).resolve().parent/'source_pacing'/(host+'.json')
        tls.fast_gate=RequestGate(g['_chotu_wait'],g['_chotu_debug'],floor,state_path,g['ChotuRateLimited']);tls.fast_products=[]
        return result
    def close_checkpoint(success=False):
        try:return old_close(success)
        finally:tls.fast_gate=None;tls.fast_products=[]
    def backoff(seconds,reason='Retry'):
        gate=getattr(tls,'fast_gate',None)
        if reason=='Rate limit' and gate is not None and gate.limited:
            raise gate.blocked_error()
        # The shared transport gate replaces independent worker pacing only.
        if getattr(tls,'fast_preloading',False) and reason=='Adaptive pacing':
            g['_chotu_wait']();return
        return old_backoff(seconds,reason)
    g['_chotu_open_checkpoint']=open_checkpoint;g['_chotu_close_checkpoint']=close_checkpoint;g['_chotu_backoff']=backoff

    def discover(base,log):
        gate=getattr(tls,'fast_gate',None)
        if gate is not None and gate.limited:raise gate.blocked_error()
        result=old_discover(base,log);tls.fast_products=result[0];return result

    def preload(tasks, operation, label,log):
        api_path=getattr(tls,'checkpoint_path',None);page_path=getattr(tls,'saved_api_path',None)
        # Saved Runs gives every fresh/resumed store its own two durable caches.
        if api_path is None or page_path is None or not tasks:return
        page_path=Path(page_path).with_name('pages.sqlite3')
        gate=tls.fast_gate;note=getattr(tls,'saved_run_note',None)
        totals=[0,0];iterator=iter(tasks);iterator_lock=threading.Lock()
        log(f'FAST FETCH: {label}; 2 workers, shared {gate.baseline:.2f}s request spacing; canonical checks preserved')
        g['_chotu_debug_stage']('Parallel '+label)
        def worker():
            db=None;cache=None;session=None
            try:
                tls.fast_gate=gate;tls.fast_preloading=True;tls.saved_run_note=note
                db=sqlite3.connect(api_path,timeout=30);db.execute('PRAGMA synchronous=FULL');tls.db=db
                cache=ResponseCache(page_path);tls.saved_response_cache=cache
                session=session_factory();session.headers.update(g['HEADERS']);tls.fast_session=session
                while not gate.limited:
                    with iterator_lock:
                        try:task=next(iterator)
                        except StopIteration:return
                    try:
                        operation(task)
                        with iterator_lock:totals[0]+=1
                    except Exception as exc:
                        with iterator_lock:totals[1]+=1
                        g['_chotu_debug']('FAST FETCH: preload deferred to canonical retry: '+str(exc)[:220])
            except Exception as exc:
                g['_chotu_debug']('FAST FETCH: worker deferred to canonical pass: '+str(exc)[:220])
            finally:
                if session:session.close()
                if cache:cache.close()
                if db:db.close()
                tls.fast_session=None;tls.saved_response_cache=None;tls.db=None;tls.fast_preloading=False;tls.fast_gate=None
        # Two long-lived sessions/connections avoid a fresh TLS handshake for every product.
        # Each worker takes just one task at a time, so a rate limit cannot leave a large queued burst.
        workers=[threading.Thread(target=worker,name='chotu-preload-'+str(i),daemon=True) for i in range(min(2,len(tasks)))]
        for thread in workers:thread.start()
        reported=0
        while any(thread.is_alive() for thread in workers):
            for thread in workers:thread.join(timeout=0.1)
            with iterator_lock:completed,failed=totals
            if completed+failed-reported>=50:
                reported=completed+failed
                log(f'FAST FETCH: {label} {reported}/{len(tasks)} tasks processed; deferred={failed}')
        log(f'FAST FETCH: {label} preload finished; successful tasks={totals[0]}, deferred={totals[1]}; canonical pass follows')

    def collections(base,log):
        products=getattr(tls,'fast_products',[])
        if getattr(tls,'saved_api_path',None) is None:
            log('FAST FETCH: serial fallback — no durable Saved Runs context; use FETCH SELECTED / New Fresh Run from the updated app')
            return old_collections(base,log)
        handles=[];seen=set()
        try:
            for page in range(1,30):
                batch=g['get_json'](f'{base}/collections.json?limit=250&page={page}').get('collections',[])
                for c in batch:
                    handle=c.get('handle')
                    if handle and g['txt'](c.get('title')) and handle not in seen and c.get('products_count')!=0:
                        handles.append(handle);seen.add(handle)
                if len(batch)<250:break
            def collection(handle):
                for page in range(1,30):
                    batch=g['get_json'](f'{base}/collections/{handle}/products.json?limit=250&page={page}').get('products',[])
                    if len(batch)<250:break
            preload(handles,collection,'category responses',log)
        except Exception as exc:log('FAST FETCH: category preload deferred; original mapping will retry: '+str(exc)[:180])
        if tls.fast_gate.limited:raise tls.fast_gate.blocked_error()
        mapping=old_collections(base,log)
        if tls.fast_gate.limited:raise tls.fast_gate.blocked_error()
        eligible=[]
        for product in products:
            if str(product.get('status') or '').strip().lower() not in ('','active'):continue
            if 'published_at' in product and not product.get('published_at'):continue
            if not product.get('handle') or g['is_free_gift'](product):continue
            if any(v.get('id') is not None and v.get('available') is True and (g['money'](v.get('price')) or 0)>0 for v in product.get('variants',[])):
                eligible.append(product['handle'])
        def detail(handle):
            g['get_json'](base.rstrip('/')+'/products/'+handle+'.js')
            # Store the original full page; hero/description/audits still parse it normally.
            response=g['S'].get(base.rstrip('/')+'/products/'+handle,timeout=25);response.raise_for_status()
        preload(eligible,detail,'product prices and pages',log)
        if tls.fast_gate.limited:raise tls.fast_gate.blocked_error()
        g['_chotu_debug_stage']('Building Excel rows')
        return mapping

    g['discover']=discover;g['collections']=collections;g['_chotu_fast_fetch_enabled']=True
