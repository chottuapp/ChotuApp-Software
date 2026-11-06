import copy,json,tempfile,unittest
from pathlib import Path
from openpyxl import Workbook,load_workbook
from incomplete_products import exclude
from locked_store_rules import incomplete_product_reasons

class IncompleteProductsTests(unittest.TestCase):
 def test_durable_receipt_keeps_all_products_and_literal_cells(self):
  from incomplete_products import save_receipt
  with tempfile.TemporaryDirectory() as tmp:
   entries=[dict(product_id=str(i),name='=1+1',source_url='https://shop.test/'+str(i),issues=['Missing description']) for i in range(120)]
   def save(path,store,campaign,run):
    book=load_workbook(path);sheet=book.active
    self.assertEqual(sheet.max_row,121);self.assertEqual(sheet['B2'].value,'=1+1');self.assertEqual(sheet['B2'].data_type,'s');self.assertEqual(sheet['E121'].value,'source-sha');book.close()
    return 'durable-manifest'
   self.assertEqual(save_receipt(entries,'Store','campaign','run','source-sha',tmp,save),'durable-manifest')
 def workbook(self,path):
  b=Workbook();p=b.active;p.title='Products'
  p.append(['product_id','name','source_url','description','scraped_image_url (cover, auto)','option_groups','base_price (PKR)'])
  p.append(['bad','Unknown bundle','https://shop.test/bad','Unknown bundle','https://shop.test/bad.jpg','shared,exclusive',123])
  p.append(['good','Named tool','https://shop.test/good','A named tool with exact source details.','https://shop.test/good.jpg','shared',456.75])
  for name,headers,rows in [('Product Images',['product_id','scraped_image_url (auto)'],[['bad','https://shop.test/bad.jpg'],['good','https://shop.test/good.jpg']]),('Variant Combinations',['product_id','option_1_group_id','base_price (PKR)'],[['bad','exclusive',123],['good','shared',456.75]]),('Option Groups',['group_id'],[['shared'],['exclusive']]),('Options',['group_id','option_name'],[['shared','One'],['exclusive','Two']])]:
   w=b.create_sheet(name);w.append(headers)
   for row in rows:w.append(row)
  b.save(path);b.close()
 def test_quarantine_preserves_original_and_removes_only_linked_rows(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);source=root/'source.xlsx';output=root/'output.xlsx';self.workbook(source);output.write_bytes(source.read_bytes());before=source.read_bytes()
   finding=dict(product_id='bad',name='Unknown bundle',source_url='https://shop.test/bad',issues=['Description lacks enough product-specific content for review'])
   a,b,receipt=exclude(source,output,'House of Tools',{'findings':[finding]},root/'filtered')
   self.assertEqual(source.read_bytes(),before);self.assertEqual(len(receipt),1)
   for file in (a,b):
    book=load_workbook(file);rows=lambda name:[r for r in book[name].iter_rows(min_row=2,values_only=True) if any(v is not None for v in r)]
    self.assertEqual([r[0] for r in rows('Products')],['good']);self.assertEqual(rows('Products')[0][-1],456.75)
    self.assertEqual([r[0] for r in rows('Variant Combinations')],['good'])
    self.assertEqual([r[0] for r in rows('Product Images')],['good'])
    self.assertEqual(rows('Option Groups'),[('shared',)]);self.assertEqual(rows('Options'),[('shared','One')]);book.close()
 def test_commercial_and_identity_failures_cannot_be_hidden_as_incomplete(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);source=root/'s.xlsx';self.workbook(source)
   finding=dict(product_id='bad',name='Unknown bundle',source_url='https://shop.test/bad',issues=['Category blank or unresolved','Source price mismatch'])
   a,b,receipt=exclude(source,source,'House of Tools',{'findings':[finding]},root/'filtered');self.assertEqual(receipt,[])
   finding['issues']=['Category blank or unresolved'];finding['source_url']='https://wrong.test/bad'
   with self.assertRaisesRegex(ValueError,'identity mismatch'):exclude(source,source,'House of Tools',{'findings':[finding]},root/'filtered')
 def test_preflight_skips_empty_placeholder_and_identity_only_before_refresh(self):
  for body in ('','<p>Code 123</p>','<p>Description coming soon.</p>'):
   product=dict(title='Exact product',body_html=body);before=copy.deepcopy(product)
   self.assertTrue(incomplete_product_reasons(product));self.assertEqual(product,before)
  self.assertEqual(incomplete_product_reasons(dict(title='Exact product',body_html='<p>Exact cotton shirt with button closure.</p>')),[])

 def test_targeted_recovery_rejects_unapproved_store(self):
  from audit804_delivery import run_campaign
  with self.assertRaisesRegex(ValueError,'outside approved'):
   run_campaign({},dict(dispatcher='campaign',stores=['Bata']),[],lambda *a:'',lambda *a:'',held_stores=['Other'])

 def test_fresh_skip_receipt_retains_exact_source_outside_temporary_export(self):
  import csv
  from locked_store_rules import record_incomplete_product
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);product=dict(id=1,title='Incomplete',handle='one',body_html='',variants=[dict(price='456.75',available=True)])
   target=record_incomplete_product(product,'https://shop.test','Store',root/'main.py',['Missing description'])
   self.assertEqual(target.parent,root/'audit_reports'/'Store')
   with target.open(encoding='utf-8-sig') as stream:row=next(csv.DictReader(stream))
   self.assertEqual(json.loads(row['original_source_product_json']),product)

 def test_a_second_capacity_finding_cannot_hide_a_price_conflict(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);source=root/'s.xlsx';self.workbook(source)
   finding=dict(product_id='bad',name='Unknown bundle',source_url='https://shop.test/bad',issues=['Source price mismatch'])
   report={'findings':[finding,dict(finding,issues=['Description exceeds Excel cell capacity'])]}
   self.assertEqual(exclude(source,source,'House of Tools',report,root/'filtered')[2],[])
