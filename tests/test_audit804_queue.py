import os,subprocess,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import audit804_queue as queue
class QueueTests(unittest.TestCase):
 def test_durable_split_roundtrip_and_store_identity(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);remote=root/'remote.git';work=root/'work';work.mkdir()
   for args in (['git','init','--bare',str(remote)],['git','init',str(work)],['git','-C',str(work),'remote','add','origin',str(remote)]):subprocess.run(args,check=True,capture_output=True)
   source=root/'Source.xlsx';source.write_bytes(b'catalog-source-fixture'*5);before=Path.cwd()
   try:
    os.chdir(work)
    with patch.object(queue,'CHUNK',10):marker=queue.save(source,'Store','fresh804-20261021-deadbeef','123')
    source.write_bytes(b'changed local source')
    output=queue.restore(marker,root/'restored.xlsx','Store','fresh804-20261021-deadbeef');self.assertEqual(output.read_bytes(),b'catalog-source-fixture'*5)
    with self.assertRaises(ValueError):queue.restore(marker,root/'wrong.xlsx','Different Store','fresh804-20261021-deadbeef')
   finally:os.chdir(before)
