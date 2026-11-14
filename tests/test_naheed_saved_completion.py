import csv,tempfile,unittest
from pathlib import Path
from openpyxl import Workbook,load_workbook
from complete_naheed_brand_export import saved_coverage,verify_old_values

class SavedNaheedCompletionTests(unittest.TestCase):
 def test_saved_receipts_target_only_unresolved_scopes_and_cannot_omit_a_brand(self):
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp)/'SCOPE COVERAGE.csv';fields=['scope_url','pages','products','reported_total','coverage_status']
   with p.open('w',newline='') as f:
    w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerow(dict(scope_url='a',pages=1,products=2,reported_total=2,coverage_status='complete'));w.writerow(dict(scope_url='b',pages=1,products=3,reported_total='',coverage_status='review_required'))
   r=saved_coverage(tmp,{'a','b'});self.assertTrue(r['a']['complete']);self.assertFalse(r['b']['complete'])
   with self.assertRaises(ValueError):saved_coverage(tmp,{'a','b','c'})
 def workbook(self,path):
  b=Workbook();b.remove(b.active)
  for name in ('Products','Product Images','Option Groups','Options','Variant Combinations'):
   s=b.create_sheet(name);s.append(['id','base_price (PKR)','Category']);s.append(['old',200,'Old'])
  b.save(path);b.close()
 def test_category_repair_can_never_change_existing_price_or_linked_rows(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);a=root/'a.xlsx';b=root/'b.xlsx';self.workbook(a);self.workbook(b)
   book=load_workbook(b);book['Products']['C2']='Verified';book.save(b);book.close();verify_old_values(a,b)
   book=load_workbook(b);book['Products']['B2']=201;book.save(b);book.close()
   with self.assertRaises(ValueError):verify_old_values(a,b)
   self.workbook(b);book=load_workbook(b);book['Options']['A2']='changed';book.save(b);book.close()
   with self.assertRaises(ValueError):verify_old_values(a,b)
