import tempfile,unittest
from pathlib import Path
from openpyxl import Workbook,load_workbook
from complete_grocery_export import merge
class GroceryCompletionTests(unittest.TestCase):
 def test_incomplete_scope_keeps_source_proof_without_a_completion_manifest(self):
  import json
  from complete_grocery_export import require_scope_complete
  with tempfile.TemporaryDirectory() as tmp:
   out=Path(tmp);scope={'label':'Dawn Bread','url':'https://www.naheed.pk/allproducts/?manufacturer=890'}
   with self.assertRaisesRegex(ValueError,'visible=1; total=2'):
    require_scope_complete(out,scope,8,{'https://www.naheed.pk/item'},2,{scope['url']},False,[])
   proof=json.loads((out/'grocery-coverage-hold.json').read_text())
   self.assertEqual(proof['unresolved_scope']['links'],['https://www.naheed.pk/item'])
   self.assertEqual(proof['status'],'held_source_coverage');self.assertFalse((out/'completion-manifest.json').exists())
   with self.assertRaisesRegex(ValueError,'count_changed=True'):
    require_scope_complete(out,scope,8,{'https://www.naheed.pk/item'},1,{scope['url']},True,[])
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
 def test_completed_checkpoint_without_cache_requires_fresh_scope_verification(self):
  import zipfile
  from complete_grocery_export import discovery_snapshots,pending_scope_indexes
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);archive=root/'checkpoint.zip'
   with zipfile.ZipFile(archive,'w') as z:z.writestr('template.xlsx',b'placeholder')
   scopes=[{'url':'https://www.naheed.pk/scope1'},{'url':'https://www.naheed.pk/scope2'}]
   snapshots=discovery_snapshots(archive,root,{p['url'] for p in scopes})
   self.assertEqual(snapshots,{})
   self.assertEqual(pending_scope_indexes(scopes,snapshots,1),{1,2})
 def test_multiple_store_caches_only_use_exact_approved_scope(self):
  import zipfile,json,requests
  from resume_support import ResponseCache
  from complete_grocery_export import discovery_snapshots
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);scope='https://www.naheed.pk/scope1';cache=ResponseCache(root/'pages.sqlite3')
   response=requests.Response();response.status_code=200;response.url=scope;response._content=json.dumps({'scope_url':scope,'links':['p1'],'pages':['page1'],'total':1,'count_changed':False}).encode();cache.put(scope+'#chotu-scope-snapshot-v1',response);cache.close()
   archive=root/'checkpoint.zip'
   with zipfile.ZipFile(archive,'w') as z:
    z.write(root/'pages.sqlite3','saved_runs/a/0/pages.sqlite3');z.write(root/'pages.sqlite3','saved_runs/a/1/pages.sqlite3')
   self.assertEqual(set(discovery_snapshots(archive,root,{scope})),{scope})
   self.assertEqual(discovery_snapshots(archive,root,{'https://www.naheed.pk/other'}),{})
