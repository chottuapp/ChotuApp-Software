import unittest,sys
from pathlib import Path
sys.path[:0]=[str(Path(__file__).resolve().parents[1]/'cloud'),str(Path(__file__).resolve().parents[1])]
from drive_catalog import enrich
class CatalogTests(unittest.TestCase):
 def test_links_and_historical_verified_time_not_modtime(self):
  state={'folder':'F','uploaded':{'A':{'sha256':'abc','folder':'F'}}}
  enrich(state,[{'Name':'F','ID':'folder-id','IsDir':True}],[{'Name':'A.xlsx','ID':'file-id','ModTime':'source-mtime'}],[{'verified_utc':'2026-10-20T12:30:00+00:00','uploaded':{'A':{'sha256':'abc','folder':'F'}}},{'verified_utc':'2026-10-21T12:30:00+00:00','uploaded':{'A':{'sha256':'abc','folder':'F'}}}])
  row=state['uploaded']['A'];self.assertTrue(row['file_url'].endswith('/file-id/view'));self.assertEqual(row['verified_utc'],'2026-10-20T12:30:00+00:00')
 def test_wrong_hash_does_not_invent_upload_time(self):
  state={'folder':'F','uploaded':{'A':{'sha256':'new','folder':'F'}}}
  enrich(state,[{'Name':'F','ID':'folder-id','IsDir':True}],[],[{'verified_utc':'2026-10-20T12:30:00+00:00','uploaded':{'A':{'sha256':'old','folder':'F'}}}])
  self.assertNotIn('verified_utc',state['uploaded']['A']);self.assertNotIn('file_url',state['uploaded']['A'])
 def test_ambiguous_folder_refused(self):
  with self.assertRaises(ValueError):enrich({'folder':'F'},[{'Name':'F','ID':'x','IsDir':True}]*2,[],[])
