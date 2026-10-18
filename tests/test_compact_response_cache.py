import hashlib,sqlite3,tempfile,unittest,json,sys
from pathlib import Path
import requests
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'cloud'))
from resume_support import ResponseCache
from continuation_policy import progress_token
class CompactCacheTests(unittest.TestCase):
 def response(self,body):
  r=requests.Response();r.status_code=200;r.url='https://example.com/product';r._content=body;r.encoding='utf-8';r.headers['Content-Type']='text/html';return r
 def test_compressed_cache_returns_exact_body_across_restart(self):
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp)/'pages.sqlite3';c=ResponseCache(p);body=('<html>Exact price 1499.95 and product details.</html>'*20000).encode();r=self.response(body);c.put(r.url,r)
   stored=c.db.execute('SELECT body FROM pages').fetchone()[0];self.assertLess(len(stored),len(body)//10);self.assertEqual(c.get(r.url).content,body);c.close();c=ResponseCache(p);self.assertEqual(c.get(r.url).content,body);c.close()
 def test_legacy_raw_cache_and_new_format_coexist(self):
  with tempfile.TemporaryDirectory() as tmp:
   c=ResponseCache(Path(tmp)/'pages.sqlite3');body=b'legacy body';c.db.execute('INSERT INTO pages VALUES(?,?,?,?,?,?)',('https://legacy','https://legacy',body,'utf-8','text/html',hashlib.sha256(body).hexdigest()));c.db.commit();self.assertEqual(c.get('https://legacy').content,body);c.close()
 def test_truncated_compressed_response_is_not_replayed(self):
  with tempfile.TemporaryDirectory() as tmp:
   c=ResponseCache(Path(tmp)/'pages.sqlite3');r=self.response(b'body'*10000);c.put(r.url,r);bad=c.db.execute('SELECT body FROM pages').fetchone()[0][:-4];c.db.execute('UPDATE pages SET body=?,checksum=?',(bad,hashlib.sha256(bad).hexdigest()));c.db.commit();self.assertIsNone(c.get(r.url));c.close()
 def test_failed_responses_are_still_not_cached(self):
  with tempfile.TemporaryDirectory() as tmp:
   c=ResponseCache(Path(tmp)/'pages.sqlite3');r=self.response(b'denied'*1000);r.status_code=429;c.put(r.url,r);self.assertIsNone(c.get(r.url));c.close()
 def test_html_cache_progress_prevents_false_stall_detection(self):
  with tempfile.TemporaryDirectory() as tmp:
   state={'id':'a','sites':[{'status':'pending'}]};p=Path(tmp)/'a/0';p.mkdir(parents=True);before=progress_token(state,tmp);c=ResponseCache(p/'pages.sqlite3');r=self.response(b'page');c.put(r.url,r);c.close();self.assertNotEqual(progress_token(state,tmp),before)
if __name__=='__main__':unittest.main()
