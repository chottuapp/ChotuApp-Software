import contextlib,io,json,os,subprocess,sys,tempfile,threading,time,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'cloud'));sys.path.insert(0,str(ROOT))
from live_snapshot import snapshot,wait_and_snapshot
from background_run import supervise
from cloud_sync_windows import Sync,atomic_copy
from runtime import CloudService
from test_parallel_stores import ENGINE
from openpyxl import Workbook


class LiveTests(unittest.TestCase):
    def setUp(self):self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
    def tearDown(self):self.temp.cleanup()
    def test_snapshot_only_publishes_done_valid_workbooks(self):
        engine=self.root/'main.py';engine.write_text(ENGINE);service=CloudService(self.root/'data',engine=engine,resolve_sites=False)
        try:
            service.start([{'name':'Ready','url':'https://ready.example'}]);deadline=time.monotonic()+8
            while service.running and time.monotonic()<deadline:time.sleep(.02)
            pending=service.output/'Incomplete.xlsx';pending.write_bytes(b'incomplete')
            result=snapshot(service.data);self.assertEqual(result['completed_files'],1);self.assertTrue(result['files_changed'])
            self.assertEqual([p.name for p in (service.data/'live-excel').glob('*.xlsx')],['Ready.xlsx'])
            self.assertFalse(snapshot(service.data)['files_changed'])
            self.assertTrue((service.data/'live-diagnostics'/'fetch-log.txt').exists())
        finally:service.close()
    def test_snapshot_requires_recorded_size_and_mtime(self):
        engine=self.root/'main.py';engine.write_text(ENGINE);service=CloudService(self.root/'data',engine=engine,resolve_sites=False)
        try:
            service.start([{'name':'Ready','url':'https://ready.example'}]);deadline=time.monotonic()+8
            while service.running and time.monotonic()<deadline:time.sleep(.02)
            path=service.output/'Ready.xlsx';path.write_bytes(b'broken')
            self.assertEqual(snapshot(service.data)['completed_files'],0)
        finally:service.close()
    def test_snapshot_empty_startup_and_finished_marker(self):
        data=self.root/'data';data.mkdir();(data/'background-result.json').write_text('{"exit_code":0}')
        with contextlib.redirect_stdout(io.StringIO()):result=wait_and_snapshot(data,seconds=0)
        self.assertTrue(result['finished']);self.assertEqual(result['completed_files'],0)
    def test_dead_supervisor_is_reported_instead_of_waiting_all_day(self):
        data=self.root/'data';data.mkdir();(data/'background-process.json').write_text('{"pid":99999999}')
        with contextlib.redirect_stdout(io.StringIO()):result=wait_and_snapshot(data,seconds=5)
        self.assertTrue(result['finished']);self.assertEqual(json.loads((data/'background-result.json').read_text())['exit_code'],1)
    def test_supervisor_keeps_one_child_and_saves_exit_code(self):
        data=self.root/'data';data.mkdir();calls=[]
        class Child:
            returncode=0
            def __init__(self,args,**kw):calls.append(args)
            def poll(self):return 0
        with patch('background_run.signal.signal'),patch.dict(os.environ,{'CLOUD_MINUTES':'300','CLOUD_STORES':'Store | https://store.example','SAVE_CHECKPOINT':'false','RESUME_RUN_ID':''}),patch('background_run.subprocess.Popen',Child):
            self.assertEqual(supervise(data),0)
        self.assertEqual(len(calls),1);self.assertIn('--minutes',calls[0]);self.assertIn('300',calls[0]);self.assertEqual(json.loads((data/'background-result.json').read_text()),{'exit_code':0})
    def test_background_process_survives_launcher_exit_and_snapshot_checks(self):
        import shutil
        app=self.root/'background-app';app.mkdir();data=self.root/'data';data.mkdir()
        for name in ('background_run.py','diagnostics.py'):shutil.copyfile(ROOT/'cloud'/name,app/name)
        (app/'cli.py').write_text("import sys,time\nfrom pathlib import Path\np=Path(sys.argv[sys.argv.index('--data')+1])\nfor i in range(20):\n (p/'counter.txt').write_text(str(i))\n time.sleep(.05)\nraise SystemExit(2)\n")
        env=dict(os.environ,CLOUD_MINUTES='1',CLOUD_STORES='Test | https://test.example',SAVE_CHECKPOINT='false',RESUME_RUN_ID='')
        start=subprocess.run([sys.executable,str(app/'background_run.py'),'start',str(data)],env=env,capture_output=True,text=True,timeout=5)
        self.assertEqual(start.returncode,0,start.stderr)
        with contextlib.redirect_stdout(io.StringIO()):first=wait_and_snapshot(data,seconds=0)
        self.assertFalse(first['finished'])
        deadline=time.monotonic()+8
        while not (data/'background-result.json').exists() and time.monotonic()<deadline:time.sleep(.05)
        self.assertEqual(json.loads((data/'background-result.json').read_text())['exit_code'],2)
        self.assertEqual((data/'counter.txt').read_text(),'19')
    def test_full_log_retains_early_lines_beyond_rotating_tail(self):
        from diagnostics import build_report
        (self.root/'fetch-full.log').write_text('First request\n'+''.join('line '+str(i)+'\n' for i in range(2100)))
        build_report(self.root,self.root/'diagnostics');log=(self.root/'diagnostics'/'fetch-log.txt').read_text();self.assertTrue(log.startswith('First request'));self.assertIn('line 2099',log)
    def test_windows_sync_downloads_snapshots_and_skips_same_artifact(self):
        downloads=[];status={'status':'in_progress','conclusion':''}
        def call(args):
            if args[:2]==['run','view']:
                if '--log' in args:return 'All GitHub log messages'
                return json.dumps(status)
            if args[0]=='api':return json.dumps({'artifacts':[{'id':2,'name':'chotuapp-excel-files'},{'id':1,'name':'chotuapp-live-logs'},{'id':3,'name':'chotuapp-checkpoint'}]})
            downloads.append(args);folder=Path(args[-1])
            if 'chotuapp-excel-files' in args:(folder/'Store.xlsx').write_bytes(b'workbook')
            else:(folder/'fetch-log.txt').write_text('live fetching log')
            return ''
        target=self.root/'PC';sync=Sync('gh','owner/repo','123',target,call)
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertFalse(sync.tick());self.assertFalse(sync.tick());status['status']='completed';status['conclusion']='success';self.assertTrue(sync.tick())
        self.assertEqual(len(downloads),2);self.assertEqual((target/'Store.xlsx').read_bytes(),b'workbook');self.assertEqual((target/'logs'/'fetch-log.txt').read_text(),'live fetching log')
        self.assertEqual((target/'logs'/'github-full-log.txt').read_text(),'All GitHub log messages')
    def test_existing_local_workbook_is_backed_up_before_replacement(self):
        source=self.root/'new.xlsx';source.write_bytes(b'new');destination=self.root/'PC'/'Store.xlsx';destination.parent.mkdir();destination.write_bytes(b'old')
        self.assertTrue(atomic_copy(source,destination));self.assertEqual(destination.read_bytes(),b'new')
        backups=list((destination.parent/'previous-cloud-files').iterdir());self.assertEqual(len(backups),1);self.assertEqual(backups[0].read_bytes(),b'old');self.assertFalse(atomic_copy(source,destination))
    def test_newer_final_diagnostics_override_older_live_report(self):
        def call(args):
            if args[0]=='api':return json.dumps({'artifacts':[{'id':2,'name':'chotuapp-diagnostics'},{'id':1,'name':'chotuapp-live-logs'}]})
            if args[:2]==['run','view']:return '{"status":"in_progress"}'
            (Path(args[-1])/'report.json').write_text('final' if 'chotuapp-diagnostics' in args else 'live');return ''
        target=self.root/'PC'
        with contextlib.redirect_stdout(io.StringIO()):Sync('gh','owner/repo','123',target,call).tick()
        self.assertEqual((target/'logs'/'report.json').read_text(),'final')

if __name__=='__main__':unittest.main()
