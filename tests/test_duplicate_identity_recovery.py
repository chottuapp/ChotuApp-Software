import json,shutil,tempfile,unittest
from pathlib import Path
from openpyxl import Workbook
from audit804_delivery import DriveIdentity

class DuplicateIdentityRecoveryTests(unittest.TestCase):
 def exercise(self,conflicting=False,unknown=False,missing_id=False):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);objects=root/'objects';objects.mkdir();calls=[]
   def book(path,code):
    w=Workbook();w.active.title='Products';w.active.append(['shop_code']);w.active.append([code]);w.save(path)
   for id,code in [('a','S1'),('b',None if unknown else 'S2' if conflicting else 'S1'),('c','S3')]:book(objects/(id+'.xlsx'),code)
   items=[{'Name':'Duplicate.xlsx','ID':'a'},{'Name':'Duplicate.xlsx','ID':'b'},{'Name':'Other.xlsx','ID':'c'}]
   if missing_id:items[1].pop('ID')
   def rc(*args):
    calls.append(args)
    if args[0]=='lsjson':return json.dumps(items)
    if args[:2]==('backend','copyid'):shutil.copy2(objects/(args[3]+'.xlsx'),args[4])
    if args[0]=='copy':return ''
    if args[0]=='check':return ''
    if args[0]=='copyto':return ''
    if args[0]=='deletefile':return ''
    return ''
   identity=DriveIdentity(rc,'F')
   try:
    if missing_id:
     with self.assertRaisesRegex(ValueError,'identity missing'):identity.__enter__()
     self.assertFalse(any(c[0] in ('copy','copyto','deletefile') for c in calls));return
    identity.__enter__()
    self.assertEqual(sum(c[:2]==('backend','copyid') for c in calls),3)
    self.assertFalse(any(c[0] in ('copy','copyto','deletefile') for c in calls))
    incoming=root/'new.xlsx';book(incoming,'S3')
    if unknown:
     with self.assertRaisesRegex(ValueError,'duplicate workbook'):identity.replace(incoming,'S3','Other.xlsx')
    else:self.assertEqual(identity.replace(incoming,'S3','Other.xlsx')['file_name'],'Other.xlsx')
    book(incoming,'S1')
    with self.assertRaises(ValueError):identity.replace(incoming,'S1','Duplicate.xlsx')
    self.assertFalse(any(c[0] in ('dedupe','moveid','moveto') for c in calls))
    self.assertFalse(any(c[0]=='copyto' and c[2].endswith('/Duplicate.xlsx') for c in calls))
   finally:identity.__exit__(None,None,None)
 def test_duplicate_copies_do_not_block_other_verified_identity(self):self.exercise()
 def test_different_codes_in_duplicate_copies_are_both_indexed(self):self.exercise(conflicting=True)
 def test_unreadable_duplicate_identity_keeps_replacements_held(self):self.exercise(unknown=True)
 def test_missing_object_id_never_falls_back_to_name(self):self.exercise(missing_id=True)
