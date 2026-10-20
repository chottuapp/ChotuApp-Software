import base64,json,shutil,tempfile,unittest
from pathlib import Path
from unittest.mock import Mock
from openpyxl import load_workbook
from test_mobile_khaadi import MobileTests,ROOT
import original_store_ingest as ingest
from rule804_pipeline import process
class OriginalTests(unittest.TestCase):
 def setup_root(self,root):
  for name in ('cloud/rule804_pipeline.py','subcategory_inference_support.py','catalog-tools/complete_rule804_batch.py','cloud/confirmed-shop-codes.json','cloud/original_store_ingest.py','laam_source_support.py'):
   dest=root/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/name,dest)
 def exercise(self,*,status='done',fail_check=False,store='Sapphire',scope_valid=True):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);self.setup_root(root);source=MobileTests().workbook(root,url='https://pk.sapphireonline.pk/products/P1.html' if store=='Sapphire' else 'https://laam.com/products/P1')
   runs=[{'databaseId':12,'displayTitle':'Cloud group solo-'+store.lower(),'status':'completed','headSha':'approved'}];policy=[{'store':store,'group':'solo-'+store.lower()}];calls=[]
   def gh(*args):
    if args[0]=='api' and '/artifacts?' in args[1]:return json.dumps({'artifacts':[{'id':8,'name':'chotuapp-excel-files'}]})
    if args[0]=='api' and '/contents/laam_source_support.py?' in args[1]:return json.dumps({'content':base64.b64encode((root/'laam_source_support.py').read_bytes() if scope_valid else b'old unfiltered adapter').decode()})
    if args[:2]==('run','download'):
     stage=Path(args[-1]);shutil.copy2(source,stage/(store+'.xlsx'));(stage/'run-summary.json').write_text(json.dumps({'stores':[{'name':store,'status':status}]}));return ''
    raise AssertionError(args)
   def rc(*args):
    calls.append(args[0]);book=load_workbook(Path(args[1])/(store+'.xlsx'));self.assertEqual(book['Products']['K2'].value,'=100+50');self.assertTrue(book['Products']['C2'].value);book.close()
    if args[0]=='check' and fail_check:raise RuntimeError('check failed')
   state={'uploaded':{'Other':{'sha256':'untouched'}}};sent=ingest.upload(state,'target',rc,runs,gh,policy,root=root)
   self.assertEqual(state['uploaded'],{'Other':{'sha256':'untouched'}})
   if status!='done' or not scope_valid:
    self.assertFalse(sent);self.assertFalse(calls)
   elif fail_check:
    self.assertFalse(sent);self.assertNotIn(store,state.get('original_uploads',{}));self.assertIn(store,state['original_holds'])
   else:
    self.assertEqual(sent,[store]);self.assertEqual(calls,['copy','check']);self.assertIn('verified_utc',state['original_uploads'][store])
    self.assertEqual(ingest.upload(state,'target',Mock(side_effect=AssertionError),runs,gh,policy,root=root),[])
 def test_sapphire_804_then_checked_copy(self):self.exercise()
 def test_incomplete_never_uploaded(self):self.exercise(status='running')
 def test_failed_check_not_recorded_verified(self):self.exercise(fail_check=True)
 def test_laam_requires_matching_clothing_source(self):self.exercise(store='LAAM',scope_valid=False)
 def test_matching_laam_revision_can_upload(self):self.exercise(store='LAAM')
 def test_foreign_source_and_unapproved_store_refused(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);source=MobileTests().workbook(root,url='https://us.sapphireonline.pk/products/P1.html')
   with self.assertRaises(ValueError):process(source,root/'out.xlsx','Sapphire',{},approved_original=True)
   with self.assertRaises(ValueError):process(source,root/'out.xlsx','Other',{},approved_original=True)
 def test_newest_candidate_first(self):
  runs=[{'databaseId':2,'displayTitle':'Automatic continuation of 1','status':'completed'},{'databaseId':1,'displayTitle':'Cloud group solo-sapphire','status':'completed'}]
  result=ingest.candidates(runs,[{'store':'Sapphire','group':'solo-sapphire'}],Mock(side_effect=AssertionError));self.assertEqual([r[1]['databaseId'] for r in result],[2,1])
