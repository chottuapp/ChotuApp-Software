from pathlib import Path
import datetime as dt
import importlib.util
import sys
import tempfile
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import automation_support as support
import install_daily_auto as installer

class ScheduleTests(unittest.TestCase):
    def test_daily_fresh_once_and_resume_only_own_same_day(self):
        now=dt.datetime(2026,10,13,10,0)
        s={'enabled':True,'time':'09:00','run_on_open':True}
        self.assertEqual(support.choose_action(s,now,True,None),'fresh')
        s['last_attempt_date']='2026-10-13'
        self.assertIsNone(support.choose_action(s,now,True,None))
        s['inflight']={'date':'2026-10-13','run_id':'own'}
        self.assertEqual(support.choose_action(s,now,True,{'id':'own','status':'incomplete'}),'resume')
        self.assertIsNone(support.choose_action(s,now,True,{'id':'manual','status':'incomplete'}))
        tomorrow=now+dt.timedelta(days=1)
        self.assertEqual(support.choose_action(s,tomorrow,True,{'id':'own','status':'incomplete'}),'fresh')
        s['enabled']=False;self.assertIsNone(support.choose_action(s,tomorrow,True,None))

    def test_wait_for_time_and_midnight_and_restart(self):
        s={'enabled':True,'time':'09:30','run_on_open':False}
        self.assertIsNone(support.choose_action(s,dt.datetime(2026,10,13,9,29),True,None))
        self.assertEqual(support.choose_action(s,dt.datetime(2026,10,13,9,30),False,None),'fresh')
        s['run_on_open']=True
        self.assertEqual(support.choose_action(s,dt.datetime(2026,10,13,1,0),True,None),'fresh')
        for value in ('24:00','09:60','x','09:00:01'):
            with self.assertRaises(ValueError):support.parse_time(value)
        self.assertEqual(support.parse_time('9:5'),'09:05')

    def test_startup_launcher_quoting_and_remove_owned_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);file=root/'startup.cmd';app=root/'Anas Khan'/'main.py'
            support.configure_startup(True,app,file,root/'Python 3'/'python.exe')
            text=file.read_text();self.assertIn('"'+str(app)+'"',text);self.assertIn('--chotu-auto',text)
            support.configure_startup(False,app,file);self.assertFalse(file.exists())
            file.write_text('user startup script')
            with self.assertRaises(RuntimeError):support.configure_startup(False,app,file)
            self.assertEqual(file.read_text(),'user startup script')

    def test_installer_preserves_engine_and_existing_hooks(self):
        source=(ROOT/'main.py').read_text()
        changed=installer.transform(source)
        self.assertIn(installer.RESUME_HOOK,changed);self.assertIn(installer.AUTO_HOOK,changed)
        self.assertEqual(changed.replace(installer.RESUME_HOOK,'').replace(installer.AUTO_HOOK,''),source)
        self.assertEqual(installer.transform(changed),changed)

class AutomationGuiTests(unittest.TestCase):
    def test_saved_selection_daily_fresh_output_once_and_existing_buttons_visible(self):
        import json
        import time
        import requests
        import threading
        original_session=requests.Session
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);target=root/'app';target.mkdir()
            (target/'main.py').write_bytes((ROOT/'main.py').read_bytes())
            installer.install(target)
            sys.path.insert(0,str(target))
            spec=importlib.util.spec_from_file_location('auto_gui',target/'main.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
            module.CONFIG=root/'sites.json';module.HOME=root;module.OUT=root/'exports';module.OUT.mkdir()
            module.CONFIG.write_text(json.dumps([{'name':'Daily A','url':'https://a.example'},{'name':'Daily B','url':'https://b.example'}]))
            template=ROOT/'importer-files/Chotu_Products_Import_Template_Discount_Tags.xlsx'
            window=module.tk.Tk();errors=[];window.report_callback_exception=lambda *args:errors.append(args)
            app=module.App(window)
            try:
                window.geometry('900x800');window.update()
                for widget in (app.refresh,app.refresh_selected,app.pause_button,app.fresh_run_button,app.continue_run_button,app.auto_save_button):
                    self.assertTrue(widget.winfo_ismapped())
                    self.assertLess(widget.winfo_rooty()+widget.winfo_height(),window.winfo_rooty()+window.winfo_height())
                window.geometry('900x640');window.update()
                for widget in (app.auto_save_button,app.auto_panel,app.fresh_run_button,app.continue_run_button):
                    self.assertTrue(widget.winfo_ismapped())
                    self.assertLessEqual(widget.winfo_rootx()+widget.winfo_width(),window.winfo_rootx()+window.winfo_width())
                    self.assertLess(widget.winfo_rooty()+widget.winfo_height(),window.winfo_rooty()+window.winfo_height())
                app.template.set(str(template))
                for v in app.store_checks.values():v.set(True)
                app.auto_enabled.set(True);app.auto_login.set(False)
                app.save_daily_automation()
                self.assertEqual(len(app._auto_settings['sites']),2)
                # Later checkbox changes do not change the saved daily selection.
                for v in app.store_checks.values():v.set(False)
                calls=[];started=threading.Event();release=threading.Event()
                def job(site,template):
                    calls.append(site['name']);started.set();release.wait(2)
                    (module.OUT/(site['name']+'.xlsx')).write_bytes(b'daily result')
                    app.events.put(('__JOB_RESULT__',True,site['name']))
                with patch.object(app,'_run_checked',side_effect=job):
                    app._daily_auto_tick();self.assertTrue(started.wait(1))
                    self.assertTrue(app.running);self.assertTrue(app._auto_active)
                    # GUI event loop remains responsive while extraction waits.
                    beat=[];window.after(1,lambda:beat.append(True));window.update();time.sleep(.01);window.update();self.assertTrue(beat)
                    release.set();deadline=time.monotonic()+3
                    while app.running and time.monotonic()<deadline:window.update();time.sleep(.01)
                    window.update();self.assertFalse(app.running)
                    app._daily_auto_tick()
                self.assertEqual(calls,['Daily A','Daily B'])
                self.assertEqual(app._auto_settings['last_result'],'Saved successfully')
                self.assertTrue((module.OUT/'Daily A.xlsx').is_file());self.assertTrue((module.OUT/'Daily B.xlsx').is_file())
                self.assertNotIn('inflight',app._auto_settings)
                self.assertFalse(errors)
            finally:
                if app._auto_lease:app._auto_lease.release()
                for callback in window.tk.splitlist(window.tk.call('after','info')):window.tk.call('after','cancel',callback)
                window.destroy();requests.Session=original_session;sys.path.remove(str(target))
