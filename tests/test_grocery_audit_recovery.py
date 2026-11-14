import copy,hashlib,json,tempfile,unittest
from pathlib import Path
from openpyxl import Workbook,load_workbook
from recover_grocery_audit import validate_recovery,ALLOWED_AUDIT_ISSUE
from naheed_brand_support import load_request

class GroceryAuditRecoveryTests(unittest.TestCase):
 def test_only_hash_bound_category_findings_and_complete_scope_proof_can_be_reused(self):
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp)/'preview.xlsx';p.write_bytes(b'immutable saved preview')
   report=dict(status='hold',findings_count=1,findings=[dict(issues=[ALLOWED_AUDIT_ISSUE])],workbook_sha256=hashlib.sha256(p.read_bytes()).hexdigest())
   proof=dict(coverage={s['url']:dict(complete=True,visible=1,total=1) for s in load_request()['brands']})
   validate_recovery(report,proof,p)
   bad=copy.deepcopy(report);bad['findings'][0]['issues']=['Price/stock gate: conflicting sale-price columns']
   with self.assertRaises(ValueError):validate_recovery(bad,proof,p)
   bad=copy.deepcopy(proof);next(iter(bad['coverage'].values()))['complete']=False
   with self.assertRaises(ValueError):validate_recovery(report,bad,p)
   p.write_bytes(b'changed')
   with self.assertRaises(ValueError):validate_recovery(report,proof,p)
 def test_source_brand_category_is_not_overwritten_by_gender_inference(self):
  from rule804_pipeline import process
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);source=root/'source.xlsx';output=root/'out.xlsx';b=Workbook();s=b.active;s.title='Products'
   row=dict(shop_code='SE10085',product_id='p',Category='Fragrances',name='Dolce & Gabbana Eau De Parfum For Men 100ml',description='An eau de parfum for men in a 100ml bottle.',source_url='https://www.naheed.pk/item',source_manufacturer='Dolce & Gabbana',owner_scope_url='https://www.naheed.pk/catalogsearch/result/?q=Dolce+%26+Gabbana',subcategory_source='owner_brand_search',subcategory_evidence='Actual verified product breadcrumb',subcategory_checked_at='2026-11-14T00:00:00Z',website_category_path='Health & Beauty > Fragrances',website_category_source_url='https://www.naheed.pk/item',website_category_status='verified_product_breadcrumb',website_category_checked_at='2026-11-14T00:00:00Z',source_scope_coverage_status='complete',source_scope_review_count=0,**{'base_price (PKR)':1000})
   s.append(list(row));s.append(list(row.values()))
   for name in ('Product Images','Option Groups','Options','Variant Combinations'):b.create_sheet(name).append(['product_id'])
   b.save(source);b.close();process(source,output,'ChotuApp Groceries',{'ChotuApp Groceries':'SE10085'})
   b=load_workbook(output);s=b['Products'];r=dict(zip([c.value for c in s[1]],[c.value for c in s[2]]));b.close();self.assertEqual(r['Category'],'Fragrances');self.assertEqual(r['subcategory_source'],'owner_brand_search');self.assertEqual(r['base_price (PKR)'],1000)
