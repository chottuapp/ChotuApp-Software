import copy,json,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
from openpyxl import load_workbook
from woocommerce_source_support import fixed_bundle_details,export
import test_woocommerce_source as fixtures

class FixedBundleContentsTests(unittest.TestCase):
 def fixture(self):
  p=fixtures.WooTests().product();p.update(type='easy_product_bundle',has_options=False,variations=[],attributes=[],name='DIY Bundle',permalink='https://houseoftools.com.pk/product/diy-bundle/',images=[dict(src='https://houseoftools.com.pk/cover.jpg')],description='',short_description='')
  entries=[]
  for ident,name in [(11,'Drill !0 Edition'),(12,'Screwdriver')]:
   entries.append(dict(product=dict(id=ident,name=name,is_variable='false',link='https://houseoftools.com.pk/product/item-'+str(ident)+'/',description='<p>Voltage: 12V<br>Includes 2 batteries.</p>'),quantity=1,optional='false',selected='true',can_change_product='false',edit_quantity='false'))
  config=dict(currency_code='PKR',bundles=dict(product=dict(id=p['id'],is_fixed_price=True,regular_price=2099,sale_price=1469),bundles=entries))
  return p,config
 def page(self,p,config):
  literal=json.dumps(config).replace(': true',': !0').replace(': false',': !1')
  text='<link rel="canonical" href="'+p['permalink']+'"><h1 class="product_title">'+p['name']+'</h1><script id="asnp-easy-product-bundles-shared-js-extra">var easyProductBundlesData='+literal+';</script>'
  return SimpleNamespace(status_code=200,url=p['permalink'],text=text)
 def test_complete_source_contents_and_minified_boolean_parser_preserve_literal_text(self):
  p,c=self.fixture();before=copy.deepcopy(p);result=fixed_bundle_details(p,self.page(p,c))
  self.assertEqual(p,before);self.assertIn('Drill !0 Edition',result['description']);self.assertIn('12V',result['description']);self.assertIn('2 batteries',result['description']);self.assertEqual(len(result['components']),2)
 def test_wrong_identity_prices_and_selectable_contents_fail_closed(self):
  for change in ('id','currency','price','optional','variable','quantity','target'):
   p,c=self.fixture();item=c['bundles']['bundles'][0]
   if change=='id':c['bundles']['product']['id']=999
   if change=='currency':c['currency_code']='USD'
   if change=='price':c['bundles']['product']['sale_price']=100
   if change=='optional':item['optional']='true'
   if change=='variable':item['product']['is_variable']='true'
   if change=='quantity':item['quantity']=None
   if change=='target':item['product']['link']='https://other.test/product/drill/'
   with self.subTest(change=change),self.assertRaises(ValueError):fixed_bundle_details(p,self.page(p,c))
 def test_export_has_one_bundle_offer_and_all_source_specs_without_child_sku_invention(self):
  from test_app import main
  p,c=self.fixture();provider=SimpleNamespace(label='fixture',supports=lambda _:True,catalog=lambda:[p],read=lambda _:p)
  with tempfile.TemporaryDirectory() as tmp:
   g=dict(vars(main),OUT=Path(tmp),S=SimpleNamespace(get=Mock(return_value=self.page(p,c))),_chotu_wait=lambda:None)
   export(g,'https://houseoftools.com.pk','House of Tools',Path(__file__).resolve().parents[1]/'importer-files/Chotu_Products_Import_Template_Discount_Tags.xlsx',lambda _:None,provider=provider)
   book=load_workbook(Path(tmp)/'House of Tools - REFRESH REVIEW.xlsx',read_only=True);iterator=book['Products'].iter_rows(values_only=True);headers=next(iterator);rows=[dict(zip(headers,r)) for r in iterator]
   self.assertEqual(len(rows),1);self.assertEqual(rows[0]['base_price (PKR)'],2099);self.assertEqual(rows[0]['sale_price (PKR, agar discount ho)'],1469);self.assertIn('12V',rows[0]['description']);self.assertEqual(book['Variant Combinations'].max_row,2);book.close()
