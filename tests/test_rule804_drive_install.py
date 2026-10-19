import importlib.util,unittest,copy
from pathlib import Path
s=importlib.util.spec_from_file_location('installer',Path(__file__).resolve().parents[1]/'catalog-tools/install_rule804_completed23_drive.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class DriveTests(unittest.TestCase):
 def setUp(self):
  self.manifest={'files':[{'file':'Store.xlsx','source_md5':'original','md5':'reviewed'}]}
 def test_original_pending_and_completed_skipped(self):
  self.assertEqual(m.validate_inventory([{'Name':'Store.xlsx','Hashes':{'md5':'original'}}],self.manifest),['Store.xlsx'])
  self.assertEqual(m.validate_inventory([{'Name':'Store.xlsx','Hashes':{'md5':'reviewed'}}],self.manifest),[])
 def test_newer_user_edit_rejected(self):
  with self.assertRaisesRegex(ValueError,'changed since'):m.validate_inventory([{'Name':'Store.xlsx','Hashes':{'md5':'user-edit'}}],self.manifest)
 def test_missing_duplicate_and_unhashed_rejected(self):
  item={'Name':'Store.xlsx','Hashes':{'md5':'original'}}
  for items in [[],[item,item],[{'Name':'Store.xlsx','Hashes':{}}]]:
   with self.assertRaises(ValueError):m.validate_inventory(items,self.manifest)
if __name__=='__main__':unittest.main()
