import hashlib,sqlite3,tempfile,unittest
from pathlib import Path
from checkpoint_compaction import compact_responses
from resume_support import ResponseCache
class CacheCompactionTests(unittest.TestCase):
 def test_legacy_and_new_responses_retain_exact_body_and_identity(self):
  import requests
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp)/'pages.sqlite3';cache=ResponseCache(p);body=b'<html>exact price 1234; stock false; size 38</html>'*1000
   cache.db.execute('INSERT INTO pages VALUES(?,?,?,?,?,?)',('https://source.test/book','https://source.test/book',body,'utf-8','text/html',hashlib.sha256(body).hexdigest()));cache.db.commit()
   response=requests.Response();response.status_code=200;response.url='https://source.test/new';response._content=body;cache.put(response.url,response);cache.close()
   self.assertEqual(compact_responses(p),1)
   cache=ResponseCache(p)
   for u in ['https://source.test/book','https://source.test/new']:self.assertEqual(cache.get(u).content,body)
   cache.close();self.assertEqual(compact_responses(p),0)
 def test_corrupt_legacy_body_never_gets_new_trusted_checksum(self):
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp)/'pages.sqlite3';cache=ResponseCache(p);cache.db.execute('INSERT INTO pages VALUES(?,?,?,?,?,?)',('url','url',b'x'*1000,'utf-8','text/html','bad'));cache.db.commit();cache.close();self.assertEqual(compact_responses(p),0)
