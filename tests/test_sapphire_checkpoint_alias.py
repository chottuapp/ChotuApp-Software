import sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'cloud'));sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from partition_resume import partition
from resume_support import RunStore
class AliasTests(unittest.TestCase):
 def test_verified_sapphire_host_alias_preserves_saved_variant_cache(self):
  with tempfile.TemporaryDirectory() as tmp:
   data=Path(tmp);store=RunStore(data/'saved_runs');old=store.root/'original';(old/'0').mkdir(parents=True);(old/'template.xlsx').write_bytes(b'template');(old/'0/pages.sqlite3').write_bytes(b'selected variants');store.save({'id':'original','template':str(old/'template.xlsx'),'sites':[{'name':'Sapphire','url':'https://sapphireonline.pk','status':'failed'}]})
   state=partition(data,[{'name':'Sapphire','url':'https://pk.sapphireonline.pk'}]);self.assertEqual((store.root/state['id']/'0/pages.sqlite3').read_bytes(),b'selected variants');self.assertEqual(state['sites'][0]['url'],'https://sapphireonline.pk')
 def test_foreign_country_host_still_does_not_match_saved_store(self):
  with tempfile.TemporaryDirectory() as tmp:
   data=Path(tmp);store=RunStore(data/'saved_runs');store.save({'id':'original','sites':[{'name':'Khaadi','url':'https://pk.khaadi.com'}]})
   with self.assertRaisesRegex(ValueError,'does not match'):partition(data,[{'name':'Khaadi','url':'https://us.khaadi.com'}])
