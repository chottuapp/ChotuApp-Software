import json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace
import chotu_groceries_source_support as source
ROOT=Path(__file__).resolve().parents[1]
def page(price='200',schema_price=200,availability='InStock',options='',title='Dawn Garlic Croutons 125g',body='Garlic-flavoured croutons in a 125g pack. Contains wheat.'):
 raw={'@type':'Product','name':title,'offers':{'price':schema_price,'priceCurrency':'PKR','availability':'https://schema.org/'+availability}}
 return '<link rel="canonical" href="https://www.naheed.pk/item"><div class="breadcrumbs"><li><a href="/">Home</a></li><li><a href="/groceries">Groceries</a></li><li><a href="/snacks">Snacks</a></li></div><div class="product-info-main"><h1>'+title+'</h1><span class="sku">123</span><div class="brand-name"><a>Dawn</a></div><div data-role="priceBox" data-product-id="182197"><span data-price-type="finalPrice" data-price-amount="'+price+'"></span></div><div class="att-stock"><span class="attribute-value">In Stock</span></div></div><div class="product attribute description"><div class="value">'+body+'</div></div><a class="MagicZoom" href="https://media.naheed.pk/catalog/product/item.jpg"></a>'+options+'<script type="application/ld+json">'+json.dumps(raw)+'</script>'
class GroceryTests(unittest.TestCase):
 def test_exact_source_price_stock_and_taxonomy(self):
  p=source.product(page(),source.BASE+'/item');self.assertEqual(p['prices']['price'],'2000000');self.assertTrue(p['is_in_stock']);self.assertEqual(p['categories'][-1]['name'],'Snacks');self.assertIn('125g',p['description']);self.assertIn('Contains wheat',p['description']);self.assertEqual(p['id'],182197)
 def test_no_retailer_name_in_customer_description(self):
  p=source.product(page(body='Garlic croutons in a 125g pack. Available at Naheed.pk.'),source.BASE+'/item');self.assertNotIn('naheed',p['description'].lower());self.assertIn('125g',p['description']);self.assertIn('naheed.pk',p['images'][0]['src'])
 def test_conflicting_commercial_facts_never_export(self):
  for html in [page(price='201'),page(availability='OutOfStock')]:
   with self.assertRaises(ValueError):source.product(html,source.BASE+'/item')
 def test_options_are_not_fabricated_from_a_minimum_price(self):
  with self.assertRaises(source.IncompleteProduct):source.product(page(options='<select class="super-attribute-select"></select>'),source.BASE+'/item')
 def test_all_owner_pages_and_categories_are_preserved(self):
  r=json.loads((ROOT/'cloud/chotu-groceries-request.json').read_text());self.assertEqual(len(r['pages']),99);self.assertEqual(len({p['group'] for p in r['pages']}),20);self.assertIsNone(r['shop_code']);self.assertEqual(len({p['url'] for p in r['pages']}),99)
  self.assertEqual([p['label'] for p in r['pages'] if p['group']=='Condoms Wellness'],['Durex','Josh'])
  self.assertTrue(all('utm_' not in p['url'] for p in r['pages']))
 def test_real_access_denial_stops_without_alternate_route(self):
  reader=source.PublicCatalog({'S':SimpleNamespace(get=lambda *a,**k:SimpleNamespace(status_code=403,content=b'Forbidden')), '_chotu_wait':lambda:None},lambda _:None)
  with self.assertRaisesRegex(RuntimeError,'SOURCE BLOCKED'):reader.read_page(source.BASE+'/catalogsearch/result/?q=Durex')
 def test_foreign_source_is_never_read(self):
  reader=source.PublicCatalog({},lambda _:None)
  with self.assertRaises(ValueError):reader.read_page('https://other.example/item')
 def test_export_keeps_owner_category_and_blank_code_with_source_taxonomy_separate(self):
  from test_app import main
  from openpyxl import load_workbook
  p=source.product(page(),source.BASE+'/item');p.update(owner_category='Bread, Bakery & Pasta',owner_scope_url=source.BASE+'/allproducts/?manufacturer=890')
  provider=SimpleNamespace(coverage_status='complete',coverage_issues=[],products={p['id']:p},label='public HTML fixture',supports=lambda _:True,catalog=lambda:[p],read=lambda _:p)
  with tempfile.TemporaryDirectory() as tmp:
   g=dict(vars(main),OUT=Path(tmp),_chotu_wait=lambda:None)
   g['_chotuapp_run_site_original']=lambda *a:None
   with patch.object(source,'PublicCatalog',return_value=provider):
    source.enable_chotu_groceries(g);g['_chotuapp_run_site_original'](source.BASE,source.STORE,ROOT/'importer-files/Chotu_Products_Import_Template_Discount_Tags.xlsx',lambda _:None)
   book=load_workbook(Path(tmp)/(source.STORE+' - REFRESH REVIEW.xlsx'));s=book['Products'];row=dict(zip([c.value for c in s[1]],[c.value for c in s[2]]))
   self.assertEqual(row['Category'],'Bread, Bakery & Pasta');self.assertEqual(row['website_category_path'],'Groceries > Snacks');self.assertFalse(row['shop_code']);self.assertEqual(row['base_price (PKR)'],200);self.assertNotIn('naheed',row['description'].lower());self.assertIn('wheat',row['description']);book.close()
 def test_runtime_copies_exact_owner_scope(self):
  from runtime import prepare_engine
  with tempfile.TemporaryDirectory() as tmp:
   engine=prepare_engine(Path(tmp));self.assertEqual(json.loads(engine.with_name('chotu-groceries-request.json').read_text())['store'],source.STORE);self.assertIn('enable_chotu_groceries',engine.read_text());self.assertTrue(engine.with_name('chotu_groceries_source_support.py').exists())
 def test_broad_search_hits_do_not_change_owner_category_purpose(self):
  p=dict(name='Milk Soap Bar',categories=[dict(name='Skin Care')]);self.assertFalse(source.scope_supported('Milk & Dairy',p))
  p=dict(name='Dove Body Wash',categories=[dict(name='Soap & Body Wash')]);self.assertFalse(source.scope_supported('Shampoo & Hair Care',p))
  p=dict(name='Durex Extra Safe Condoms 3 Pack',categories=[dict(name='Sexual Wellness')]);self.assertTrue(source.scope_supported('Condoms Wellness',p))
 def test_scope_discovery_deduplicates_products_and_ignores_card_actions(self):
  with tempfile.TemporaryDirectory() as tmp:
   reader=source.PublicCatalog({'_chotu_wait':lambda:None,'__file__':str(Path(tmp)/'main.py')},lambda _:None)
   scope=dict(group='Bread, Bakery & Pasta',label='Dawn',url=source.BASE+'/allproducts/?manufacturer=890');reader.request={'pages':[scope]}
   listing='<ol id="product_result"><li class="product-item"><a href="/item">Product</a><a href="/item">Image</a><a href="javascript:void(0)">Wishlist</a><a href="/checkout/cart/add/id/182197">Cart</a></li></ol><p class="toolbar-amount">1 Item</p>'
   reader.read_page=lambda url:listing if url==scope['url'] else page()
   products=reader.catalog();self.assertEqual(len(products),1);self.assertEqual(products[0]['owner_category'],scope['group']);self.assertEqual(products[0]['categories'][-1]['name'],'Snacks')
   self.assertTrue((Path(tmp)/'audit_reports'/source.STORE/(source.STORE+' - SCOPE COVERAGE.csv')).is_file())
 def test_rule804_cannot_replace_owner_category_with_inferred_taxonomy(self):
  from hold804_repairs import category
  from grocery_owner_scope import audit
  row=dict(name='Dawn Garlic Croutons 125g',Category='Bread, Bakery & Pasta',source_url=source.BASE+'/item',owner_scope_url=source.BASE+'/allproducts/?manufacturer=890',subcategory_source='owner_supplied_scope',source_scope_coverage_status='complete')
  self.assertEqual(category(row,source.STORE)[0],'Bread, Bakery & Pasta');self.assertEqual(audit(row,row),[])
  changed=dict(row,Category='Snacks');self.assertTrue(audit(changed,row))
  with self.assertRaises(ValueError):category(changed,source.STORE)
 def test_electronics_are_excluded_before_option_price_export(self):
  self.assertTrue(source.electronic_item('National Electric Kettle',['Home Appliances']))
  self.assertTrue(source.electronic_item('Hair Dryer',['Beauty','Hair Care']))
  self.assertFalse(source.electronic_item('Shampoo for Dry Hair',['Hair Care']))
  self.assertFalse(source.electronic_item('Durex Condoms 3 Pack',['Sexual Wellness']))
  with self.assertRaisesRegex(source.IncompleteProduct,'electronic item excluded'):source.product(page(title='USB Charger',schema_price=0),source.BASE+'/item')
 def test_numbered_pages_are_all_followed(self):
  with tempfile.TemporaryDirectory() as tmp:
   reader=source.PublicCatalog({'_chotu_wait':lambda:None,'__file__':str(Path(tmp)/'main.py')},lambda _:None)
   scope=dict(group='Bread, Bakery & Pasta',label='Dawn',url=source.BASE+'/allproducts/?manufacturer=890');second=scope['url']+'&p=2'
   def listing(item,next_url=''):
    return '<div class="products-grid"><li class="product-item"><a class="product-item-link" href="/'+item+'">Product</a></li></div><p class="toolbar-amount">Items 1 - 1 of 2</p>'+('<div class="pages"><a href="'+next_url+'">2</a></div>' if next_url else '')
   reader.read_page=lambda url:listing('item',second) if url==scope['url'] else listing('item-two')
   links,total,pages=reader.discover_scope(scope)
   self.assertEqual(links,{source.BASE+'/item',source.BASE+'/item-two'});self.assertEqual(total,2);self.assertEqual(pages,{scope['url'],second})
 def test_stale_source_total_does_not_abort_other_scopes_or_approve_complete_catalog(self):
  from grocery_owner_scope import audit
  with tempfile.TemporaryDirectory() as tmp:
   reader=source.PublicCatalog({'_chotu_wait':lambda:None,'__file__':str(Path(tmp)/'main.py')},lambda _:None)
   scope=dict(group='Bread, Bakery & Pasta',label='Dawn',url=source.BASE+'/allproducts/?manufacturer=890');other=dict(scope,url=source.BASE+'/allproducts/?manufacturer=891');reader.request={'pages':[scope,other]}
   listing='<div class="products-grid"><li class="product-item"><a class="product-item-link" href="/item">Product</a></li></div><p class="toolbar-amount">Items 1 - 1 of 2</p>'
   seen=[]
   def read(url):
    seen.append(url);return page() if url==source.BASE+'/item' else listing if url==scope['url'] else listing.replace('of 2','of 1')
   reader.read_page=read
   with patch('grocery_browser_support.render_listing',return_value=listing):products=reader.catalog()
   self.assertIn(other['url'],seen);self.assertEqual(len(products),1);self.assertEqual(reader.coverage_status,'review_required');self.assertEqual(len(reader.coverage_issues),1)
   row=dict(Category='Bread, Bakery & Pasta',source_url=source.BASE+'/item',owner_scope_url=scope['url'],subcategory_source='owner_supplied_scope',source_scope_coverage_status=reader.coverage_status)
   self.assertTrue(audit(row,row));self.assertIn('coverage unresolved',audit(row,row)[0])
   text=(Path(tmp)/'audit_reports'/source.STORE/(source.STORE+' - SCOPE COVERAGE.csv')).read_text();self.assertIn('review_required',text)
 def test_toolbar_total_uses_catalog_total_not_a_trailing_page_number(self):
  self.assertEqual(source.listing_total('Items 1 - 31 of 34'),34)
  self.assertEqual(source.listing_total('Items 1 - 12 of 34 Page 1 of 3'),34)
  self.assertEqual(source.listing_total('1 Item'),1)
  with self.assertRaises(ValueError):source.listing_total('Loading products')
 def test_scroll_and_delayed_load_more_are_exhausted(self):
  from grocery_browser_support import exhaust_listing,SELECTOR
  pending=set()
  class Node:
   def __init__(self,page,kind):self.page=page;self.kind=kind
   @property
   def first(self):return self
   def count(self):return self.page.number if self.kind==SELECTOR else 1 if self.kind=='#load-more' else 0
   def is_visible(self):return self.page.more
   def click(self,**kwargs):self.page.more=False;self.page.delay=2;pending.add('catalog-xhr')
  class Page:
   number=2;more=True;delay=0;scrolled=False
   def locator(self,kind):return Node(self,kind)
   def wait_for_timeout(self,ms):
    if self.delay:
     self.delay-=1
     if not self.delay:self.number=5;pending.clear()
   def evaluate(self,*args):
    if not self.scrolled:self.number+=2;self.scrolled=True
  page=Page();exhaust_listing(page,lambda:None,lambda _:None,[],pending,max_steps=10)
  self.assertEqual(page.number,7);self.assertFalse(pending)
 def test_structured_source_description_and_images_are_not_missed(self):
  from bs4 import BeautifulSoup
  soup=BeautifulSoup(page(),'html.parser');soup.select_one('.product.attribute.description').decompose();soup.select_one('.MagicZoom').decompose()
  script=soup.select_one('script[type="application/ld+json"]');raw=json.loads(script.get_text());raw.update(description='Garlic croutons in a 125g pack. Contains wheat.',image='https://media.naheed.pk/catalog/product/source.jpg');script.string=json.dumps(raw)
  duplicate=soup.new_tag('script');duplicate['type']='application/ld+json';duplicate.string=json.dumps(raw);soup.append(duplicate)
  p=source.product(str(soup),source.BASE+'/item');self.assertIn('125g',p['description']);self.assertIn('wheat',p['description']);self.assertEqual(p['images'][0]['src'],raw['image'])
 def test_fresh_scope_reconciliation_removes_the_hold_only_when_totals_match(self):
  with tempfile.TemporaryDirectory() as tmp:
   reader=source.PublicCatalog({'_chotu_wait':lambda:None,'__file__':str(Path(tmp)/'main.py')},lambda _:None)
   scope=dict(group='Bread, Bakery & Pasta',label='Dawn',url=source.BASE+'/allproducts/?manufacturer=890');reader.request={'pages':[scope]}
   one=source.BASE+'/item';two=source.BASE+'/item-two';calls=[]
   def discover(selected):
    calls.append(reader.force_fresh);return ({one,two} if reader.force_fresh else {one},2,{scope['url']})
   reader.discover_scope=discover;reader.read_page=lambda url:page() if url==one else page().replace('/item','/item-two').replace('182197','182198')
   products=reader.catalog();self.assertEqual(calls,[False,True]);self.assertEqual(len(products),2);self.assertEqual(reader.coverage_status,'complete');self.assertEqual(reader.coverage_issues,[])
 def test_transient_request_timeout_retries_and_exhaustion_pauses(self):
  import requests
  from unittest.mock import Mock
  response=Mock(status_code=200,url=source.BASE+'/item',content=b'ok',text='ok')
  getter=Mock(side_effect=[requests.exceptions.ReadTimeout(),response]);backoff=Mock()
  reader=source.PublicCatalog({'S':SimpleNamespace(get=getter),'_chotu_wait':lambda:None,'_chotu_backoff':backoff},lambda _:None)
  self.assertEqual(reader.read_page(source.BASE+'/item'),'ok');self.assertEqual(getter.call_count,2)
  reader.last=0;getter.side_effect=requests.exceptions.ReadTimeout()
  with self.assertRaisesRegex(RuntimeError,'SOURCE PAUSED.*3 attempts'):reader.read_page(source.BASE+'/item')
  self.assertEqual(getter.call_count,5)
 def test_tls_identity_failure_is_not_retried(self):
  import requests
  from unittest.mock import Mock
  getter=Mock(side_effect=requests.exceptions.SSLError('certificate mismatch'))
  reader=source.PublicCatalog({'S':SimpleNamespace(get=getter),'_chotu_wait':lambda:None},lambda _:None)
  with self.assertRaises(requests.exceptions.SSLError):reader.read_page(source.BASE+'/item')
  self.assertEqual(getter.call_count,1)
 def test_completed_scope_snapshot_survives_resume_without_fresh_rechecks(self):
  from resume_support import ResponseCache
  with tempfile.TemporaryDirectory() as tmp:
   cache=ResponseCache(Path(tmp)/'pages.sqlite3')
   config={'_chotu_wait':lambda:None,'__file__':str(Path(tmp)/'main.py'),'_chotu_tls':SimpleNamespace(saved_response_cache=cache)}
   scope=dict(group='Bread, Bakery & Pasta',label='Dawn',url=source.BASE+'/allproducts/?manufacturer=890')
   reader=source.PublicCatalog(config,lambda _:None);reader.request={'pages':[scope]}
   reader.discover_scope=lambda selected:({source.BASE+'/item'},2,{scope['url']})
   reader.read_page=lambda url:page()
   self.assertEqual(len(reader.catalog()),1);self.assertEqual(reader.coverage_status,'review_required')
   cache.close();cache=ResponseCache(Path(tmp)/'pages.sqlite3');config['_chotu_tls'].saved_response_cache=cache
   resumed=source.PublicCatalog(config,lambda _:None);resumed.request=reader.request;resumed.read_page=lambda url:page()
   resumed.discover_scope=lambda selected:self.fail('Completed scope was unnecessarily refetched')
   self.assertEqual(len(resumed.catalog()),1);self.assertEqual(resumed.coverage_status,'review_required');cache.close()
 def test_unfinished_browser_scope_is_held_while_other_products_continue(self):
  from grocery_browser_support import ListingRenderIncomplete
  with tempfile.TemporaryDirectory() as tmp:
   reader=source.PublicCatalog({'_chotu_wait':lambda:None,'__file__':str(Path(tmp)/'main.py')},lambda _:None)
   bad=dict(group='Bread, Bakery & Pasta',label='Dawn',url=source.BASE+'/allproducts/?manufacturer=890')
   good=dict(bad,url=source.BASE+'/allproducts/?manufacturer=891');reader.request={'pages':[bad,good]}
   calls=[]
   def read(url):
    calls.append(url)
    if url==bad['url']:return '<div id="product_result"></div><button id="load-more">Load more</button>'
    if url==good['url']:return '<div class="products-grid"><li class="product-item"><a class="product-item-link" href="/item">Product</a></li></div><p class="toolbar-amount">1 Item</p>'
    return page()
   reader.read_page=read
   with patch('grocery_browser_support.render_listing',side_effect=ListingRenderIncomplete('Public UI timeout')):products=reader.catalog()
   self.assertEqual(len(products),1);self.assertIn(good['url'],calls);self.assertEqual(reader.coverage_status,'review_required');self.assertIn('render_error',reader.coverage_issues[0])
 def test_real_browser_rate_limit_still_stops_instead_of_skipping_scope(self):
  with tempfile.TemporaryDirectory() as tmp:
   reader=source.PublicCatalog({'_chotu_wait':lambda:None,'__file__':str(Path(tmp)/'main.py')},lambda _:None)
   reader.request={'pages':[dict(url=source.BASE+'/catalogsearch/result/?q=Durex')]}
   reader.read_page=lambda url:'<div id="product_result"></div><button id="load-more">More</button>'
   with patch('grocery_browser_support.render_listing',side_effect=RuntimeError('SOURCE PAUSED: rate limit')):
    with self.assertRaisesRegex(RuntimeError,'rate limit'):reader.catalog()
 def test_browser_timeout_retains_already_visible_product_cards(self):
  from grocery_browser_support import ListingRenderIncomplete
  with tempfile.TemporaryDirectory() as tmp:
   reader=source.PublicCatalog({'_chotu_wait':lambda:None,'__file__':str(Path(tmp)/'main.py')},lambda _:None)
   scope=dict(group='Bread, Bakery & Pasta',label='Dawn',url=source.BASE+'/allproducts/?manufacturer=890');reader.request={'pages':[scope]}
   listing='<div class="products-grid"><li class="product-item"><a class="product-item-link" href="/item">Product</a></li></div><button id="load-more">More</button><p class="toolbar-amount">Items 1 - 1 of 2</p>'
   reader.read_page=lambda url:listing if url==scope['url'] else page()
   with patch('grocery_browser_support.render_listing',side_effect=ListingRenderIncomplete('Public UI timeout')):products=reader.catalog()
   self.assertEqual(len(products),1);self.assertEqual(reader.coverage_status,'review_required');self.assertEqual(reader.coverage_issues[0]['reported_total'],2)
