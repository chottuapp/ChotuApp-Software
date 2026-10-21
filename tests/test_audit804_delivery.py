import json,shutil,tempfile,unittest
from pathlib import Path
from openpyxl import Workbook
from audit804_delivery import DriveIdentity,completed_files
class DeliveryTests(unittest.TestCase):
 def book(self,path,code,description='old'):
  b=Workbook();s=b.active;s.title='Products';s.append(['shop_code','product_id','description']);s.append([code,'P1',description]);b.save(path)
 def exercise(self,fail=False,alias=False,wrong=False):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);remote=root/'remote';remote.mkdir();oldname='Custom old name.xlsx' if alias else 'Store.xlsx';self.book(remote/oldname,'OTHER' if wrong else 'S1');new=root/'new.xlsx';self.book(new,'S1','new');calls=[]
   def rc(*args):
    calls.append(args)
    if args[0]=='lsjson':return json.dumps([{'Name':p.name} for p in remote.glob('*.xlsx')])
    if args[0]=='copy':
     if args[1].startswith('chotudrive:'):
      for p in remote.glob('*.xlsx'):shutil.copy2(p,Path(args[2])/p.name)
     else:
      name=args[args.index('--include')+1];shutil.copy2(Path(args[1])/name,remote/name)
    if args[0]=='check' and fail:raise RuntimeError('checksum check failed')
    if args[0]=='copyto':shutil.copy2(args[1],remote/Path(args[2]).name)
    return ''
   before=(remote/oldname).read_bytes()
   with DriveIdentity(rc,'F') as identity:
    if fail or wrong:
     with self.assertRaises((RuntimeError,ValueError)):identity.replace(new,'S1','Store.xlsx')
     self.assertEqual((remote/oldname).read_bytes(),before)
    else:
     result=identity.replace(new,'S1','Store.xlsx');self.assertEqual(result['file_name'],oldname);self.assertEqual(len(list(remote.glob('*.xlsx'))),1)
   if wrong:self.assertFalse(any(c[0]=='check' for c in calls))
 def test_same_code_replacement_keeps_single_file(self):self.exercise()
 def test_alias_matches_by_code_not_filename(self):self.exercise(alias=True)
 def test_failed_check_restores_old_file(self):self.exercise(fail=True)
 def test_wrong_code_never_overwritten(self):self.exercise(wrong=True)
 def test_only_completed_exports_selected(self):
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp);(p/'completion-manifest.json').write_text(json.dumps({'files':[{'store':'A','complete':True},{'store':'B','complete':False}]}));self.assertEqual([r['store'] for r in completed_files(p)],['A'])
