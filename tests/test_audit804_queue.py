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
 def test_github_restore_checks_each_downloaded_part(self):
  import json,hashlib
  from unittest.mock import MagicMock
  data=b'checked catalog bytes';prefix='inputs/campaign/store/abcdef1234567890';marker=prefix+'/manifest.json'
  record={'store':'Store','campaign_id':'campaign','sha256':hashlib.sha256(data).hexdigest(),'parts':[{'path':prefix+'/source.xlsx.part-000','bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}]}
  def response(payload):
   obj=MagicMock();obj.__enter__.return_value=obj;obj.iter_content.return_value=[payload];return obj
  with tempfile.TemporaryDirectory() as tmp,patch.dict(os.environ,{'GH_TOKEN':'test-only-placeholder'}),patch('audit804_queue.subprocess.check_output',return_value='https://github.com/chottuapp/ChotuApp-Software.git'),patch('requests.get') as get:
   get.side_effect=[response(json.dumps(record).encode()),response(data)]
   self.assertEqual(queue.restore(marker,Path(tmp)/'ok.xlsx','Store','campaign').read_bytes(),data)
   get.side_effect=[response(json.dumps(record).encode()),response(b'changed bytes')]
   with self.assertRaisesRegex(ValueError,'part changed'):queue.restore(marker,Path(tmp)/'bad.xlsx','Store','campaign')
