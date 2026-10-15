import sys
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
import sqlite3
import requests
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from resume_support import ResponseCache,SessionProxy

class HighSpeedCacheTests(unittest.TestCase):
    def test_api_path_avoids_duplicate_write_but_reuses_legacy_snapshot(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache=ResponseCache(Path(tmp)/'pages.sqlite3');calls=[]
            def get(url,**kwargs):
                calls.append(url);r=requests.Response();r.status_code=200;r.url=url;r._content=b'{"price":123}';return r
            proxy=SessionProxy(SimpleNamespace(get=get),SimpleNamespace(saved_response_cache=cache,fast_json_request=True),lambda:None)
            url='https://fixture/products/p.js'
            self.assertEqual(proxy.get(url).json(),{'price':123})
            self.assertIsNone(cache.get(url))
            legacy=get(url);cache.put(url,legacy);before=len(calls)
            self.assertEqual(proxy.get(url).json(),{'price':123});self.assertEqual(len(calls),before)
            cache.close()
    def test_html_remains_durable_and_wal_reads_while_writer_active(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'pages.sqlite3';cache=ResponseCache(path)
            self.assertEqual(cache.db.execute('pragma synchronous').fetchone()[0],2)
            self.assertEqual(cache.db.execute('pragma journal_mode').fetchone()[0],'wal')
            def get(url,**kwargs):
                r=requests.Response();r.status_code=200;r.url=url;r._content=b'<html>Product</html>';return r
            proxy=SessionProxy(SimpleNamespace(get=get),SimpleNamespace(saved_response_cache=cache),lambda:None)
            url='https://fixture/products/p';proxy.get(url)
            other=sqlite3.connect(path,timeout=.1)
            cache.db.execute('begin immediate')
            self.assertEqual(other.execute('select count(*) from pages').fetchone()[0],1)
            cache.db.rollback();other.close();cache.close()
            restored=ResponseCache(path);self.assertEqual(restored.get(url).content,b'<html>Product</html>');restored.close()
