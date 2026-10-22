import json,unittest
from unittest.mock import patch
from resume_failed_stores import checkpoint_parent
class SavedRecoveryTests(unittest.TestCase):
 def responder(self,checkpoints):
  def gh(*a):
   if a[:2]==('run','view'):
    rid=a[2];return json.dumps({'status':'completed','databaseId':int(rid),'displayTitle':'Automatic continuation of 100' if rid=='200' else 'Cloud group original'})
   rid=a[1].split('/runs/')[1].split('/')[0]
   return json.dumps({'artifacts':checkpoints.get(rid,[])})
  return gh
 def test_falls_back_to_last_available_saved_ancestor(self):
  with patch('resume_failed_stores.gh',side_effect=self.responder({'100':[{'name':'chotuapp-checkpoint','expired':False}]})):
   self.assertEqual(checkpoint_parent('200'),('100',['200','100']))
 def test_expired_chain_never_silently_restarts_from_zero(self):
  with patch('resume_failed_stores.gh',side_effect=self.responder({'100':[{'name':'chotuapp-checkpoint','expired':True}]})):
   with self.assertRaisesRegex(ValueError,'No available checkpoint'):checkpoint_parent('200')
 def test_active_source_cannot_spawn_competing_worker(self):
  with patch('resume_failed_stores.gh',return_value=json.dumps({'status':'in_progress'})):
   with self.assertRaisesRegex(ValueError,'still active'):checkpoint_parent('200')
