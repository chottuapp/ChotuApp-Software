import json,unittest
from axis_source_support import page_products,public_products
class AxisPublicState(unittest.TestCase):
 def test_normal_public_json_keeps_only_product_objects(self):
  rows=public_products({'data':{'product':{'id':'one','name':'Actual','price':500,'variants':[{'size':'M','stock':2}]}},'sessionToken':'NEVER'})
  self.assertEqual(rows,[{'id':'one','name':'Actual','price':500,'variants':[{'size':'M','stock':2}]}])
 def test_exact_embedded_product_and_variants_preserved_without_eval(self):
  product={'id':'a','slug':'actual','name':'Actual tracksuit','price':8999,'salePrice':5999,'variants':[{'size':'L','stock':100,'price':5999}],'adminToken':'NEVER'}
  payload='3:'+json.dumps({'product':product});html='<script>self.__next_f.push('+json.dumps([1,payload])+')</script>'
  rows=page_products(html);self.assertEqual(len(rows),1);self.assertEqual(rows[0]['variants'],product['variants']);self.assertEqual(rows[0]['salePrice'],5999);self.assertNotIn('adminToken',rows[0])
 def test_header_config_and_unlinked_prices_are_not_products(self):
  self.assertEqual(page_products('<script>self.config={"name":"Offer","price":1};</script>'),[])
 def test_malformed_script_is_not_executed(self):
  self.assertEqual(page_products('<script>self.__next_f.push(executeAnything());</script>'),[])
 def test_named_render_record_can_supply_product_under_other_prop_name(self):
  payload='a:'+json.dumps(['$','component',None,{'initialData':{'id':'p1','slug':'actual','name':'Actual','price':500}}])+'\n'
  html='<script>self.__next_f.push('+json.dumps([1,payload])+')</script>'
  self.assertEqual(page_products(html)[0]['id'],'p1')

class AxisCommercialGuards(unittest.TestCase):
 def html(self,variant_price=5999,stock=100,active=True):
  p={'productId':35,'slug':'actual','name':'Actual tracksuit','image':'https://images.example/actual.jpg','basePrice':5999,'variants':[{'id':1347,'product_id':35,'size_name':'L','color_name':'Navy','price':variant_price,'stock':stock,'is_active':active,'sku':None}]}
  payload='a:'+json.dumps(['$','component',None,{'currencyCode':'PKR','initialData':p}])+'\n'
  return '<main><h1>Actual tracksuit</h1><p>Rs. 5,999</p><p>Rs. 8,999</p><p>Source 300 GSM fabric details.</p><div>COLOR</div><div>SIZE</div></main><script>self.__next_f.push('+json.dumps([1,payload])+')</script>'
 def test_exact_ids_prices_options_and_stock_are_preserved(self):
  from axis_source_support import normalize_product
  parent,children=normalize_product(self.html(),'https://www.axispk.shop/product/actual')
  self.assertEqual(parent['id'],35);self.assertEqual(children[0]['id'],1347);self.assertEqual(children[0]['stock_quantity'],100);self.assertEqual(children[0]['prices']['price'],'599900');self.assertEqual(children[0]['prices']['regular_price'],'899900');self.assertEqual(children[0]['attributes'],[{'name':'Color','value':'Navy'},{'name':'Size','value':'L'}]);self.assertIn('300 GSM',parent['description'])
 def test_observed_axis_price_conflict_never_silently_selects_one_price(self):
  from axis_source_support import normalize_product,SourcePriceConflict
  with self.assertRaises(SourcePriceConflict):normalize_product(self.html(4699),'https://www.axispk.shop/product/actual')
 def test_unknown_stock_or_wrong_source_identity_is_held(self):
  from axis_source_support import normalize_product
  for html,url in [(self.html(stock=None),'https://www.axispk.shop/product/actual'),(self.html(),'https://www.axispk.shop/product/another'),(self.html(),'https://other.example/product/actual')]:
   with self.subTest(url=url),self.assertRaises(ValueError):normalize_product(html,url)
 def test_explicit_unavailable_variant_remains_unavailable(self):
  from axis_source_support import normalize_product
  parent,children=normalize_product(self.html(stock=0),'https://www.axispk.shop/product/actual');self.assertFalse(parent['is_in_stock']);self.assertFalse(children[0]['is_in_stock'])

class AxisRouting(unittest.TestCase):
 def test_axis_uses_its_public_source_and_other_stores_keep_their_adapter(self):
  from unittest.mock import Mock,patch
  from axis_source_support import enable_axis_source,PublicCatalog,BASE
  original=Mock(return_value='other');g={'_chotuapp_run_site_original':original};enable_axis_source(g)
  with patch('woocommerce_source_support.export',return_value='axis') as export:
   self.assertEqual(g['_chotuapp_run_site_original'](BASE,'Axis PK','template',print),'axis')
   self.assertIsInstance(export.call_args.kwargs['provider'],PublicCatalog)
  original.assert_not_called();self.assertEqual(g['_chotuapp_run_site_original']('https://other.example','Other','template',print),'other')
