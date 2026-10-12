import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from types import SimpleNamespace
from unittest.mock import patch
import requests
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import resume_support as support
import install_resume_update

class DurableTests(unittest.TestCase):
    def test_selected_queue_survives_process_restart_and_fresh_starts_new(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);template=root/'template.xlsx';template.write_bytes(b'schema')
            store=support.RunStore(root/'runs')
            state=store.fresh([{'name':'A','url':'https://a.example'},{'name':'B','url':'https://b.example'}],template)
            output=root/'A.xlsx';output.write_bytes(b'completed');stat=output.stat()
            def advance(s):
                s['sites'][0].update(status='done',progress=100,output={'path':str(output),'size':stat.st_size,'mtime_ns':stat.st_mtime_ns})
                s['sites'][1].update(status='running',progress=42,detail='Variants')
            store.update(advance)
            code="import resume_support as s,json,sys; r=s.RunStore(sys.argv[1]); d=r.load(); print(json.dumps({'pending':r.pending(d),'progress':d['sites'][1]['progress']}))"
            result=subprocess.check_output([sys.executable,'-c',code,str(root/'runs')],cwd=ROOT,text=True)
            self.assertEqual(json.loads(result),{'pending':[1],'progress':42})
            old=store.load()['id'];new=store.fresh([{'name':'C','url':'https://c.example'}],template)
            self.assertNotEqual(old,new['id']);self.assertEqual(store.pending(new),[0])
            self.assertTrue((root/'runs'/old/'template.xlsx').exists())

    def test_successful_page_survives_process_restart_failed_response_not_saved(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'pages.sqlite3';cache=support.ResponseCache(path)
            response=requests.Response();response.status_code=200;response._content=b'{"price":499}';response.url='https://store.example/product.js';response.encoding='utf-8'
            cache.put(response.url,response)
            response.status_code=429;cache.put('https://store.example/failure',response)
            response.status_code=200;response._content=b'incomplete JSON';cache.put('https://store.example/bad.json',response)
            self.assertIsNone(cache.get('https://store.example/bad.json'));cache.close()
            code="import resume_support as s,sys; c=s.ResponseCache(sys.argv[1]); print(c.get('https://store.example/product.js').json()['price']); print(c.get('https://store.example/failure')); c.close()"
            output=subprocess.check_output([sys.executable,'-c',code,str(path)],cwd=ROOT,text=True)
            self.assertEqual(output.strip(),'499\nNone')

    def test_committed_queue_and_response_survive_abrupt_process_exit(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);template=root/'template.xlsx';template.write_bytes(b'schema')
            code="""import resume_support as s,requests,sys,os
from pathlib import Path
p=Path(sys.argv[1]);r=s.RunStore(p/'runs');r.fresh([{'name':'A','url':'https://a.example'}],p/'template.xlsx')
c=s.ResponseCache(p/'response.sqlite3');x=requests.Response();x.status_code=200;x.url='https://a.example/products.json';x._content=b'{"products":[{"id":1}]}';c.put(x.url,x)
os._exit(17)
"""
            result=subprocess.run([sys.executable,'-c',code,str(root)],cwd=ROOT)
            self.assertEqual(result.returncode,17)
            store=support.RunStore(root/'runs');self.assertEqual(store.load()['sites'][0]['name'],'A')
            cache=support.ResponseCache(root/'response.sqlite3')
            self.assertEqual(cache.get('https://a.example/products.json').json()['products'][0]['id'],1);cache.close()

    def test_lease_blocks_simultaneous_writer(self):
        with tempfile.TemporaryDirectory() as tmp:
            first=support.RunLease(tmp);second=support.RunLease(tmp)
            first.acquire()
            with self.assertRaises(RuntimeError):second.acquire()
            first.release();second.acquire();second.release()

class ResumeGuiTests(unittest.TestCase):
    def test_restart_continues_original_selected_queue_skips_done_and_reads_cache(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);target=root/'app';target.mkdir()
            original=subprocess.check_output(['git','-C',str(ROOT),'show','28f80c2:main.py'])
            (target/'main.py').write_bytes(original)
            # Installer obtains helper from repository without changing engine functions.
            install_resume_update.install(target)
            text=(target/'main.py').read_text()
            self.assertEqual(text.replace(install_resume_update.HOOK,''),original.decode())
            spec=importlib.util.spec_from_file_location('resume_gui_fixture',target/'main.py')
            module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
            module.CONFIG=root/'sites.json';module.HOME=root;module.OUT=root/'exports';module.OUT.mkdir()
            template=root/'template.xlsx';template.write_bytes(b'fixture schema')
            store=support.RunStore(target/'saved_runs')
            state=store.fresh([{'name':'Finished','url':'https://finished.example'},{'name':'Remaining','url':'https://remaining.example'},{'name':'Last','url':'https://last.example'}],template)
            output=module.OUT/'Finished.xlsx';output.write_bytes(b'previous good output');stat=output.stat()
            def advance(s):
                s['sites'][0].update(status='done',output={'path':str(output),'size':stat.st_size,'mtime_ns':stat.st_mtime_ns},progress=100)
                s['sites'][1].update(status='running',progress=43,detail='Saved progress')
            store.update(advance)
            folder=store.root/state['id']/'1';folder.mkdir()
            cache=support.ResponseCache(folder/'pages.sqlite3')
            response=requests.Response();response.status_code=200;response._content=b'{"price":499}';response.url='https://remaining.example/product.js';response.encoding='utf-8'
            cache.put(response.url,response)
            html=requests.Response();html.status_code=200;html.url='https://remaining.example/products/p1';html._content=b'<media-gallery><div class="product__media"><img src="https://images.example/hero.jpg"></div></media-gallery>';html.encoding='utf-8'
            cache.put(html.url,html);cache.close()
            rootwin=module.tk.Tk();errors=[];rootwin.report_callback_exception=lambda *args:errors.append(args)
            app=module.App(rootwin);rootwin.update()
            self.assertEqual(app.continue_run_button.cget('state'),'normal')
            rootwin.geometry('900x640');rootwin.update()
            for button in (app.fresh_run_button,app.continue_run_button):
                self.assertTrue(button.winfo_ismapped())
                self.assertLess(button.winfo_rooty()+button.winfo_height(),rootwin.winfo_rooty()+rootwin.winfo_height())
            calls=[];last_started=threading.Event();release_last=threading.Event()
            def job(site,template):
                calls.append(site['name'])
                if site['name']=='Last':
                    last_started.set();release_last.wait(3)
                # Newly constructed app and worker can replay response persisted before restart.
                if site['name']=='Remaining':
                    self.assertEqual(module.S.get('https://remaining.example/product.js').json()['price'],499)
                    module._chotu_tls.image_audit=[];module._chotu_tls.image_throttled=False
                    module._chotu_tls.adaptive_last_request=time.monotonic();module._chotu_tls.adaptive_pace=2.7
                    started=time.monotonic()
                    hero=module.storefront_cover('https://remaining.example',{'handle':'p1'},[{'src':'https://images.example/hero.jpg'}],lambda x:None)
                    self.assertEqual(hero,'https://images.example/hero.jpg')
                    self.assertLess(time.monotonic()-started,1.0)
                new=module.OUT/(site['name']+'.xlsx');new.write_bytes(b'new output')
                app.events.put(('__JOB_RESULT__',True,site['name']))
            try:
                with patch.object(app,'_run_checked',side_effect=job):
                    app.continue_saved_run()
                    self.assertTrue(last_started.wait(2))
                    self.assertTrue(app.running)
                    self.assertTrue((module.OUT/'Remaining.xlsx').is_file())
                    self.assertEqual(store.load()['sites'][1]['status'],'done')
                    app.refresh_saved_controls()
                    self.assertIn('Files saved: 2/3',app.saved_run_label.cget('text'))
                    release_last.set()
                    deadline=time.monotonic()+4
                    while app.running and time.monotonic()<deadline:rootwin.update();time.sleep(.01)
                self.assertFalse(app.running);self.assertEqual(calls,['Remaining','Last'])
                self.assertEqual(store.load()['status'],'complete')
                self.assertEqual(output.read_bytes(),b'previous good output')
                self.assertFalse(errors)
            finally:
                for callback in rootwin.tk.splitlist(rootwin.tk.call('after','info')):rootwin.tk.call('after','cancel',callback)
                rootwin.destroy()
                module.requests.Session=support.original_requests_session if hasattr(support,'original_requests_session') else requests.sessions.Session

if __name__=='__main__':unittest.main()
