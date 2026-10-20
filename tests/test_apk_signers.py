import importlib.util,struct,hashlib,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];spec=importlib.util.spec_from_file_location('apk_signers',ROOT/'android/tools/apk_signers.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
def lp(value,width=4):return len(value).to_bytes(width,'little')+value
class ApkSignerTests(unittest.TestCase):
 def test_v2_cert_fingerprint_does_not_depend_on_sdk_output_labels(self):
  cert=b'certificate bytes';signed=lp(b'digests')+lp(lp(cert));signers=lp(lp(signed));pair=lp((0x7109871a).to_bytes(4,'little')+lp(signers),8);size=len(pair)+24;block=size.to_bytes(8,'little')+pair+size.to_bytes(8,'little')+b'APK Sig Block 42';prefix=b'local header';central=len(prefix+block);end=b'PK\x05\x06'+b'\0'*12+central.to_bytes(4,'little')+b'\0\0'
  with tempfile.TemporaryDirectory() as tmp:
   file=Path(tmp)/'test.apk';file.write_bytes(prefix+block+end);self.assertEqual(module.fingerprints(file),[hashlib.sha256(cert).hexdigest()])
   file.write_bytes(prefix+block+end[:-1])
   with self.assertRaises(ValueError):module.fingerprints(file)
 def test_invalid_length_is_rejected(self):
  with self.assertRaises(ValueError):module.lp(b'\xff\xff\xff\xff')
