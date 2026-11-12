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
 def test_scope_repair_uses_current_checkpoint_not_hardcoded_old_indexes(self):
  from complete_grocery_export import pending_scope_indexes
  pages=[{'url':'https://www.naheed.pk/scope/'+str(i)} for i in range(4)]
  snapshots={p['url']:{'links':['one'],'pages':['page1'],'total':1,'count_changed':False} for p in pages}
  snapshots[pages[2]['url']]['count_changed']=True
  self.assertEqual(pending_scope_indexes(pages,snapshots,1),{3})
  self.assertEqual(pending_scope_indexes(pages,snapshots,2),{1,2,3,4})
