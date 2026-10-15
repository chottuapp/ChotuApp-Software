"""Keep window management responsive without changing extraction or requests."""
import atexit
from collections import deque
import queue
import threading
import time


class AsyncLog:
    def __init__(self,path):
        self.path=path;self.items=queue.Queue();self.error=None
        self.thread=threading.Thread(target=self.run,name='chotu-debug-writer',daemon=True)
        self.thread.start();atexit.register(self.shutdown)
    def run(self):
        while True:
            text=self.items.get()
            try:
                if text is None:return
                with self.path.open('a',encoding='utf-8') as stream:stream.write(text)
            except OSError as exc:self.error=str(exc)
            finally:self.items.task_done()
    def shutdown(self):
        if self.thread.is_alive():self.items.put(None);self.thread.join(timeout=1)
    def open(self,mode='r',**kwargs):
        if mode=='a':return _LogChunk(self)
        return self.path.open(mode,**kwargs)
    def __getattr__(self,name):return getattr(self.path,name)


class _LogChunk:
    def __init__(self,writer):self.writer=writer;self.parts=[]
    def __enter__(self):return self
    def write(self,text):self.parts.append(text);return len(text)
    def __exit__(self,*args):
        if self.parts:self.writer.items.put(''.join(self.parts))


class QuietLabel:
    def __init__(self,widget,app):self.widget=widget;self.app=app;self.pending={};self.applied={}
    def configure(self,**kwargs):
        self.pending.update(kwargs)
        if not self.app._quiet_ui:self.flush()
    config=configure
    def flush(self):
        changed={k:v for k,v in self.pending.items() if k not in self.applied or self.applied[k]!=v}
        if changed:self.widget.configure(**changed);self.applied.update(changed)
        self.pending.clear()
    def __getattr__(self,name):return getattr(self.widget,name)


class QuietConsole:
    def __init__(self,widget,app):self.widget=widget;self.app=app;self.pending=deque(maxlen=350)
    def insert(self,index,text,*args):
        if self.app._quiet_ui and index=='end':self.pending.extend(text.splitlines(True));return
        self.flush();return self.widget.insert(index,text,*args)
    def see(self,index):
        if not self.app._quiet_ui:return self.widget.see(index)
    def flush(self):
        if self.pending:
            self.widget.insert('end',''.join(self.pending));self.pending.clear()
            self.app._trim_console(self.widget,350);self.widget.see('end')
    def __getattr__(self,name):return getattr(self.widget,name)


def enable_responsive_ui(g):
    if g.get('_chotu_responsive_ui'):return
    App=g['App'];original_init=App.__init__;old_watchdog=App.debug_watchdog;old_status=App.set_live_status
    def init(self,root):
        self._quiet_ui=False;self._ui_minimized=False;self._ui_resize_until=0
        original_init(self,root)
        self.debug_file=AsyncLog(self.debug_file)
        self._quiet_labels=[]
        for name in ('header_clock','runtime_label','debug_status','progress_label','saved_run_label'):
            if hasattr(self,name):
                proxy=QuietLabel(getattr(self,name),self);setattr(self,name,proxy);self._quiet_labels.append(proxy)
        for key,widget in self.metric_values.items():
            proxy=QuietLabel(widget,self);self.metric_values[key]=proxy;self._quiet_labels.append(proxy)
        self.logbox=QuietConsole(self.logbox,self);self.debug_box=QuietConsole(self.debug_box,self)
        def event(e):
            if e.widget is not root:return
            if e.type.name=='Unmap':self._ui_minimized=True
            elif e.type.name=='Map':self._ui_minimized=False
            else:self._ui_resize_until=time.monotonic()+.15
            self._quiet_ui=self._ui_minimized or time.monotonic()<self._ui_resize_until
            if self._quiet_ui:self.live_spinner.stop()
        for sequence in ('<Unmap>','<Map>','<Configure>'):root.bind(sequence,event,add='+')
        root.title(root.title()+' | Smooth UI')
        root.after(200,self._quiet_flush)
    def flush(self):
        if not self.root.winfo_exists():return
        was_quiet=self._quiet_ui
        self._quiet_ui=self._ui_minimized or time.monotonic()<self._ui_resize_until
        if not self._quiet_ui:
            for label in self._quiet_labels:label.flush()
            self.logbox.flush();self.debug_box.flush()
            if was_quiet and self.running:self.live_spinner.start(80)
        self.root.after(200,self._quiet_flush)
    def animate(self):
        # Static status + one-second clock avoid 4fps redraw of the same text.
        try:
            if not self._quiet_ui:
                active=self.running
                self.header_clock.configure(text='● EXTRACTION ACTIVE' if active else '● SYSTEM READY',text_color='#55e69a' if active else '#a2c5ad')
                if active and self._ui_started is not None:
                    elapsed=max(0,int(time.monotonic()-self._ui_started))
                    self.runtime_label.configure(text='SESSION  {:02d}:{:02d}:{:02d}'.format(elapsed//3600,elapsed//60%60,elapsed%60))
        finally:self.root.after(1000,self._animate_dashboard)
    def watchdog(self):
        if self._quiet_ui:self.root.after(2000,self.debug_watchdog)
        else:old_watchdog(self)
    def status(self,*args,**kwargs):
        result=old_status(self,*args,**kwargs)
        self.live_spinner.stop()
        if (args[0] if args else kwargs.get('state'))=='working' and not self._quiet_ui:self.live_spinner.start(80)
        return result
    App.__init__=init;App._quiet_flush=flush;App._animate_dashboard=animate
    App.debug_watchdog=watchdog;App.set_live_status=status;g['_chotu_responsive_ui']=True
