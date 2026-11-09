import tempfile,unittest
from pathlib import Path
from openpyxl import Workbook,load_workbook
from grocery_scope_repair import repair
from subcategory_inference_support import apply
from website_order_support import apply_order
SCOPE='https://www.naheed.pk/allproducts/?manufacturer=890'
class GroceryScopeRepairTests(unittest.TestCase):
 def test_final_sort_preserves_explicit_owner_heading(self):
  row=dict(product_id='p',name='Dawn Garlic Croutons',description='Croutons with wheat.',source_url='https://www.naheed.pk/item',owner_scope_url=SCOPE,subcategory_source='owner_supplied_scope',Category='Bread, Bakery & Pasta',source_scope_coverage_status='review_required',source_scope_review_count=4)
  apply_order([row]);self.assertEqual(row['Category'],'Bread, Bakery & Pasta');self.assertEqual(row['subcategory_source'],'owner_supplied_scope');self.assertEqual(row['source_scope_review_count'],4)
 def test_saved_category_repair_preserves_money_and_coverage_hold(self):
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp)/'source.xlsx';out=Path(tmp)/'fixed.xlsx';b=Workbook();s=b.active;s.title='Products'
   row=dict(Category='Croutons',owner_scope_url=SCOPE,source_url='https://www.naheed.pk/item',source_manufacturer='Dawn',subcategory_source='inferred_description',subcategory_evidence='old generic inference',source_scope_coverage_status='review_required',source_scope_review_count=4,**{'base_price (PKR)':200})
   s.append(list(row));s.append(list(row.values()));b.save(p);b.close();path,count=repair(p,out,'ChotuApp Groceries');self.assertEqual(count,1)
   b=load_workbook(path);s=b['Products'];r=dict(zip([c.value for c in s[1]],[c.value for c in s[2]]));b.close();self.assertEqual(r['Category'],'Bread, Bakery & Pasta');self.assertEqual(r['base_price (PKR)'],200);self.assertEqual(r['source_scope_review_count'],4);self.assertEqual(r['source_scope_coverage_status'],'review_required')
 def test_unknown_scope_does_not_bypass_inference(self):
  with self.assertRaises(ValueError):apply(dict(name='Serum',source_url='https://other.example/item',owner_scope_url=SCOPE,subcategory_source='owner_supplied_scope'))
