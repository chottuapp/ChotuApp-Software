"""Reuse immutable review evidence within one process; refresh on file replacement."""
import json
from functools import lru_cache
from pathlib import Path

@lru_cache(maxsize=8)
def _read(path,mtime_ns,ctime_ns,size):
 return json.loads(Path(path).read_text())

def read_review_evidence(path):
 path=Path(path);stat=path.stat()
 return _read(str(path.resolve()),stat.st_mtime_ns,stat.st_ctime_ns,stat.st_size)
