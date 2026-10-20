import unittest,tempfile,hashlib,os,json,sys
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'cloud')]
import move_reviewed_drive_batch as move
class TransferTests(unittest.TestCase):
 def exercise(self,fail=False):
  with tempfile.TemporaryDirectory() as tmp:
   stage=Path(tmp);calls=[]
   state={'uploaded':{},'daily_uploads':{move.SOURCE:{'Miss Rose':{'sha256':hashlib.sha256(b'reviewed').hexdigest(),'rule804':'applied'}}}}
   def rc(*args):
    calls.append(args)
    if args[0]=='copy' and args[1]=='chotudrive:'+move.SOURCE:(stage/'Miss Rose.xlsx').write_bytes(b'reviewed')
    if args[0]=='lsjson':return json.dumps([{'Name':'Miss Rose.xlsx'},{'Name':'Old Other Store.xlsx'}])
    if fail and args[0]=='check':raise RuntimeError('Checksum mismatch')
    return ''
   with patch.object(move,'publish'),patch.dict(os.environ,{'GITHUB_RUN_ID':'1'}),patch('builtins.print'):
    if fail:
     with self.assertRaises(RuntimeError):move.transfer(rc,stage,state)
     self.assertFalse(any(c[0]=='deletefile' for c in calls))
    else:
     result=move.transfer(rc,stage,state)
     deletes=[c for c in calls if c[0]=='deletefile'];self.assertEqual(deletes,[('deletefile','chotudrive:'+move.SOURCE+'/Miss Rose.xlsx')])
     self.assertEqual(result['moves'][-1]['preserved_other_files'],1);self.assertEqual(result['uploaded']['Miss Rose']['folder'],move.TARGET)
     self.assertLess(next(i for i,c in enumerate(calls) if c[0]=='check'),next(i for i,c in enumerate(calls) if c[0]=='deletefile'))
 def test_replaces_matching_files_preserves_other_names(self):self.exercise()
 def test_failed_verification_never_deletes_source(self):self.exercise(True)
