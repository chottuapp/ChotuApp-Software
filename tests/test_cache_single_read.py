import unittest,threading
from types import SimpleNamespace
from unittest.mock import Mock
from fast_fetch_support import GatedSession
class CacheReadTests(unittest.TestCase):
 def test_verified_cached_body_read_once_and_pause_preserved(self):
  response=object();cache=Mock();cache.get.return_value=response;session=Mock();gate=Mock();pause=Mock();note=Mock()
  tls=SimpleNamespace(fast_gate=gate,saved_response_cache=cache,saved_run_note=note)
  self.assertIs(GatedSession(session,tls,pause).get('https://store.example/product'),response)
  cache.get.assert_called_once();pause.assert_called_once();note.assert_called_once();session.get.assert_not_called();gate.wait.assert_not_called()
 def test_bad_or_missing_cache_still_uses_gate_and_transport(self):
  cache=Mock();cache.get.return_value=None;session=Mock();tls=SimpleNamespace(fast_gate=Mock(),saved_response_cache=cache)
  GatedSession(session,tls,lambda:None).get('https://store.example/product')
  tls.fast_gate.wait.assert_called_once();session.get.assert_called_once();tls.fast_gate.response.assert_called_once()
if __name__=='__main__':unittest.main()
