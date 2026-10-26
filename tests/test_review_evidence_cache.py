import json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from review_evidence_cache import read_review_evidence,_read
class ReviewCacheTests(unittest.TestCase):
 def test_reuse_and_same_length_replacement_refresh(self):
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp)/'facts.json';p.write_text('{"v":1}');_read.cache_clear()
   with patch('review_evidence_cache.json.loads',wraps=json.loads) as parse:
    self.assertEqual(read_review_evidence(p),{'v':1});self.assertEqual(read_review_evidence(p),{'v':1});self.assertEqual(parse.call_count,1)
    replacement=p.with_suffix('.new');replacement.write_text('{"v":2}');replacement.replace(p)
    self.assertEqual(read_review_evidence(p),{'v':2});self.assertEqual(parse.call_count,2)
