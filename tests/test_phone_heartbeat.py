import unittest
from runner_status import phone_connection
class PhoneHeartbeatTests(unittest.TestCase):
 def test_old_pc_is_not_phone_confirmation(self):
  result=phone_connection([{'execution':'Windows local','worker_active':True,'status_confirmed':True}])
  self.assertFalse(result['status_confirmed']);self.assertEqual(result['status'],'not_connected_or_no_report')
 def test_stale_phone_does_not_claim_running(self):
  result=phone_connection([{'execution':'Android app','worker_active':True,'status_confirmed':False}])
  self.assertFalse(result['status_confirmed']);self.assertNotIn('worker_active',result)
 def test_recent_terminal_phone_report_is_connected_but_stopped(self):
  result=phone_connection([{'execution':'Android app','worker_active':False,'status':'stopped','status_confirmed':True}])
  self.assertTrue(result['status_confirmed']);self.assertFalse(result['worker_active']);self.assertEqual(result['worker_status'],'stopped')
