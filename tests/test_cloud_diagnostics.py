import json,os,subprocess,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'cloud'))
from diagnostics import Collector,build_report,redact,issue_codes
from publish_report import publish,validate_report


class DiagnosticTests(unittest.TestCase):
    def setUp(self):self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
    def tearDown(self):self.temp.cleanup()
    def report(self):
        return {'schema_version':1,'run_id':'12345','attempt':'1','stores':[{'name':'Store','status':'done','products':10,'variants':20,'http_statuses':{'200':4},'issue_codes':[]}]}
    def test_bounded_telemetry_captures_http_and_cache_without_urls(self):
        collector=Collector(self.root/'telemetry.json')
        collector.observe('[Store] HTTP END status=200 elapsed=1.2s bytes=200 https://secret.example/path?token=private')
        collector.observe('[Store] CACHE HIT: https://example.com/products.json?limit=250')
        collector.observe('[Store] HTTP END status=403 elapsed=0.3s bytes=10 https://example.com')
        collector.flush();data=json.loads((self.root/'telemetry.json').read_text());item=data['stores']['Store']
        self.assertEqual(item['http_statuses'],{'200':1,'403':1});self.assertEqual(item['cache_events'],1);self.assertEqual(item['network_seconds'],1.5)
        self.assertIn('HTTP_403',item['issues']);self.assertNotIn('secret.example',json.dumps(data));self.assertNotIn('private',json.dumps(data))
    def test_zero_mismatch_note_is_not_a_data_failure(self):
        self.assertNotIn('DATA_MISMATCH',issue_codes('PRICE AUDIT: 138 products; 0 review/mismatch rows'))
        self.assertIn('DATA_MISMATCH',issue_codes('FAILED: Price mismatch'))
        self.assertNotIn('DATA_MISMATCH',issue_codes('PRICE AUDIT: 3894 products; 9 review/mismatch rows; REVIEW=9, MISMATCH=0'))
        self.assertIn('AUDIT_REVIEW',issue_codes('PRICE AUDIT: 9 review/mismatch rows'))
        self.assertIn('DATA_MISMATCH',issue_codes('PRICE AUDIT: 2 review/mismatch rows; REVIEW=0, MISMATCH=2'))
    def test_public_report_allowlist_omits_details_credentials_and_full_logs(self):
        output=self.root/'ANAS_DATA_FETCH';output.mkdir()
        (output/'run-summary.json').write_text(json.dumps({'status':'incomplete','checkpoint':'saved','stores':[{'name':'Seran','status':'blocked','detail':'SOURCE BLOCKED: HTTP 403; password=very-private-secret','secret':'never-copy','software_revision':'a'*16}]}))
        (self.root/'fetch.log').write_text('Authorization: Bearer secret\nHTTP https://user:pass@store.example/products?token=secret\n')
        with patch.dict(os.environ,{'GITHUB_RUN_ID':'12345','GITHUB_RUN_ATTEMPT':'1','GITHUB_SHA':'a'*40}):report=build_report(self.root,self.root/'diagnostics')
        serialized=json.dumps(report);self.assertNotIn('very-private-secret',serialized);self.assertNotIn('detail',serialized);self.assertIn('HTTP_403',report['stores'][0]['issue_codes'])
        log=(self.root/'diagnostics'/'redacted-log.txt').read_text();self.assertNotIn('Bearer secret',log);self.assertNotIn('user:pass',log);self.assertNotIn('token=secret',log)
    def test_report_exists_when_fetch_never_created_state(self):
        report=build_report(self.root,self.root/'output');self.assertEqual(report['status'],'no_saved_state');self.assertEqual(report['stores'],[])
    def test_publication_rejects_unapproved_fields(self):
        data=self.report();data['password']='secret'
        with self.assertRaises(ValueError):validate_report(data)
        data=self.report();data['stores'][0]['detail']='private'
        with self.assertRaises(ValueError):validate_report(data)
    def test_publication_creates_and_appends_report_branch_without_changing_main(self):
        bare=self.root/'origin.git';repo=self.root/'work';subprocess.run(['git','init','--bare',str(bare)],check=True,capture_output=True)
        repo.mkdir()
        def git(*args):return subprocess.check_output(['git','-C',str(repo),*args],stderr=subprocess.DEVNULL).decode().strip()
        git('init','-b','main');git('config','user.name','Fixture');git('config','user.email','fixture@example.com');git('remote','add','origin',str(bare))
        (repo/'main.py').write_text('original software\n');git('add','main.py');git('commit','-m','Original app');git('push','origin','main');before=git('rev-parse','HEAD')
        path=self.root/'report.json';data=self.report();path.write_text(json.dumps(data));publish(path,repo)
        data['run_id']='12346';path.write_text(json.dumps(data));publish(path,repo)
        self.assertEqual(git('rev-parse','HEAD'),before);self.assertEqual(git('branch','--show-current'),'main');self.assertEqual(git('status','--porcelain'),'')
        self.assertEqual((repo/'main.py').read_text(),'original software\n')
        git('fetch','origin','cloud-reports');files=git('ls-tree','-r','--name-only','FETCH_HEAD').splitlines()
        self.assertEqual(files,['README.md','latest.json','runs/12345-1.json','runs/12346-1.json'])
        latest=json.loads(git('show','FETCH_HEAD:latest.json'));self.assertEqual(latest['run_id'],'12346')
    def test_redaction_removes_known_token_shapes_and_sensitive_headers(self):
        self.assertNotIn('gho_abcdefghijk',redact('token gho_abcdefghijk'))
        self.assertEqual(redact('Cookie: session=secret'),'[credential-bearing log line removed]')

if __name__=='__main__':unittest.main()
