import tempfile,unittest
from pathlib import Path
from openpyxl import Workbook,load_workbook
from complete_grocery_export import merge
class GroceryCompletionTests(unittest.TestCase):
 def create(self,path,pid,price):
  b=Workbook();b.remove(b.active)
  for name,key in [('Products','product_id'),('Product Images','image_id'),('Option Groups','group_id'),('Options','option_id'),('Variant Combinations','combination_id')]:
   s=b.create_sheet(name);s.append([key,'source_url','base_price (PKR)']);s.append([pid,'https://www.naheed.pk/'+pid,price])
  b.save(path);b.close()
 def test_append_preserves_existing_values_and_all_linked_sheets(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);self.create(root/'old.xlsx','old',200);self.create(root/'new.xlsx','new',350);merge(root/'old.xlsx',root/'new.xlsx',root/'combined.xlsx')
   b=load_workbook(root/'combined.xlsx')
   for s in b:
    self.assertEqual(s.cell(2,1).value,'old');self.assertEqual(s.cell(2,3).value,200);self.assertEqual(s.cell(3,1).value,'new');self.assertEqual(s.cell(3,3).value,350)
   b.close()
 def test_duplicate_product_identity_is_never_appended(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);self.create(root/'old.xlsx','same',200);self.create(root/'new.xlsx','same',350)
   with self.assertRaises(ValueError):merge(root/'old.xlsx',root/'new.xlsx',root/'combined.xlsx')
