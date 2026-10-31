"""Lossless migration of legacy raw response caches before checkpoint packaging."""
import hashlib,sqlite3,zlib
from pathlib import Path

def compact_responses(path):
 path=Path(path);changed=0
 with sqlite3.connect(path,timeout=30) as db:
  tables={r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
  if 'pages' not in tables:return 0
  db.execute('CREATE TABLE IF NOT EXISTS page_format(url TEXT PRIMARY KEY,codec TEXT NOT NULL,raw_bytes INTEGER NOT NULL)')
  cursor=db.execute("SELECT p.url,p.body,p.checksum,f.codec,f.raw_bytes FROM pages p LEFT JOIN page_format f ON f.url=p.url WHERE f.codec IS NULL OR f.codec IN ('raw','zlib-v1')")
  for url,body,digest,codec,raw_bytes in cursor:
   if not isinstance(body,bytes) or not 512<=len(body)<=64*1024**2:continue
   if hashlib.sha256(body).hexdigest()!=digest:continue
   original=body
   if codec=='zlib-v1':
    if not isinstance(raw_bytes,int) or not 0<=raw_bytes<=64*1024**2:continue
    try:
     decoder=zlib.decompressobj();original=decoder.decompress(body,raw_bytes+1)
     if len(original)!=raw_bytes or not decoder.eof or decoder.unused_data:continue
    except zlib.error:continue
   packed=zlib.compress(original,6)
   if len(packed)>=len(body)*.9:continue
   db.execute('UPDATE pages SET body=?,checksum=? WHERE url=?',(packed,hashlib.sha256(packed).hexdigest(),url))
   db.execute('INSERT OR REPLACE INTO page_format VALUES(?,?,?)',(url,'zlib-v1',len(original)));changed+=1
  db.commit()
  if changed:
   db.execute('PRAGMA wal_checkpoint(TRUNCATE)')
   db.execute('VACUUM')
 return changed
