import sys,unittest,tempfile
from pathlib import Path
from types import SimpleNamespace
from bs4 import BeautifulSoup
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'cloud'))
import khaadi_source_support as source
FIX=ROOT/'tests/fixtures/khaadi_public'
URL=source.BASE+'/black-cambric-kurta/1-26-320-A-C1-VG_MULTI.html'
def fixture(n):return (FIX/(n+'.html')).read_text()
class KhaadiTests(unittest.TestCase):
 def test_captured_standalone_tailored_product_layout(self):
  html=(ROOT/'catalog-inputs/khaadi-layout/231b8aae835f433db7dbe3df4a27decb.html').read_text()
  p=source.inspect_page(html,source.BASE+'/floral-tailored-3-piece/T-CHD09B-R-VG_MULTI.html')
  self.assertEqual(p['id'],'T-CHD09B-R-VG_MULTI');self.assertEqual(p['price'],'6500.00')
  self.assertEqual([x['label'] for x in p['sizes']],['XS','S','M','XL']);self.assertEqual(len(p['images']),6)
  self.assertIsNone(p['available'])
 def test_actual_selected_ids_prices_stock_and_scope(self):
  for n,value,pid in [('xs','0XS','1001976750'),('l','00L','1001976753')]:
   p=source.inspect_page(fixture(n),URL+'?dwvar_1-26-320-A-C1-VG__MULTI_size='+value)
   self.assertEqual(p['id'],pid);self.assertEqual(p['price'],'6000.00');self.assertTrue(p['available']);self.assertEqual(p['selected']['value'],value)
   self.assertNotIn('1001976793',p['id']);self.assertEqual(len(p['images']),9)
 def test_actual_normalization_uses_exact_selected_pages(self):
  soup=BeautifulSoup(fixture('master'),'html.parser')
  for n in soup.select('.set-item')[0].select('[data-attr="size"] input'):
   if n['data-attr-value']=='00S':n.parent.decompose()
  urls=[]
  def read(url):
   urls.append(url);return SimpleNamespace(text=fixture('xs' if '=0XS' in url else 'l'))
  p=source.normalize_product(str(soup),URL,read)
  self.assertEqual([v['id'] for v in p['variants']],['1001976750','1001976753'])
  self.assertEqual([v['option1'] for v in p['variants']],['XS','L']);self.assertNotIn('inventory_quantity',p['variants'][0]);self.assertIn('100% Cotton',p['body_html'])
  self.assertTrue(all('/on/demandware.store/' not in u for u in urls))
 def test_replayed_master_wrong_size_and_wrong_currency_rejected(self):
  with self.assertRaisesRegex(ValueError,'acknowledge'):source.inspect_page(fixture('master'),URL+'?dwvar_1-26-320-A-C1-VG__MULTI_size=0XS')
  with self.assertRaisesRegex(ValueError,'acknowledge'):source.inspect_page(fixture('l'),URL+'?dwvar_1-26-320-A-C1-VG__MULTI_size=0XS')
  with self.assertRaisesRegex(ValueError,'PKR'):source.inspect_page(fixture('xs').replace('PKR','USD'),URL+'?dwvar_1-26-320-A-C1-VG__MULTI_size=0XS')
 def test_runtime_loads_khaadi_adapter(self):
  from runtime import prepare_engine
  with tempfile.TemporaryDirectory() as tmp:
   engine=prepare_engine(Path(tmp));self.assertTrue((engine.parent/'khaadi_source_support.py').exists());self.assertIn('enable_khaadi_source(globals())',engine.read_text())
 def test_foreign_hosts_and_variant_api_not_requested(self):
  reader=source.PublicCatalog({},print)
  for url in ['https://us.khaadi.com/product.html',source.BASE+'/on/demandware.store/Product-Variation']:
   with self.assertRaises(source.SourceUnavailable):reader.read(url)

 def test_mixed_sitemap_excludes_policy_and_category_pages(self):
  from unittest.mock import patch
  sitemap='<urlset>'+''.join('<url><loc>'+source.BASE+p+'</loc></url>' for p in ['/blogs/winter2025.html','/blog/summer2026.html','/return-exchange-global.html','/privacy-policy.html','/ready-to-wear.html','/black-cambric-kurta/1-26-320-A-C1-VG_MULTI.html','/account/orders.html'])+'</urlset>'
  requested=[]
  class Reader(source.PublicCatalog):
   def read(self,url,**kwargs):
    requested.append(url)
    text=('User-agent: *\nSitemap: '+source.BASE+'/sitemap_0.xml') if url.endswith('robots.txt') else sitemap if url.endswith('.xml') else fixture('master')
    return SimpleNamespace(text=text,content=text.encode())
  with patch.object(source,'normalize_product',return_value={'id':'main','variants':[]}):
   products,complete=Reader({'_chotu_wait':lambda:None},lambda _:None).catalog()
  self.assertEqual(len(products),1);self.assertFalse(complete)
  self.assertEqual([u for u in requested if u.endswith('.html')],[URL])

 def test_content_page_is_skipped_but_broken_product_is_not(self):
  from unittest.mock import patch
  other=source.BASE+'/seasonal/lookbook2026.html'
  for action,raises in [('Page-Show',False),('Product-Show',True)]:
   class Reader(source.PublicCatalog):
    def read(self,url,**kwargs):
     text=('User-agent: *\nSitemap: '+source.BASE+'/sitemap_0.xml') if url.endswith('robots.txt') else '<urlset><url><loc>'+other+'</loc></url><url><loc>'+URL+'</loc></url></urlset>' if url.endswith('.xml') else '<div class="page" data-action="'+action+'"></div>' if url==other else fixture('master')
     return SimpleNamespace(text=text,content=text.encode())
   with patch.object(source,'normalize_product',side_effect=lambda html,*args: {'id':'main','variants':[]} if 'product-set-detail' in html else (_ for _ in ()).throw(ValueError('Primary product missing'))):
    if raises:
     with self.assertRaisesRegex(ValueError,'Primary product missing'):Reader({'_chotu_wait':lambda:None},lambda _:None).catalog()
    else:self.assertEqual(len(Reader({'_chotu_wait':lambda:None},lambda _:None).catalog()[0]),1)

 def test_category_only_sitemap_discovers_deduplicated_public_product_links(self):
  from unittest.mock import patch
  category=source.BASE+'/ready-to-wear/essentials/kurta/'
  pages={source.BASE+'/robots.txt':'User-agent: *\nDisallow: /on/demandware.store/\nSitemap: '+source.BASE+'/sitemap_0.xml',source.BASE+'/sitemap_0.xml':'<urlset><url><loc>'+category+'</loc></url></urlset>',category:'<div class="product-tile"><a href="https://pk.khaadi.com">Root</a><a href="https://pk.khaadi.com?lang=en">Empty path query</a><a href="#">Anchor</a><a href="mailto:info@khaadi.com">Email</a><a href="tel:123">Phone</a><a href="javascript:;">Menu</a><a href="'+URL+'?source=listing">Kurta</a><a href="'+URL+'">Duplicate</a><a href="/blogs/winter2025.html">Blog</a><a href="https://us.khaadi.com/wrong/123.html">Foreign</a></div>',URL:fixture('master')}
  requests=[]
  class Reader(source.PublicCatalog):
   def read(self,url,**kwargs):
    requests.append(url);text=pages[url];return SimpleNamespace(text=text,content=text.encode(),status_code=200)
  with patch.object(source,'normalize_product',return_value={'id':'main','variants':[]}):
   products,complete=Reader({'_chotu_wait':lambda:None},lambda _:None).catalog()
  self.assertEqual(len(products),1);self.assertFalse(complete);self.assertEqual(requests.count(URL),1);self.assertIn(category,requests)
 def test_removed_category_does_not_stop_other_live_category(self):
  from unittest.mock import patch
  dead=source.BASE+'/old-collection/';live=source.BASE+'/ready-to-wear/'
  class Reader(source.PublicCatalog):
   def read(self,url,**kwargs):
    if url.endswith('robots.txt'):text='User-agent: *\nSitemap: '+source.BASE+'/sitemap_0.xml'
    elif url.endswith('.xml'):text='<urlset><url><loc>'+dead+'</loc></url><url><loc>'+live+'</loc></url></urlset>'
    elif url==live:text='<a href="'+URL+'">Kurta</a>'
    else:text=fixture('master')
    return SimpleNamespace(text=text,content=text.encode(),status_code=404 if url==dead else 200)
  with patch.object(source,'normalize_product',return_value={'id':'main','variants':[]}):self.assertEqual(len(Reader({'_chotu_wait':lambda:None},lambda _:None).catalog()[0]),1)

 def test_actual_captured_homepage_links_discover_products_without_crashing(self):
  from unittest.mock import patch
  category=source.BASE+'/ready-to-wear/'
  class Reader(source.PublicCatalog):
   def read(self,url,**kwargs):
    if url.endswith('robots.txt'):text='User-agent: *\nSitemap: '+source.BASE+'/sitemap_0.xml'
    elif url.endswith('.xml'):text='<urlset><url><loc>'+category+'</loc></url></urlset>'
    elif url==category:text=(FIX/'homepage_links.html').read_text()
    else:text=fixture('master')
    return SimpleNamespace(text=text,content=text.encode(),status_code=200)
  with patch.object(source,'normalize_product',return_value={'id':'main','variants':[]}):
   products,complete=Reader({'_chotu_wait':lambda:None},lambda _:None).catalog()
  self.assertGreater(len(products),1);self.assertFalse(complete)
 def test_completed_discovery_queue_is_restored_and_corruption_rebuilt(self):
  from unittest.mock import patch
  from urllib.robotparser import RobotFileParser
  category=source.BASE+'/ready-to-wear/'
  robots='User-agent: *\nSitemap: '+source.BASE+'/sitemap_0.xml'
  requests=[]
  class Reader(source.PublicCatalog):
   def read(self,url,**kwargs):
    requests.append(url)
    text='<urlset><url><loc>'+category+'</loc></url></urlset>' if url.endswith('.xml') else '<a href="'+URL+'">Kurta</a>'
    return SimpleNamespace(text=text,content=text.encode(),status_code=200)
  with tempfile.TemporaryDirectory() as tmp:
   reader=Reader({'_chotu_tls':SimpleNamespace(saved_api_path=Path(tmp)/'api.sqlite3'),'_chotu_wait':lambda:None},lambda _:None);reader.robot=RobotFileParser();reader.robot.parse(robots.splitlines())
   response=SimpleNamespace(text=robots)
   try:
    first=reader.discover_urls(response);second=reader.discover_urls(response)
    self.assertEqual(first,second);self.assertEqual(requests.count(category),1)
    (Path(tmp)/'khaadi-discovery.json').write_text('{broken')
    self.assertEqual(reader.discover_urls(response),first);self.assertEqual(requests.count(category),2)
   finally:reader.close()
