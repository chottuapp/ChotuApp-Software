import copy,json,sys,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import czone_source_support as c
import install_czone_source as installer

URL=c.BASE+'/adapter'
def page(price='250.00',sale='0.00',stock='InStock',variant=None):
    p={'productID':'2462094','productName':'Adapter A14','productURL':'/adapter','productDesc':'USB adapter.','productHighlights':'Input: USB3.0_Output: TYPE C','productPrice':{'price':price,'listPrice':sale,'isHidePrice':'0'},'productStock':{'stockStatus':'instock' if stock=='InStock' else 'outofstock','soldQuantity':'16'},'productImages':[{'mediaType':'image','imageFile':'https://example.com/front.jpg','isMain':'1','priority':'1'},{'mediaType':'image','imageFile':'https://example.com/back.jpg','isMain':'0','priority':'2'}],'imageFile':'https://example.com/front.jpg','productFields':{'sku':'SKU123','vendorName':'Amaze','categoryName':'Adapters','warranty':'6 - Month(s) Warranty'},'productVariants':variant,'productOptions':None,'isVariant':'0'}
    a=[]
    def pack(value):
        i=len(a);a.append(None)
        if isinstance(value,dict):a[i]={k:pack(v) for k,v in value.items()}
        elif isinstance(value,list):a[i]=[pack(v) for v in value]
        else:a[i]=value
        return i
    pack(p)
    schema={'@type':'Product','name':'Adapter A14','offers':{'@type':'Offer','url':URL,'priceCurrency':'PKR','price':price,'availability':'https://schema.org/'+stock,'itemCondition':'https://schema.org/NewCondition'}}
    return '<script id="__NUXT_DATA__" type="application/json">'+json.dumps(a)+'</script><script type="application/ld+json">'+json.dumps(schema)+'</script><div class="wx-product-info-item-price"><span class="wx-product-price">Rs. '+price+'</span></div>'

class CzoneTests(unittest.TestCase):
    def test_order_only_variants_are_excluded_before_price_interpretation(self):
        html=page(variant=[{'variantID':'699775','price':'299000.00','isActive':'1'}])
        html=html.replace('"instock"','"onorderonly"')
        product=c.parse_product(html,URL)
        self.assertFalse(product['available']);self.assertNotIn('price',product)
    def test_parallel_pages_use_three_sessions_and_durable_thread_local_caches(self):
        import threading,time
        from fast_fetch_support import GatedSession,RequestGate
        from resume_support import SessionProxy,ResponseCache
        from unittest.mock import patch
        import requests
        with tempfile.TemporaryDirectory() as temp:
            tls=threading.local();pause=lambda:None
            gate=RequestGate(pause,lambda x:None,baseline=.001)
            tls.fast_gate=gate;tls.saved_api_path=Path(temp)/'api.sqlite3'
            state={'active':0,'max':0,'calls':0};lock=threading.Lock()
            class Raw:
                headers={}
                def get(self,url,**kw):
                    with lock:
                        state['active']+=1;state['calls']+=1;state['max']=max(state['max'],state['active'])
                    time.sleep(.025)
                    response=requests.Response();response.status_code=200;response.url=url;response._content=b'public HTML';response.encoding='utf-8'
                    with lock:state['active']-=1
                    return response
                def close(self):pass
            factory=lambda:GatedSession(SessionProxy(Raw(),tls,pause),tls,pause)
            g={'_chotu_tls':tls,'_chotu_wait':pause,'requests':SimpleNamespace(Session=factory)}
            urls=[c.BASE+'/item-'+str(i) for i in range(9)]
            self.assertEqual({u for u,b in c.parallel_pages(g,urls,lambda x:None)},set(urls))
            self.assertGreater(state['max'],1);self.assertLessEqual(state['max'],3)
            self.assertEqual(state['calls'],9)
            cache=ResponseCache(Path(temp)/'pages.sqlite3')
            self.assertTrue(all(cache.get(url) is not None for url in urls));cache.close()
            list(c.parallel_pages(g,urls,lambda x:None));self.assertEqual(state['calls'],9)
            self.assertIs(tls.fast_gate,gate)
    def test_nuxt_literal_numbers_are_not_reference_indices(self):
        from bs4 import BeautifulSoup
        values=[{'price':1,'count':2,'zero':3,'flag':4},27000,1,0,True]
        _,decode=c.nuxt(BeautifulSoup('<script id="__NUXT_DATA__">'+json.dumps(values)+'</script>','html.parser'))
        self.assertEqual(decode(values[0]),{'price':27000,'count':1,'zero':0,'flag':True})
    def test_nuxt_shared_and_cyclic_references_preserved(self):
        from bs4 import BeautifulSoup
        values=[{'first':1,'second':1},{'self':1,'quantity':2},32]
        _,decode=c.nuxt(BeautifulSoup('<script id="__NUXT_DATA__">'+json.dumps(values)+'</script>','html.parser'))
        result=decode(values[0]);self.assertIs(result['first'],result['second'])
        self.assertIs(result['first']['self'],result['first']);self.assertEqual(result['first']['quantity'],32)
    def test_nuxt_out_of_bounds_rejected(self):
        from bs4 import BeautifulSoup
        _,decode=c.nuxt(BeautifulSoup('<script id="__NUXT_DATA__">[{"price":999}]</script>','html.parser'))
        with self.assertRaisesRegex(ValueError,'out of bounds'):decode(0)
    def test_existing_chrome_used_without_download(self):
        calls=[];browser=object()
        driver=SimpleNamespace(launch=lambda **kw:(calls.append(kw),browser)[1])
        self.assertIs(c.launch_catalog_browser(driver,lambda s:None),browser)
        self.assertEqual(calls,[{'headless':True,'channel':'chrome'}])
    def test_existing_edge_fallback(self):
        calls=[];browser=object()
        def launch(**kw):
            calls.append(kw)
            if kw.get('channel')=='chrome':raise RuntimeError('Chrome not installed')
            return browser
        self.assertIs(c.launch_catalog_browser(SimpleNamespace(launch=launch),lambda s:None),browser)
        self.assertEqual(calls[-1]['channel'],'msedge')
    def test_missing_browsers_stop_without_downloader(self):
        def launch(**kw):raise RuntimeError('Browser unavailable')
        with self.assertRaisesRegex(RuntimeError,'No browser download was attempted'):
            c.launch_catalog_browser(SimpleNamespace(launch=launch),lambda s:None)
    def test_price_gallery_warranty_specifications(self):
        p=c.parse_product(page(),URL)
        self.assertEqual(str(p['price']),'250.00');self.assertEqual(len(p['images']),2)
        self.assertIn('6 - Month(s) Warranty',p['description']);self.assertIn('Input: USB3.0',p['description']);self.assertEqual(p['sold'],16)
    def test_mismatched_display_price_stops(self):
        with self.assertRaisesRegex(ValueError,'Displayed'):c.parse_product(page().replace('Rs. 250.00','Rs. 999'),URL)
    def test_no_minor_unit_conversion(self):
        self.assertEqual(c.parse_product(page('27000.00'),URL)['price'],27000)
    def test_cross_product_offer_rejected(self):
        with self.assertRaises(ValueError):c.parse_product(page().replace(URL,c.BASE+'/other'),URL)
    def test_unavailable_not_sellable(self):
        self.assertFalse(c.parse_product(page(stock='OutOfStock'),URL)['available'])
    def test_unknown_variants_never_dropped(self):
        with self.assertRaisesRegex(ValueError,'variant schema'):c.parse_product(page(variant=[{'id':'unverified'}]),URL)
    def test_sale_and_no_fake_discount(self):
        self.assertEqual(c.parse_product(page(sale='300.00'),URL)['base'],300)
        self.assertEqual(c.parse_product(page(sale='0.00'),URL)['base'],250)
    def test_installer_preserves_source_and_idempotent(self):
        text="_chotuapp_run_site_original = run_site\nif __name__=='__main__':\n    pass\n"
        transformed=installer.transform(text)
        self.assertEqual(installer.transform(transformed),transformed)
        self.assertEqual(transformed.replace(installer.HOOK,''),text)
    def test_non_czone_uses_original(self):
        calls=[];g={'_chotuapp_run_site_original':lambda *x:calls.append(x)};c.enable_czone_source(g)
        g['_chotuapp_run_site_original']('https://vincecare.com','Vince','x',print)
        self.assertEqual(calls[0][0],'https://vincecare.com')
    def test_export_matches_template_and_keeps_prices(self):
        import main,openpyxl
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);listing='<p>1 Products</p><script id="__NUXT_DATA__">[]</script>'
            sitemap='<urlset><url><loc>'+URL+'</loc></url></urlset>'
            pages={c.BASE+'/products':listing.encode(),c.BASE+'/sitemap.xml':sitemap.encode(),URL:page().encode()}
            class Session:
                def get(self,url,**kw):return SimpleNamespace(content=pages[url],raise_for_status=lambda:None)
            g={'S':Session(),'_chotu_wait':lambda:None,'OUT':root,'load_workbook':openpyxl.load_workbook,'uid':main.uid,'write_row':main.write_row}
            c.export(g,c.BASE,'Computer Zone',Path(main.__file__).parent/'ChotuApp_Template.xlsx',lambda x:None)
            result=openpyxl.load_workbook(root/'Computer Zone - REFRESH REVIEW.xlsx')
            products=list(result['Products'].values);r=dict(zip(products[0],products[1]))
            self.assertEqual(r['base_price (PKR)'],250);self.assertIn('TYPE C',r['description'])
            self.assertEqual(result['Product Images'].max_row,3)
            self.assertEqual(result['Variant Combinations'].max_row,2)
            self.assertEqual(r['source_url'],URL)

if __name__=='__main__':unittest.main()
