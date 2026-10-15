from copy import deepcopy
import json
from pathlib import Path
import sys
import tempfile
import threading
from types import SimpleNamespace
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import farda_source_support as source
import install_farda_source as installer
ROOT=Path(__file__).resolve().parents[1]

class FardaTests(unittest.TestCase):
    def fixture(self,data):
        calls=[]
        gate=SimpleNamespace(lock=threading.RLock(),baseline=.25,interval=4.61)
        tls=SimpleNamespace(fast_gate=gate,fast_worker_count=5)
        g={'_chotu_tls':tls,'get_json':lambda url:(calls.append(('api',url)) or data),'run_site':lambda *args:(calls.append(('run',args[:3])) or 'canonical result')}
        source.enable_farda_source(g);return g,calls,tls
    def test_known_shop_link_uses_canonical_engine_without_changing_data(self):
        data={'products':[{'id':1,'handle':'food','variants':[{'id':2,'price':'129.99','compare_at_price':'150','available':True},{'id':3,'price':'140','available':False}]}]};snapshot=deepcopy(data)
        g,calls,tls=self.fixture(data)
        result=g['run_site']('https://www.fardafoods.com','Farda Foods','template.xlsx',lambda s:None)
        self.assertEqual(result,'canonical result');self.assertEqual(calls[-1],('run',(source.SHOP,'Farda Foods','template.xlsx')))
        self.assertEqual(data,snapshot);self.assertEqual(tls.fast_worker_count,1);self.assertEqual(tls.fast_gate.interval,4.61)
        self.assertEqual(calls[0],('api',source.SHOP+'/products.json?limit=250&page=1'))
    def test_other_stores_are_untouched_and_make_no_probe(self):
        g,calls,tls=self.fixture(None);g['run_site']('https://www.shopmodest.pk','Modest','template',lambda s:None)
        self.assertEqual(calls,[('run',('https://www.shopmodest.pk','Modest','template'))]);self.assertEqual(tls.fast_worker_count,5)
    def test_empty_html_or_bad_variants_cannot_reach_export(self):
        for data in ({'products':[]},[],{'html':'page'},{'products':[{'id':1,'handle':'x','variants':[{'id':2,'price':100}]}]}):
            with self.subTest(data=data):
                g,calls,tls=self.fixture(data)
                with self.assertRaises(RuntimeError):g['run_site']('https://fardafoods.com','Farda','template',lambda s:None)
                self.assertFalse(any(c[0]=='run' for c in calls))
    def test_installer_only_adds_hook_with_backup_and_retains_user_files(self):
        original=(ROOT/'main.py').read_text();updated=installer.transform(original)
        self.assertEqual(updated.replace(installer.HOOK,''),original);self.assertEqual(installer.transform(updated),updated)
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'main.py').write_text(original);(root/'saved.sqlite3').write_bytes(b'keep')
            installer.install(root)
            self.assertEqual((root/'saved.sqlite3').read_bytes(),b'keep')
            self.assertEqual(next((root/'backups').glob('*/main.py')).read_text(),original)

    def test_healthy_farda_can_overlap_requests_without_erasing_recent_throttles(self):
        data={'products':[{'id':1,'handle':'food','variants':[{'id':2,'price':'10','available':True}]}]}
        g,calls,tls=self.fixture(data);tls.fast_gate.interval=.25
        g['run_site']('https://fardafoods.com','Farda','template',lambda s:None)
        self.assertEqual(tls.fast_worker_count,2);self.assertEqual(tls.fast_gate.interval,.5)
        import time
        g,calls,tls=self.fixture(data);tls.fast_gate.interval=2.5;tls.fast_gate.recovery_not_before=time.time()+1800
        g['run_site']('https://fardafoods.com','Farda','template',lambda s:None)
        self.assertEqual(tls.fast_worker_count,1);self.assertEqual(tls.fast_gate.interval,2.5)
