"""Bounded per-store preloading; preserve canonical extraction and durable caches."""
import email.utils
import json
import math
import os
import tempfile
from urllib.parse import urlparse
import datetime
from pathlib import Path
import sqlite3
import threading
import time


# These hosts returned HTTP 429 during category preloading at 0.25s spacing.
RECENTLY_LIMITED_SOURCES={'vincecare.com','saeedghani.pk','pk.hemaniherbals.com','bonanzasatrangi.com','gulahmedshop.com','stylo.pk'}
CAUTIOUS_SOURCES={'rawayat.com.pk','rivaj-uk.com','junaidjamshed.com','tawakkalfabrics.co'}


def source_policy(host):
    host=host.lower().removeprefix('www.')
    if host in RECENTLY_LIMITED_SOURCES:return (2.5,1)
    if host in ('outfitters.com.pk','zellbury.com','laam.com','pk.khaadi.com','khaadi.com','sapphireonline.pk','pk.sapphireonline.pk'):return (1.5,1)
    return (1.0,1) if host in CAUTIOUS_SOURCES or host=='shopmodest.pk' else (1.0,5) if host=='elitecosmeticspk.com' else (0.25,5)


class RequestGate:
    def __init__(self, pause, log, baseline=0.25, state_path=None, error_factory=RuntimeError):
        self.pause=pause;self.log=log;self.baseline=baseline;self.interval=baseline
        self.lock=threading.RLock();self.next_start=0.0;self.cooldown=0.0;self.limited=False
        self.success_streak=0;self.recovery_window=20;self.recovery_not_before=0.0
        self.state_path=Path(state_path) if state_path else None;self.error_factory=error_factory
        if self.state_path:
            try:
                state=json.loads(self.state_path.read_text())
                learned=float(state.get('min_spacing',baseline))
                if math.isfinite(learned):self.interval=max(self.baseline,min(12.0,learned))
                self.recovery_not_before=float(state.get('recovery_not_before_epoch',0))
                if 'recovery_not_before_epoch' not in state and self.interval>self.baseline:
                    # Older profiles recorded slowdown but not when it happened.
                    # Do not immediately accelerate a previously throttled source.
                    self.recovery_not_before=time.time()+1800
                remaining=float(state.get('retry_after_epoch',0))-time.time()
                if remaining>0:self.cooldown=time.monotonic()+remaining;self.limited=True
                if 'recovery_not_before_epoch' not in state:self.persist_state()
            except (OSError,ValueError,TypeError):pass
    def blocked_error(self):
        remaining=max(1,int(self.cooldown-time.monotonic()+0.99))
        return self.error_factory(f'SOURCE PAUSED: website rate limit; retry this saved store after at least {remaining}s. Checkpoint retained; other stores can proceed.')
    def persist_state(self):
        if not self.state_path:return
        # Serialize successful recovery with a simultaneous 429, so a healthy
        # response cannot erase a newer cooldown written by another worker.
        with self.lock:
            temporary=None
            try:
                self.state_path.parent.mkdir(parents=True,exist_ok=True)
                state={'retry_after_epoch':time.time()+max(0,self.cooldown-time.monotonic()) if self.limited else 0,
                       'min_spacing':self.interval,'profile_version':3,'recovery_not_before_epoch':self.recovery_not_before}
                with tempfile.NamedTemporaryFile(dir=self.state_path.parent,mode='w',delete=False) as stream:
                    temporary=Path(stream.name);json.dump(state,stream);stream.flush();os.fsync(stream.fileno())
                os.replace(temporary,self.state_path)
            except OSError as exc:self.log('FAST FETCH: could not persist adaptive source profile: '+str(exc))
            finally:
                if temporary:temporary.unlink(missing_ok=True)
    def persist_block(self,delay):
        self.persist_state()
    def network_failure(self):
        with self.lock:self.success_streak=0
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
                self.success_streak=0
                if not self.limited:self.interval=min(12.0,max(2.5,self.interval*1.8))
                self.cooldown=max(self.cooldown,time.monotonic()+delay);self.limited=True
                self.recovery_not_before=max(self.recovery_not_before,time.time()+1800)
                self.persist_block(delay)
            self.log(f'FAST FETCH: HTTP {response.status_code}; store paused, checkpoint retained, cooldown {delay:.0f}s; no repeated blocked requests')
        elif response.status_code==200:
            previous=None;recovered_value=None
            with self.lock:
                if self.limited or time.time()<self.recovery_not_before:return
                self.success_streak+=1
                if self.success_streak>=self.recovery_window:
                    self.success_streak=0
                    recovered=max(self.baseline,round(self.interval*0.75,4))
                    if recovered<self.interval:
                        previous=self.interval;self.interval=recovered;recovered_value=recovered
                        self.persist_state()
            if previous is not None:
                self.log(f'ADAPTIVE RECOVERY: {self.recovery_window} consecutive HTTP 200 responses; spacing {previous:.2f}s -> {recovered_value:.2f}s; configured floor {self.baseline:.2f}s')
        else:
            self.network_failure()


class GatedSession:
    def __init__(self,session,tls,pause):self.session=session;self.tls=tls;self.pause=pause
    def __getattr__(self,name):return getattr(self.session,name)
    def get(self,url,**kwargs):
        gate=getattr(self.tls,'fast_gate',None)
        if not gate:return self.session.get(url,**kwargs)
        cache=getattr(self.tls,'saved_response_cache',None)
        parsed=urlparse(url)
        if cache is not None and not parsed.username and not parsed.password and not any(kwargs.get(k) for k in ('params','stream','auth')):
            cached=cache.get(url)
            if cached is not None:
                # get() already verified the checksum. Avoid reading/hashing the
                # same large HTML body again through the underlying SessionProxy.
                self.pause()
                note=getattr(self.tls,'saved_run_note',None)
                if note:note('SAVED RESPONSE: '+url)
                return cached
        gate.wait(getattr(self.tls,'fast_preloading',False))
        try:response=self.session.get(url,**kwargs)
        except Exception:
            gate.network_failure();raise
        gate.response(response);return response


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
        root.title(root.title()+' | Fast Fetch | Stable Source Pacing')
    g['App'].__init__=init
    def session_factory(*args,**kwargs):return GatedSession(factory(*args,**kwargs),tls,g['_chotu_wait'])
    g['requests'].Session=session_factory
    g['S']=ThreadSession(GatedSession(g['S'],tls,g['_chotu_wait']),tls)
    old_open=g['_chotu_open_checkpoint'];old_close=g['_chotu_close_checkpoint']
    old_discover=g['discover'];old_collections=g['collections'];old_backoff=g['_chotu_backoff']
    old_get_json=g['get_json']
    def get_json(*args,**kwargs):
        previous=getattr(tls,'fast_json_request',False)
        tls.fast_json_request=True
        try:return old_get_json(*args,**kwargs)
        finally:tls.fast_json_request=previous
    g['get_json']=get_json
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
        floor,configured_workers=source_policy(host)
        state_path=Path(g['__file__']).resolve().parent/'source_pacing'/(host+'.json')
        tls.fast_gate=RequestGate(g['_chotu_wait'],g['_chotu_debug'],floor,state_path,g['ChotuRateLimited']);tls.fast_products=[]
        tls.fast_worker_count=1 if time.time()<tls.fast_gate.recovery_not_before else configured_workers
        if tls.fast_worker_count==1:g['_chotu_debug']('STABLE PACING: single worker; learned spacing retained; no acceleration during recent-throttle recovery hold.')
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
        worker_count=getattr(tls,'fast_worker_count',5)
        log(f'FAST FETCH: {label}; {worker_count} workers, shared {gate.interval:.2f}s starting request spacing; canonical checks preserved')
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
        # Bounded persistent sessions overlap slow responses under one shared start budget.
        # Each worker takes just one task at a time, so a rate limit cannot leave a large queued burst.
        workers=[threading.Thread(target=worker,name='chotu-preload-'+str(i),daemon=True) for i in range(min(worker_count,len(tasks)))]
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
        if hasattr(tls,'website_category_navigation'):
            log('FAST FETCH: strict website category mapping; skip legacy all-collection preload')
        else:
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
