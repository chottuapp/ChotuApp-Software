import json,unittest
from github_json import read_json
class LargeReportTests(unittest.TestCase):
 def test_large_raw_report_retains_existing_receipts(self):
  state=dict(uploaded={'Store':{'sha256':'verified'}},audit804_results={'padding':'x'*(1024*1024+1)})
  def gh(*args):
   self.assertEqual(args[-1],'Accept: application/vnd.github.raw+json');return json.dumps(state)
  self.assertEqual(read_json(gh,'repos/owner/repo/contents/latest.json?ref=reports'),state)
 def test_metadata_empty_content_never_resets_report(self):
  with self.assertRaises(ValueError):read_json(lambda *a:json.dumps(dict(encoding='none',content='')),'path')
 def test_invalid_or_missing_raw_report_is_not_empty_success(self):
  for payload in ['', '[]', 'not-json']:
   with self.subTest(payload=payload),self.assertRaises(ValueError):read_json(lambda *a:payload,'path')
  def denied(*args):raise RuntimeError('HTTP 403')
  with self.assertRaises(RuntimeError):read_json(denied,'path')
