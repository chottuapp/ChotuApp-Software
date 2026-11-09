import copy,json,shutil,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from openpyxl import Workbook,load_workbook
from audit804 import issues_for
from hold804_repairs import category
from reviewed804_repairs import roots,conflicting_name,description
from audit804_delivery import DriveIdentity
import test_incomplete_products as incomplete_fixtures
from incomplete_products import exclude

class StalledAuditTests(unittest.TestCase):
 def test_explicit_objects_do_not_become_claims_or_usage_tools(self):
  examples=[('Miss Rose','Oil Control Compact Powder','Compact powder sets makeup and controls shine on skin.','Face Powders'),('Rivaj UK','Fantasy 3 In 1 Palette','Palette contains contour, blush and highlighter. Spray brush with makeup fixer for lasting wear.','Face Palettes'),('Computer Zone','HP ZBOOK Firefly 14 G8','Intel Core processor, 16GB RAM, FHD display.','Laptops'),('Shop Modest','Girls Embroidered Outfit','Top: Chiffon embroidered shirt.\n• Bottom: Dhaka pajama trouser.\n• Dupatta: Net dupatta.','Clothing Sets'),('ChenOne','Women Jogging Suit','Full sleeves with front zip. Fitted trouser with elasticated belt.','Tracksuits')]
  for store,name,body,label in examples:
   with self.subTest(name=name):
    row=dict(name=name,description=body,Category='Sale');self.assertEqual(category(row,store)[0],label);self.assertEqual(issues_for(dict(row,Category=label)),[])
 def test_negated_trouser_is_not_product_purpose(self):
  row=dict(name='SS24A',Category='Shirts',description='Cut: Basic.\n• Trouser: Not Included.\n• SHOULDER: 14 | 15.\n• SLEEVE LENGTH: 18 | 19.\n• Fabric: Lawn.')
  self.assertEqual(category(row,'Sana Safinaz')[0],'Shirts');self.assertFalse(issues_for(row))
  self.assertTrue(issues_for(dict(row,Category='Trousers')))
 def test_own_hyphenated_name_is_not_a_different_product(self):
  row=dict(name='AVELIA- 3pc',description='Avelia is a powder-blue 3-piece stitched ensemble.')
  self.assertIsNone(conflicting_name(row,roots([row])))
  other=dict(name='Azura');row['description']='Azura is a black 3-piece stitched outfit.'
  self.assertEqual(conflicting_name(row,roots([row,other])),'Azura')
 def test_dotted_copied_prose_repair_keeps_all_detail_numbers(self):
  row=dict(name='Leonie - 3 pc',description='OUTFIT DESCRIPTION.\nAzura is a 3-piece stitched outfit.\nPRODUCT DETAIL.\nRTW - 3 PC.\nShirt: Raw Silk.\nTrouser: Raw Silk.\nDupatta: 4-side Organza.')
  fixed,reason=description(row,'Seran',{'leonie','azura'})
  self.assertTrue(reason);self.assertNotIn('Azura',fixed);self.assertIn('4-side Organza',fixed)
 def test_incomplete_quarantine_does_not_reapply_new_category_exclusions(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);source=root/'source.xlsx';output=root/'output.xlsx';incomplete_fixtures.IncompleteProductsTests().workbook(source)
   shutil.copy2(source,output)
   # Initial owner filtering is upstream; an audit quarantine must remove exactly
   # the requested identity, not independently remove other rows from just one side.
   from owner_product_exclusions import apply
   finding=dict(product_id='bad',name='Unknown bundle',source_url='https://shop.test/bad',issues=['Description lacks enough product-specific content for review'])
   with patch('locked_store_rules.freshbasket_produce',side_effect=AssertionError('owner policy already applied upstream')):
    a,b,receipt=exclude(source,output,'Fresh Basket',{'findings':[finding]},root/'filtered')
   self.assertEqual(len(receipt),1)
   for path in (a,b):
    w=load_workbook(path);self.assertEqual([r[0] for r in w['Products'].iter_rows(min_row=2,values_only=True) if r[0]],['good']);w.close()

class DuplicateArchiveTests(unittest.TestCase):
 def exercise(self,fail=False,wrong=False):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp)
   def book(name,code,host,desc):
    p=root/name;w=Workbook();s=w.active;s.title='Products';s.append(['shop_code','source_url','description']);s.append([code,'https://'+host+'/products/x',desc]);w.save(p);return p
   a=book('a.xlsx','S1','store.test','old a');b=book('b.xlsx','OTHER' if wrong else 'S1','store.test','old b');incoming=book('new.xlsx','S1','store.test','new')
   remote='chotudrive:F';objects={'a':dict(path=remote+'/Store.xlsx',data=a.read_bytes()),'b':dict(path=remote+'/Store.xlsx',data=b.read_bytes())};staged={};calls=[]
   def data(path):
    if path in staged:return staged[path]
    matches=[o['data'] for o in objects.values() if o['path']==path]
    if len(matches)!=1:raise ValueError('ambiguous test path')
    return matches[0]
   def rc(*args):
    calls.append(args);op=args[0]
    if op=='lsjson':return json.dumps([{'Name':'Store.xlsx','ID':id} for id,o in objects.items() if o['path']==remote+'/Store.xlsx'])
    if args[:2]==('backend','copyid'):Path(args[4]).write_bytes(objects[args[3]]['data'])
    if args[:2]==('backend','moveid'):objects[args[3]]['path']=args[4]
    if op=='copy':
     name=args[args.index('--include')+1];staged[args[2]+'/'+name]=(Path(args[1])/name).read_bytes()
    if op=='check':
     if fail and args[2]==remote:raise RuntimeError('final verification failed')
     name=args[args.index('--include')+1]
     self.assertEqual((Path(args[1])/name).read_bytes(),data(args[2]+'/'+name))
    if op=='copyto':objects['new']=dict(path=args[2],data=data(args[1]))
    if op=='deletefile':staged.pop(args[1],None)
    return ''
   with DriveIdentity(rc,'F') as identity:
    if fail or wrong:
     with self.assertRaises((ValueError,RuntimeError)):identity.replace(incoming,'S1','Store.xlsx')
    else:
     receipt=identity.replace(incoming,'S1','Store.xlsx');self.assertEqual(receipt['duplicate_copies_preserved'],2)
     self.assertEqual(data(remote+'/Store.xlsx'),incoming.read_bytes())
   self.assertEqual(objects['a']['data'],a.read_bytes());self.assertEqual(objects['b']['data'],b.read_bytes())
   for id in ('a','b'):
    self.assertEqual(objects[id]['path'],remote+'/Store.xlsx' if fail or wrong else remote+'/_duplicate_backups/'+id+'/Store.xlsx')
   self.assertFalse(any(c[0]=='deletefile' and '_incoming/' not in c[1] for c in calls))
   if wrong:self.assertFalse(any(c[:2]==('backend','moveid') for c in calls))
 def test_every_duplicate_preserved_before_verified_promotion(self):self.exercise()
 def test_final_failure_restores_original_ids_and_bytes(self):self.exercise(fail=True)
 def test_conflicting_duplicate_codes_are_never_moved(self):self.exercise(wrong=True)
