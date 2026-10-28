import unittest,copy
from woocommerce_source_support import offer,variants
class WooTests(unittest.TestCase):
 def product(self):return dict(id=10,type='simple',is_in_stock=True,is_purchasable=True,is_on_backorder=False,prices=dict(currency_code='PKR',currency_minor_unit=0,price='1469',regular_price='2099'))
 def test_exact_currency_scale_and_discount(self):
  p=self.product();self.assertEqual(tuple(map(str,offer(p)[:2])),('2099','1469'));p['prices']['currency_minor_unit']=2;p['prices']['price']='146900';p['prices']['regular_price']='209900';self.assertEqual(tuple(map(str,offer(p)[:2])),('2099','1469'))
 def test_unknown_stock_and_non_pkr_rejected(self):
  p=self.product();p['is_in_stock']=None
  with self.assertRaises(ValueError):offer(p)
  p=self.product();p['prices']['currency_code']='USD'
  with self.assertRaises(ValueError):offer(p)
 def test_real_variant_identity_not_cartesian_product(self):
  p=self.product();p.update(type='variable',variations=[dict(id=11,attributes=[dict(name='Size',value='M')])]);v=self.product();v.update(id=11,parent=10,type='variation');self.assertEqual(variants(p,lambda path:v)[0][1],{'Size':'M'})
  v['parent']=999
  with self.assertRaises(ValueError):variants(p,lambda path:v)
 def test_wildcard_options_rejected(self):
  p=self.product();p.update(type='variable',variations=[dict(id=11,attributes=[dict(name='Size',value='')])]);v=self.product();v.update(id=11,parent=10,type='variation')
  with self.assertRaises(ValueError):variants(p,lambda path:v)
