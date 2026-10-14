from pathlib import Path
import importlib.util
import json
import sys
import tempfile
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import remove_daily_auto as remover
import install_daily_auto
import install_fast_fetch

class ManualTests(unittest.TestCase):
    def test_removal_preserves_all_other_source_and_is_idempotent(self):
        source=install_fast_fetch.transform(install_daily_auto.transform((ROOT/'main.py').read_text()))
        changed=remover.transform(source)
        expected=source.replace(remover.AUTO_HOOK,'')
        self.assertEqual(changed.replace(remover.MANUAL_HOOK,''),expected)
        self.assertEqual(remover.transform(changed),changed)
        self.assertIn(install_fast_fetch.FAST_HOOK,changed)
        self.assertNotIn('_enable_daily_automation(globals())',changed)

    def test_disable_owned_startup_and_settings_without_touching_saved_queue(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);backup=root/'backup';backup.mkdir();startup=root/'startup.cmd'
            settings={'enabled':True,'startup':True,'sites':[{'name':'Vince'}],'time':'09:00','inflight':{'run_id':'keep'}}
            (root/'daily_automation.json').write_text(json.dumps(settings));(root/'saved.txt').write_bytes(b'keep')
            startup.write_text(remover.STARTUP_MARKER+'\nold command')
            remover.disable_settings(root,backup,startup)
            result=json.loads((root/'daily_automation.json').read_text())
            self.assertFalse(result['enabled']);self.assertFalse(result['startup'])
            self.assertEqual(result['sites'],settings['sites']);self.assertEqual(result['inflight'],settings['inflight'])
            self.assertFalse(startup.exists());self.assertTrue((backup/'daily_startup.cmd').is_file())
            self.assertEqual((root/'saved.txt').read_bytes(),b'keep')
            startup.write_text('unrelated user launcher');remover.disable_settings(root,backup,startup)
            self.assertEqual(startup.read_text(),'unrelated user launcher')

    def test_actual_gui_no_auto_panel_and_manual_selected_fetch(self):
        import requests
        original_factory=requests.Session
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);target=root/'app';target.mkdir()
            source=install_fast_fetch.transform(install_daily_auto.transform((ROOT/'main.py').read_text()))
            (target/'main.py').write_text(source);(target/'saved.keep').write_bytes(b'progress')
            remover.install(target)
            sys.path.insert(0,str(target))
            spec=importlib.util.spec_from_file_location('manual_gui',target/'main.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
            module.HOME=root;module.CONFIG=root/'sites.json';module.OUT=root/'exports'
            module.CONFIG.write_text(json.dumps([{'name':'A','url':'https://a.example'},{'name':'B','url':'https://b.example'},{'name':'C','url':'https://c.example'}]))
            rootwin=module.tk.Tk();errors=[];rootwin.report_callback_exception=lambda *args:errors.append(args)
            app=module.App(rootwin)
            try:
                rootwin.update();self.assertFalse(hasattr(app,'auto_panel'));self.assertTrue(app.saved_controls.winfo_ismapped())
                self.assertTrue(module._chotu_fast_fetch_enabled)
                app.template.set(str(ROOT/'importer-files/Chotu_Products_Import_Template_Discount_Tags.xlsx'))
                app.store_checks['https://a.example'].set(True);app.store_checks['https://c.example'].set(True)
                with patch.object(app,'_launch_jobs') as launch:
                    app.start_selected();chosen,template=launch.call_args.args
                    self.assertEqual([x['name'] for x in chosen],['A','C'])
                    launch.reset_mock();app._top20_auto_tick();launch.assert_not_called()
                self.assertFalse(errors);self.assertEqual((target/'saved.keep').read_bytes(),b'progress')
            finally:
                for cb in rootwin.tk.splitlist(rootwin.tk.call('after','info')):rootwin.tk.call('after','cancel',cb)
                rootwin.destroy();requests.Session=original_factory;sys.path.remove(str(target))
