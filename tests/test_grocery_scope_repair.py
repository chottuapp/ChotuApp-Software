import tempfile,unittest
from pathlib import Path
from openpyxl import Workbook,load_workbook
from grocery_scope_repair import repair
from subcategory_inference_support import apply
from website_order_support import apply_order
SCOPE='https://www.naheed.pk/allproducts/?manufacturer=890'
class GroceryScopeRepairTests(unittest.TestCase):
 def test_final_sort_preserves_exact_brand_category_and_coverage_hold(self):
  row=dict(name='Dawn Garlic Croutons',Category='Snacks',source_url='https://www.naheed.pk/item',owner_scope_url='https://www.naheed.pk/catalogsearch/result/?q=Dawn',source_manufacturer='Dawn',subcategory_source='owner_brand_search',website_category_path='Groceries > Snacks',website_category_source_url='https://www.naheed.pk/item',website_category_status='verified_product_breadcrumb',website_category_checked_at='2026-11-14T00:00:00Z',source_scope_coverage_status='review_required',source_scope_review_count=34)
  apply_order([row]);self.assertEqual(row['subcategory_source'],'owner_brand_search');self.assertEqual(row['Category'],'Snacks');self.assertEqual(row['source_scope_review_count'],34)
 def test_final_sort_preserves_explicit_owner_heading(self):
  row=dict(product_id='p',name='Dawn Garlic Croutons',description='Croutons with wheat.',source_url='https://www.naheed.pk/item',owner_scope_url=SCOPE,subcategory_source='owner_supplied_scope',Category='Bread, Bakery & Pasta',source_scope_coverage_status='review_required',source_scope_review_count=4)
  apply_order([row]);self.assertEqual(row['Category'],'Bread, Bakery & Pasta');self.assertEqual(row['subcategory_source'],'owner_supplied_scope');self.assertEqual(row['source_scope_review_count'],4)
 def test_saved_category_repair_preserves_money_and_coverage_hold(self):
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp)/'source.xlsx';out=Path(tmp)/'fixed.xlsx';b=Workbook();s=b.active;s.title='Products'
   row=dict(Category='Croutons',owner_scope_url=SCOPE,source_url='https://www.naheed.pk/item',source_manufacturer='Dawn',subcategory_source='inferred_description',subcategory_evidence='old generic inference',source_scope_coverage_status='review_required',source_scope_review_count=4,**{'base_price (PKR)':200})
   s.append(list(row));s.append(list(row.values()));b.save(p);b.close();path,count=repair(p,out,'ChotuApp Groceries');self.assertEqual(count,1)
   b=load_workbook(path);s=b['Products'];r=dict(zip([c.value for c in s[1]],[c.value for c in s[2]]));b.close();self.assertEqual(r['Category'],'Bread, Bakery & Pasta');self.assertEqual(r['base_price (PKR)'],200);self.assertEqual(r['source_scope_review_count'],4);self.assertEqual(r['source_scope_coverage_status'],'review_required')
 def test_saved_brand_metadata_recovery_uses_retained_source_and_keeps_coverage_hold(self):
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp)/'source.xlsx';out=Path(tmp)/'fixed.xlsx';b=Workbook();s=b.active;s.title='Products'
   row=dict(Category='Wrong inferred label',owner_scope_url='https://www.naheed.pk/catalogsearch/result/?q=Rose+Petal',source_url='https://www.naheed.pk/item',source_manufacturer='Rose Petal',subcategory_source='inferred_description',subcategory_evidence='old inference',source_scope_coverage_status='review_required',source_scope_review_count=34,website_category_path='Home > Tissues',website_category_source_url='https://www.naheed.pk/item',website_category_status='verified_product_breadcrumb',**{'base_price (PKR)':200})
   s.append(list(row));s.append(list(row.values()));b.save(p);b.close();path,count=repair(p,out,'ChotuApp Groceries');self.assertEqual(count,1)
   b=load_workbook(path);s=b['Products'];r=dict(zip([c.value for c in s[1]],[c.value for c in s[2]]));b.close();self.assertEqual(r['Category'],'Tissues');self.assertEqual(r['subcategory_source'],'owner_brand_search');self.assertEqual(r['base_price (PKR)'],200);self.assertEqual(r['source_scope_review_count'],34)
   again,changes=repair(path,Path(tmp)/'again.xlsx','ChotuApp Groceries');self.assertEqual(changes,0);self.assertEqual(again,path)
 def test_existing_brand_marker_repairs_category_only_with_retained_breadcrumb(self):
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp)/'source.xlsx';out=Path(tmp)/'fixed.xlsx'
   row=dict(Category='Wrong label',owner_scope_url='https://www.naheed.pk/catalogsearch/result/?q=Rose+Petal',source_url='https://www.naheed.pk/item',source_manufacturer='Rose Petal',subcategory_source='owner_brand_search',subcategory_evidence='retained receipt',source_scope_coverage_status='review_required',source_scope_review_count=34,website_category_path='Home > Tissues',website_category_source_url='https://www.naheed.pk/item',website_category_status='verified_product_breadcrumb')
   for url in (row['source_url'],'https://www.naheed.pk/another-item'):
    row['website_category_source_url']=url
    book=Workbook();sheet=book.active;sheet.title='Products';sheet.append(list(row));sheet.append(list(row.values()));book.save(p);book.close()
    if url!=row['source_url']:
     with self.assertRaises(ValueError):repair(p,out,'ChotuApp Groceries')
    else:
     path,count=repair(p,out,'ChotuApp Groceries');self.assertEqual(count,1)
     book=load_workbook(path);sheet=book['Products'];fixed=dict(zip([c.value for c in sheet[1]],[c.value for c in sheet[2]]));book.close()
     self.assertEqual(fixed['Category'],'Tissues');self.assertEqual(fixed['source_scope_review_count'],34)
 def test_unknown_scope_does_not_bypass_inference(self):
  with self.assertRaises(ValueError):apply(dict(name='Serum',source_url='https://other.example/item',owner_scope_url=SCOPE,subcategory_source='owner_supplied_scope'))

class GroceryTraversalScopeTests(unittest.TestCase):
 def test_scope_change_remains_reviewable_and_foreign_navigation_stays_rejected(self):
  from urllib.parse import urlsplit
  from grocery_browser_support import ListingRenderIncomplete,verify_traversed_listing
  expected=urlsplit('https://www.naheed.pk/catalogsearch/result/?q=Nestle')
  verify_traversed_listing(urlsplit(expected.geturl()+'&p=2'),expected)
  with self.assertRaises(ListingRenderIncomplete):
   verify_traversed_listing(urlsplit('https://www.naheed.pk/catalogsearch/result/?q=Other'),expected)
  with self.assertRaises(ValueError):
   verify_traversed_listing(urlsplit('https://another.example/catalogsearch/result/?q=Nestle'),expected)
