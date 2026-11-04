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
