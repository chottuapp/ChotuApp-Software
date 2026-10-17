import tempfile,unittest
from pathlib import Path
from unittest.mock import Mock,patch
from cloud_live_windows import refresh_helper
class LauncherTests(unittest.TestCase):
 def test_identical_helper_does_not_restart_and_valid_change_replaces(self):
  with tempfile.TemporaryDirectory() as tmp:
   target=Path(tmp)/'helper.py';target.write_bytes(b'print(1)\n');run=Mock(stdout='a'*40)
   response=Mock();response.read.return_value=b'print(1)\n';ctx=Mock();ctx.__enter__=Mock(return_value=response);ctx.__exit__=Mock(return_value=False)
   with patch('cloud_live_windows.subprocess.run',return_value=run),patch('cloud_live_windows.urllib.request.urlopen',return_value=ctx):
    self.assertEqual(refresh_helper('gh','owner/repo',target),('a'*40,False))
    response.read.return_value=b'print(2)\n';self.assertEqual(refresh_helper('gh','owner/repo',target),('a'*40,True));self.assertEqual(target.read_bytes(),b'print(2)\n')
 def test_invalid_download_preserves_installed_helper(self):
  with tempfile.TemporaryDirectory() as tmp:
   target=Path(tmp)/'helper.py';target.write_bytes(b'print(1)\n');response=Mock();response.read.return_value=b'bad python !';ctx=Mock();ctx.__enter__=Mock(return_value=response);ctx.__exit__=Mock(return_value=False)
   with patch('cloud_live_windows.subprocess.run',return_value=Mock(stdout='a'*40)),patch('cloud_live_windows.urllib.request.urlopen',return_value=ctx):
    with self.assertRaises(SyntaxError):refresh_helper('gh','owner/repo',target)
   self.assertEqual(target.read_bytes(),b'print(1)\n')
if __name__=='__main__':unittest.main()
