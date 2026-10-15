from pathlib import Path
import importlib.util
import json
import sys
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import requests
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import resume_support

class SourceRetryTests(unittest.TestCase):
    def exercise(self,mode):
        original_factory=requests.Session
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);file=root/'main.py';file.write_bytes((ROOT/'main.py').read_bytes())
            spec=importlib.util.spec_from_file_location('source_retry_'+mode,file);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
            module.CONFIG=root/'sites.json';module.HOME=root;module.OUT=root/'exports';module.OUT.mkdir()
            sites=[{'name':'Limited','url':'https://limited.example'},{'name':'Other','url':'https://other.example'}]
            if mode=='mixed':sites.append({'name':'Missing','url':'https://missing.example'})
            module.CONFIG.write_text(json.dumps(sites));template=root/'template.xlsx';template.write_bytes(b'fixture template')
            resume_support.enable_resume(module.__dict__)
            window=module.tk.Tk();errors=[];window.report_callback_exception=lambda *args:errors.append(args)
            app=module.App(window);calls=[];old=module.OUT/'Limited.xlsx';old.write_bytes(b'prior valid file');attempts=0
            def run(site,template):
                nonlocal attempts
                calls.append(site['name'])
                if site['name']=='Missing':
                    app.events.put('FAILED: Missing: Website endpoint unavailable (404)')
                    app.events.put(('__JOB_RESULT__',False,'Missing'));return
                if site['name']=='Limited':
                    attempts+=1
                    if mode!='recover' or attempts==1:
                        cooldown=time.monotonic()+(300 if mode=='long-delay' else .12)
                        app._source_gate=lambda:SimpleNamespace(cooldown=cooldown)
                        app.events.put('FAILED: Limited: SOURCE PAUSED: website rate limit; retry this saved store after at least 60s.')
                        app.events.put(('__JOB_RESULT__',False,'Limited'));return
                app._source_gate=lambda:None
                (module.OUT/(site['name']+'.xlsx')).write_bytes(b'new verified result')
                app.events.put(('__JOB_RESULT__',True,site['name']))
            try:
                with patch.object(app,'_run_checked',side_effect=run):
                    app._launch_jobs(sites,str(template));deadline=time.monotonic()+4
                    while app.running and time.monotonic()<deadline:window.update();time.sleep(.01)
                window.update();self.assertFalse(app.running);self.assertFalse(errors)
                state=app.saved_runs.load()
                self.assertEqual(calls[:2],['Limited','Other'])
                self.assertEqual(app.job_completed,len(sites))
                self.assertEqual(state['sites'][1]['status'],'done')
                self.assertTrue((module.OUT/'Other.xlsx').is_file())
                if mode=='recover':
                    self.assertEqual(calls,['Limited','Other','Limited']);self.assertEqual(state['status'],'complete')
                    self.assertFalse(app.job_failed);self.assertEqual(old.read_bytes(),b'new verified result')
                else:
                    self.assertEqual(attempts,1 if mode=='long-delay' else 3)
                    self.assertEqual(state['sites'][0]['status'],'source_paused');self.assertEqual(state['status'],'incomplete')
                    self.assertEqual(old.read_bytes(),b'prior valid file')
                    self.assertIn('Website cooldown',app.live_status.cget('text'))
                    self.assertNotIn('Excel missing',app.live_status.cget('text'))
                    self.assertEqual(app.progress_value.get(),int(100/len(sites)))
                    self.assertEqual(app.saved_runs.pending(state),[0,2] if mode=='mixed' else [0])
                    if mode=='mixed':
                        self.assertIn('Failed: Missing',app.live_status.cget('text'))
                        self.assertEqual(state['sites'][2]['status'],'failed')
            finally:
                for cb in window.tk.splitlist(window.tk.call('after','info')):window.tk.call('after','cancel',cb)
                window.destroy();requests.Session=original_factory
    def test_other_stores_first_then_saved_retry_recovers_without_false_failure(self):self.exercise('recover')
    def test_repeated_rate_limit_bounded_and_clear_cooldown_status(self):self.exercise('exhaust')
    def test_long_retry_after_is_not_waited_or_bypassed(self):self.exercise('long-delay')

    def test_mixed_endpoint_failure_and_cooldown_keep_true_completion_progress(self):self.exercise('mixed')
