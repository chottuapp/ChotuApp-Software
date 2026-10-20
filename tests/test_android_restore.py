import importlib.util,io,json,hashlib,tarfile,tempfile,unittest
from pathlib import Path
spec=importlib.util.spec_from_file_location('restore',Path(__file__).resolve().parents[1]/'catalog-tools/restore_android_studio_windows.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class RestoreTests(unittest.TestCase):
 def test_restores_cache_not_engine_and_rebases_export(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);archive=root/'backup.tar';records=[]
   with tarfile.open(archive,'w:') as tar:
    for name,data in [('files/khaadi/local-status.json',json.dumps({'status':'paused','files':['/old/files/Khaadi.xlsx']}).encode()),('files/khaadi/responses.sqlite3',b'saved-response-cache'),('files/engine/main.py',b'old code')]:
     item=tarfile.TarInfo(name);item.size=len(data);tar.addfile(item,io.BytesIO(data));records.append({'path':name,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()})
   manifest=root/'manifest.json';manifest.write_text(json.dumps({'archive_sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'files':records}))
   output=root/'restore.tar';self.assertEqual(m.prepare(archive,manifest,output),2)
   with tarfile.open(output) as tar:
    self.assertNotIn('files/engine/main.py',tar.getnames());state=json.load(tar.extractfile('files/khaadi/local-status.json'));self.assertIn('com.chotuapp.studio',state['files'][0])
   archive.write_bytes(b'changed')
   with self.assertRaises(ValueError):m.prepare(archive,manifest,output)
