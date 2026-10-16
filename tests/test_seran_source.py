import copy,sys,unittest
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import seran_source_support as support
BASE='https://www.seran.com.pk'


def product(i=1):return {'id':i,'handle':'item-'+str(i),'title':'Product '+str(i),'variants':[{'id':i*10,'price':'1490.00','compare_at_price':'1790.00','available':True}], 'images':[{'src':'https://cdn.shopify.com/image.png'}]}
def xml(handles):return ('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'+''.join('<url><loc>'+BASE+'/products/'+h+'</loc><image:loc xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">https://other.example/image</image:loc></url>' for h in handles)+'</urlset>').encode()


class SeranSourceTests(unittest.TestCase):
    def fixture(self,batches=None,handles=None,denied=True):
        batches=batches or [[product()]];calls=[]
        def discover(base,log):
            calls.append(('normal',base))
            if denied:raise RuntimeError('Website endpoint unavailable (403): '+base+'/products.json?limit=250&page=1')
            return batches[0],True
        def get(url):
            calls.append(('api',url));page=int(url.rsplit('=',1)[-1]);return {'products':copy.deepcopy(batches[page-1])}
        response=SimpleNamespace(status_code=200,url=BASE+'/sitemap.xml',content=xml(handles or ['item-1']))
        g={'discover':discover,'get_json':get,'_chotu_wait':lambda:None,'_chotu_tls':SimpleNamespace(),'S':SimpleNamespace(get=lambda url,**kw:response)}
        support.enable_seran_source(g);return g,calls,response
    def test_healthy_source_unchanged_no_fallback(self):
        g,calls,_=self.fixture(denied=False);result=g['discover'](BASE,lambda x:None)
        self.assertEqual(result,([product()],True));self.assertEqual(len(calls),1)
    def test_403_fallback_matches_sitemap_and_preserves_prices_images_variants(self):
        g,calls,_=self.fixture();result=g['discover'](BASE,lambda x:None)
        self.assertEqual(result,([product()],True));self.assertEqual(g['_chotu_tls'].fast_products,[product()]);self.assertEqual(len(calls),2)
    def test_other_stores_and_non_403_errors_do_not_fallback(self):
        g,calls,_=self.fixture()
        with self.assertRaises(RuntimeError):g['discover']('https://other.example',lambda x:None)
        self.assertEqual(len(calls),1)
        for reason in ('SOURCE PAUSED: website rate limit','Network/JSON error: timeout'):
            def original(base,log):raise RuntimeError(reason)
            h={'discover':original};support.enable_seran_source(h)
            with self.assertRaisesRegex(RuntimeError,reason):h['discover'](BASE,lambda x:None)
    def test_partial_custom_all_collection_cannot_be_exported(self):
        g,_,_=self.fixture(handles=['item-1','item-2'])
        with self.assertRaisesRegex(RuntimeError,'SOURCE BLOCKED:.*1 sitemap products missing'):g['discover'](BASE,lambda x:None)
    def test_unverified_extra_products_cannot_be_exported(self):
        g,_,_=self.fixture(batches=[[product(),product(2)]])
        with self.assertRaisesRegex(RuntimeError,'SOURCE BLOCKED:.*1 collection products absent'):g['discover'](BASE,lambda x:None)
    def test_collection_denial_is_bounded_and_clear(self):
        g,calls,_=self.fixture()
        def denied(url):calls.append(('blocked',url));raise RuntimeError('Website endpoint unavailable (403): '+url)
        g['get_json']=denied
        with self.assertRaisesRegex(RuntimeError,'SOURCE BLOCKED: Seran'):g['discover'](BASE,lambda x:None)
        self.assertEqual(len(calls),2)
    def test_sitemap_denial_and_cross_source_redirect_fail_closed(self):
        for code,final in [(403,BASE+'/sitemap.xml'),(200,'https://unrelated.example/sitemap.xml')]:
            g,_,r=self.fixture();r.status_code=code;r.url=final
            with self.assertRaisesRegex(RuntimeError,'SOURCE BLOCKED:'):g['discover'](BASE,lambda x:None)
    def test_pagination_checks_full_coverage(self):
        records=[product(i) for i in range(1,252)]
        g,calls,_=self.fixture(batches=[records[:250],records[250:]],handles=[p['handle'] for p in records]);data,complete=g['discover'](BASE,lambda x:None)
        self.assertTrue(complete);self.assertEqual(data,records);self.assertEqual(len(calls),3)
    def test_duplicate_product_and_invalid_variant_fail_closed(self):
        for records in ([product(),product()], [dict(product(),variants=[{'id':10,'price':'1490'}])]):
            g,_,_=self.fixture(batches=[records])
            with self.assertRaisesRegex(RuntimeError,'SOURCE BLOCKED:'):g['discover'](BASE,lambda x:None)
    def test_nested_product_sitemap_and_rate_limit_preserved(self):
        g,_,r=self.fixture();nested=BASE+'/sitemap_products_1.xml?from=1&to=20'
        index=b'<sitemapindex><sitemap><loc>https://www.seran.com.pk/sitemap_products_1.xml?from=1&amp;to=20</loc></sitemap></sitemapindex>'
        def get(url,**kw):return SimpleNamespace(url=url,status_code=200,content=index if url.endswith('/sitemap.xml') else xml(['item-1']))
        g['S'].get=get;self.assertEqual(g['discover'](BASE,lambda x:None),([product()],True))
        r.status_code=429;g['S'].get=lambda *a,**kw:r
        with self.assertRaisesRegex(RuntimeError,'SOURCE PAUSED:'):g['discover'](BASE,lambda x:None)

if __name__=='__main__':unittest.main()
