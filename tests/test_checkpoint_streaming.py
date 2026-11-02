import os
import tempfile
import unittest
import zipfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from checkpoint_parts import archive_writer,archive_path


class StreamingCheckpointTests(unittest.TestCase):
 def test_streams_with_space_for_one_archive_and_roundtrips_exact_source_bytes(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);target=root/'checkpoint.zip';payload=os.urandom(300*1024);budget=400*1024
   def disk(_):return SimpleNamespace(free=budget-sum(p.stat().st_size for p in root.rglob('*') if p.is_file()))
   with patch('checkpoint_parts.shutil.disk_usage',side_effect=disk):
    with archive_writer(target,part_bytes=128*1024,max_bytes=1024*1024,reserve=0) as archive:archive.writestr('saved_runs/exact.bin',payload)
   self.assertFalse(target.exists());self.assertTrue(target.with_suffix('.parts').is_dir());self.assertFalse(target.with_suffix('.pending.zip').exists())
   with archive_path(target.with_suffix('.parts')) as complete:
    with zipfile.ZipFile(complete) as archive:self.assertEqual(archive.read('saved_runs/exact.bin'),payload)
 def test_small_checkpoint_stays_legacy_zip_compatible(self):
  with tempfile.TemporaryDirectory() as tmp:
   target=Path(tmp)/'checkpoint.zip'
   with archive_writer(target,reserve=0) as archive:archive.writestr('saved_runs/state.json','{"stock":false,"price":1234.50}')
   with zipfile.ZipFile(target) as archive:self.assertEqual(archive.read('saved_runs/state.json'),b'{"stock":false,"price":1234.50}')
 def test_bound_failure_preserves_previous_checkpoint_and_removes_partial_parts(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);target=root/'checkpoint.zip';target.write_bytes(b'previous verified checkpoint')
   with self.assertRaisesRegex(ValueError,'safety limit'):
    with archive_writer(target,part_bytes=128,max_bytes=256,reserve=0) as archive:archive.writestr('saved_runs/data.bin',os.urandom(1024))
   self.assertEqual(target.read_bytes(),b'previous verified checkpoint');self.assertEqual(sorted(p.name for p in root.iterdir()),['checkpoint.zip'])
