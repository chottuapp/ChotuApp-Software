from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import install_responsive_ui
import rollback_responsive_ui as rollback
ROOT=Path(__file__).resolve().parents[1]

class RollbackTests(unittest.TestCase):
    def test_exactly_removes_ui_hook_preserving_all_other_source(self):
        source=(ROOT/'main.py').read_text()
        from install_fast_fetch import transform
        installed=transform(source)
        installed=install_responsive_ui.transform(installed)
        restored=rollback.transform(installed)
        self.assertEqual(restored,transform(source))
        self.assertEqual(rollback.transform(restored),restored)
    def test_backup_and_saved_files_unchanged(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp);original=(ROOT/'main.py').read_text();installed=install_responsive_ui.transform(original)
            (folder/'main.py').write_text(installed)
            for name in ('fast_fetch_support.py','resume_support.py','stores.json','saved_run.sqlite3','export.xlsx'):(folder/name).write_bytes(b'preserve')
            rollback.install(folder)
            self.assertEqual((folder/'main.py').read_text(),original)
            self.assertEqual(next((folder/'backups').glob('*/main.py')).read_text(),installed)
            for name in ('fast_fetch_support.py','resume_support.py','stores.json','saved_run.sqlite3','export.xlsx'):self.assertEqual((folder/name).read_bytes(),b'preserve')
    def test_unknown_modified_hook_fails_before_write(self):
        source=install_responsive_ui.transform((ROOT/'main.py').read_text()).replace('_enable_smooth_ui(globals())','_enable_smooth_ui( globals())')
        with self.assertRaises(RuntimeError):rollback.transform(source)
