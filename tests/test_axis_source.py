import json,unittest
from axis_source_support import page_products
class AxisPublicState(unittest.TestCase):
 def test_exact_embedded_product_and_variants_preserved_without_eval(self):
  product={'id':'a','slug':'actual','name':'Actual tracksuit','price':8999,'salePrice':5999,'variants':[{'size':'L','stock':100,'price':5999}],'adminToken':'NEVER'}
  payload='3:'+json.dumps({'product':product});html='<script>self.__next_f.push('+json.dumps([1,payload])+')</script>'
  rows=page_products(html);self.assertEqual(len(rows),1);self.assertEqual(rows[0]['variants'],product['variants']);self.assertEqual(rows[0]['salePrice'],5999);self.assertNotIn('adminToken',rows[0])
 def test_header_config_and_unlinked_prices_are_not_products(self):
  self.assertEqual(page_products('<script>self.config={"name":"Offer","price":1};</script>'),[])
 def test_malformed_script_is_not_executed(self):
  self.assertEqual(page_products('<script>self.__next_f.push(executeAnything());</script>'),[])
