import sys,tempfile,unittest,zipfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'cloud'))
from checkpoint_parts import split_archive,archive_path
from cli import checkpoint,restore
class PartTests(unittest.TestCase):
 def test_large_save_and_restore_roundtrip(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);data=root/'data';(data/'saved_runs').mkdir(parents=True);(data/'saved_runs'/'fixture.txt').write_bytes(bytes(range(256))*10)
   checkpoint(data,root/'checkpoint.zip',max_bytes=100)
   self.assertFalse((root/'checkpoint.zip').exists());self.assertTrue((root/'checkpoint.parts'/'manifest.json').exists())
   restore(root,root/'restored');self.assertEqual((root/'restored'/'saved_runs'/'fixture.txt').read_bytes(),bytes(range(256))*10)
 def test_corrupt_part_is_rejected_before_extracting(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);source=root/'input';source.write_bytes(b'abc'*100);parts=split_archive(source,root/'parts',part_bytes=100)
   (parts/'part-0000.bin').write_bytes(b'x'*100)
   with self.assertRaisesRegex(ValueError,'checksum'):
    with archive_path(parts):self.fail('Corrupt checkpoint accepted')
 def test_legacy_zip_still_works(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);path=root/'checkpoint.zip';path.write_bytes(b'legacy')
   with archive_path(root) as actual:self.assertEqual(actual,path)
if __name__=='__main__':unittest.main()
