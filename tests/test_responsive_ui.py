import importlib.util
from pathlib import Path
import queue
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import responsive_ui_support as support
import install_responsive_ui as installer
ROOT=Path(__file__).resolve().parents[1]

class ResponsiveTests(unittest.TestCase):
    def test_installer_changes_only_startup_hook_and_backs_up(self):
        source=(ROOT/'main.py').read_text();updated=installer.transform(source)
        self.assertEqual(updated.replace(installer.HOOK,''),source)
        self.assertEqual(installer.transform(updated),updated)
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'main.py').write_text(source);(root/'saved.txt').write_text('keep')
            installer.install(root)
            self.assertEqual((root/'saved.txt').read_text(),'keep')
            self.assertEqual(next((root/'backups').glob('*/main.py')).read_text(),source)
    def test_slow_disk_write_does_not_block_producer(self):
        entered=threading.Event();release=threading.Event()
        class SlowPath:
            def open(self,*args,**kwargs):
                entered.set();release.wait(2)
                import io
                return io.StringIO()
        writer=support.AsyncLog(SlowPath())
        try:
            start=time.monotonic()
            with writer.open('a') as stream:stream.write('first\n')
            self.assertLess(time.monotonic()-start,.1);self.assertTrue(entered.wait(1))
            with writer.open('a') as stream:stream.write('second\n')
            self.assertLess(time.monotonic()-start,.2)
        finally:release.set();writer.shutdown()
    def test_native_gui_cached_event_flood_and_restore(self):
        import tkinter as tk
        import resume_support
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'main.py';path.write_bytes((ROOT/'main.py').read_bytes())
            spec=importlib.util.spec_from_file_location('ui_fixture',path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
            resume_support.enable_resume(m.__dict__);support.enable_responsive_ui(m.__dict__)
            root=tk.Tk();app=m.App(root);root.update()
            try:
                app._ui_minimized=True;app._quiet_ui=True
                for i in range(1200):app.events.put(('__DEBUG__','HTTP START attempt=1 fixture '+str(i)))
                beats=[]
                def beat():beats.append(time.monotonic());root.after(10,beat)
                root.after(10,beat)
                end=time.monotonic()+1.0
                while time.monotonic()<end:root.update();time.sleep(.002)
                self.assertGreater(len(beats),15)
                self.assertTrue(app._quiet_ui)
                self.assertTrue(app.debug_box.pending)
                count=app._ui_request_count;self.assertGreater(count,0)
                app._ui_minimized=False;app._ui_resize_until=0;app._quiet_flush()
                self.assertFalse(app.debug_box.pending)
                self.assertEqual(app.metric_values['requests'].cget('text'),f'{count:,}')
                app.debug_file.items.join()
                self.assertIn('fixture',app.debug_file.read_text())
                self.assertIn('Smooth UI',root.title())
            finally:app.debug_file.shutdown();root.destroy()
