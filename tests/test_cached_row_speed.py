"""A preloaded page must not consume a website pacing slot during row building."""
import tempfile,time,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock,patch
import requests
import main
from resume_support import ResponseCache

class CachedRowSpeedTests(unittest.TestCase):
 def page(self,url):
  r=requests.Response();r.status_code=200;r.url=url;r.encoding='utf-8';r._content=b'<html><meta property="og:image" content="https://cdn.example/p.jpg"><h1>Product</h1></html>';return r
 def test_valid_saved_page_skips_network_delay_and_preserves_verification(self):
  with tempfile.TemporaryDirectory() as tmp:
   cache=ResponseCache(Path(tmp)/'pages.sqlite3');url='https://shop.example/products/p';cache.put(url,self.page(url))
   tls=SimpleNamespace(saved_response_cache=cache,adaptive_last_request=12345,adaptive_pace=1.5,image_audit=[]);p={'handle':'p'}
   with patch.object(main,'_chotu_tls',tls),patch.object(main,'_chotu_wait') as wait,patch.object(main,'_chotu_backoff') as backoff,patch.object(main,'_chotu_debug_response'),patch.object(main,'S') as session:
    cover=main.storefront_cover('https://shop.example',p,[{'src':'https://cdn.example/p.jpg'}],lambda _:None)
   self.assertEqual(cover,'https://cdn.example/p.jpg');self.assertEqual(tls.image_audit[0][1],'VERIFIED');self.assertEqual(tls.adaptive_last_request,12345);backoff.assert_not_called();session.get.assert_not_called();wait.assert_called_once();cache.close()
 def test_cache_miss_retains_network_pacing(self):
  tls=SimpleNamespace(saved_response_cache=Mock(get=Mock(return_value=None)),adaptive_last_request=time.monotonic(),adaptive_pace=1.5,image_audit=[])
  with patch.object(main,'_chotu_tls',tls),patch.object(main,'_chotu_wait'),patch.object(main,'_chotu_backoff') as backoff,patch.object(main,'S',SimpleNamespace(get=Mock(return_value=self.page('https://shop.example/products/p')))) as session:
   main.storefront_cover('https://shop.example',{'handle':'p'},[{'src':'https://cdn.example/p.jpg'}],lambda _:None)
  self.assertEqual(backoff.call_count,1);self.assertGreater(backoff.call_args.args[0],1);session.get.assert_called_once()
 def test_corrupt_checkpoint_falls_back_to_paced_network_request(self):
  with tempfile.TemporaryDirectory() as tmp:
   cache=ResponseCache(Path(tmp)/'pages.sqlite3');url='https://shop.example/products/p';cache.put(url,self.page(url));cache.db.execute('UPDATE pages SET checksum=?',('corrupt',));cache.db.commit()
   tls=SimpleNamespace(saved_response_cache=cache,image_audit=[])
   with patch.object(main,'_chotu_tls',tls),patch.object(main,'_chotu_wait'),patch.object(main,'_chotu_backoff') as backoff,patch.object(main,'S',SimpleNamespace(get=Mock(return_value=self.page(url)))) as session:
    main.storefront_cover('https://shop.example',{'handle':'p'},[{'src':'https://cdn.example/p.jpg'}],lambda _:None)
   backoff.assert_called_once();session.get.assert_called_once();cache.close()
if __name__=='__main__':unittest.main()
