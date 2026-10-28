import unittest
from types import SimpleNamespace
from unittest.mock import Mock
from runtime import CloudService
class ShutdownTests(unittest.TestCase):
 def test_inflight_request_finishes_before_lease_release(self):
  class Inflight:
   remaining=45
   def join(self,timeout):self.remaining=max(0,self.remaining-timeout)
   def is_alive(self):return self.remaining>0
  service=CloudService.__new__(CloudService);service.thread=Inflight();service.scheduler=Mock();service.diagnostics=Mock();service.lease=Mock();service.logger=SimpleNamespace(handlers=[])
  def release():self.assertFalse(service.thread.is_alive())
  service.lease.release.side_effect=release;service.close();service.lease.release.assert_called_once();service.diagnostics.flush.assert_called_once()
