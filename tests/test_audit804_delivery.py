import json,shutil,tempfile,unittest
from pathlib import Path
from openpyxl import Workbook
from audit804_delivery import DriveIdentity,completed_files
class DeliveryTests(unittest.TestCase):
 def book(self,path,code,description='old'):
  b=Workbook();s=b.active;s.title='Products';s.append(['shop_code','product_id','description','source_url']);s.append([code,'P1',description,'https://store.example/products/one']);b.save(path)
 def exercise(self,fail=False,alias=False,wrong=False,blank=False,migrate=False,finalfail=False):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);remote=root/'remote';remote.mkdir();oldname='Custom old name.xlsx' if alias else 'Store.xlsx';self.book(remote/oldname,None if migrate else 'OTHER' if wrong else 'S1');new=root/'new.xlsx';self.book(new,None if blank else 'S1','new');calls=[];wrote=[False]
   def local(path):return remote/str(path).removeprefix('chotudrive:F').lstrip('/') if str(path).startswith('chotudrive:') else Path(path)
   def rc(*args):
    calls.append(args)
    if args[0]=='lsjson':return json.dumps([{'Name':p.name} for p in remote.glob('*.xlsx')])
    if args[0]=='copy':
     if args[1].startswith('chotudrive:'):
      for p in remote.glob('*.xlsx'):shutil.copy2(p,Path(args[2])/p.name)
     else:
      wrote[0]=True;name=args[args.index('--include')+1];dest=local(args[2])/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(Path(args[1])/name,dest)
    if args[0]=='check' and wrote[0] and (fail or finalfail and args[2]=='chotudrive:F'):raise RuntimeError('checksum check failed')
    if args[0]=='copyto':
     src=local(args[1]);dest=local(args[2]);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dest)
    if args[0]=='deletefile':local(args[1]).unlink(missing_ok=True)
    return ''
   before=(remote/oldname).read_bytes()
   with DriveIdentity(rc,'F') as identity:
    if fail or wrong or finalfail:
     with self.assertRaises((RuntimeError,ValueError)):identity.replace(new,None if blank else 'S1','Store.xlsx')
     self.assertEqual((remote/oldname).read_bytes(),before)
    else:
     result=identity.replace(new,None if blank else 'S1','Store.xlsx');self.assertEqual(result['file_name'],oldname);self.assertEqual(len(list(remote.glob('*.xlsx'))),1)
   if not fail and not wrong and not finalfail:
    promotion=next(i for i,c in enumerate(calls) if c[0]=='copyto' and str(c[1]).startswith('chotudrive:'))
    self.assertTrue(any(c[0]=='check' and '/_incoming/' in str(c[2]) for c in calls[:promotion]))
   if wrong:self.assertFalse(any(c[0]=='check' for c in calls))
 def test_same_code_replacement_keeps_single_file(self):self.exercise()
 def test_alias_matches_by_code_not_filename(self):self.exercise(alias=True)
 def test_failed_check_restores_old_file(self):self.exercise(fail=True)
 def test_wrong_code_never_overwritten(self):self.exercise(wrong=True)
 def test_only_completed_exports_selected(self):
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp);(p/'completion-manifest.json').write_text(json.dumps({'files':[{'store':'A','complete':True},{'store':'B','complete':False}]}));self.assertEqual([r['store'] for r in completed_files(p)],['A'])

 def test_owner_authorized_blank_matches_exact_store_filename(self):self.exercise(blank=True)
 def test_blank_identity_checksum_failure_restores_old(self):self.exercise(blank=True,fail=True)

 def test_confirmed_code_migrates_exact_blank_store_file(self):self.exercise(migrate=True)
 def test_migration_verification_failure_rolls_back_blank_original(self):self.exercise(migrate=True,fail=True)

 def test_failed_final_verification_restores_old_after_staged_upload(self):self.exercise(finalfail=True)
