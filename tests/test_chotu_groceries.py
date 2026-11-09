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
  provider=SimpleNamespace(products={p['id']:p},label='public HTML fixture',supports=lambda _:True,catalog=lambda:[p],read=lambda _:p)
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
  row=dict(name='Dawn Garlic Croutons 125g',Category='Bread, Bakery & Pasta',source_url=source.BASE+'/item',owner_scope_url=source.BASE+'/allproducts/?manufacturer=890',subcategory_source='owner_supplied_scope')
  self.assertEqual(category(row,source.STORE)[0],'Bread, Bakery & Pasta');self.assertEqual(audit(row,row),[])
  changed=dict(row,Category='Snacks');self.assertTrue(audit(changed,row))
  with self.assertRaises(ValueError):category(changed,source.STORE)
 def test_electronics_are_excluded_before_option_price_export(self):
  self.assertTrue(source.electronic_item('National Electric Kettle',['Home Appliances']))
  self.assertTrue(source.electronic_item('Hair Dryer',['Beauty','Hair Care']))
  self.assertFalse(source.electronic_item('Shampoo for Dry Hair',['Hair Care']))
  self.assertFalse(source.electronic_item('Durex Condoms 3 Pack',['Sexual Wellness']))
  with self.assertRaisesRegex(source.IncompleteProduct,'electronic item excluded'):source.product(page(title='USB Charger',schema_price=0),source.BASE+'/item')
