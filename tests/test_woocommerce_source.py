import unittest,copy
from woocommerce_source_support import offer,variants,unpriced_unpurchasable
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

 def test_zero_price_is_excluded_only_when_explicitly_unpurchasable(self):
  p=self.product();p['prices'].update(price='0',regular_price='0');p['is_purchasable']=False
  self.assertTrue(unpriced_unpurchasable(p));p['is_purchasable']=True;self.assertFalse(unpriced_unpurchasable(p))
  with self.assertRaises(ValueError):offer(p)
 def test_declared_any_colour_expands_only_source_terms(self):
  p=self.product();p.update(type='variable',attributes=[dict(name='Color',has_variations=True,terms=[dict(name='Black',slug='black'),dict(name='Maroon',slug='maroon')])],variations=[dict(id=11,attributes=[dict(name='Color',value=None)])])
  v=self.product();v.update(id=11,parent=10,type='variation')
  self.assertEqual([a for _,a in variants(p,lambda path:v)],[{'Color':'Black'},{'Color':'Maroon'}])
 def test_conflicting_overlapping_source_rules_are_not_guessed(self):
  p=self.product();p.update(type='variable',attributes=[dict(name='Color',has_variations=True,terms=[dict(name='Black',slug='black')])],variations=[dict(id=11,attributes=[dict(name='Color',value=None)]),dict(id=12,attributes=[dict(name='Color',value='black')])])
  def get(path):
   v=self.product();v.update(id=int(path.split('/')[-1]),parent=10,type='variation');v['prices']['price']='1400' if v['id']==12 else '1469';return v
  with self.assertRaises(ValueError):variants(p,get)
 def test_removed_product_requires_own_declared_category_redirect(self):
  from woocommerce_source_support import removed_listing
  from types import SimpleNamespace
  p={'permalink':'https://xcessorieshub.com/product/removed/','categories':[{'link':'https://xcessorieshub.com/product-category/chargers/'}]}
  url=p['categories'][0]['link'];page='<link rel="canonical" href="'+url+'"><h1>Chargers</h1>'
  self.assertTrue(removed_listing(p,SimpleNamespace(status_code=200,url=url,text=page)))
  self.assertFalse(removed_listing(p,SimpleNamespace(status_code=200,url=url,text=page+'<form class="cart"></form>')))
  self.assertFalse(removed_listing(p,SimpleNamespace(status_code=200,url='https://other.example/',text=page)))
 def test_styles_removed_without_losing_product_facts(self):
  from woocommerce_source_support import content_text
  self.assertEqual(content_text('<style>.x{width:800px}</style><p>Size: 16 cm</p><script>test()</script>'),'Size: 16 cm')
 def test_media_recovery_requires_exact_cart_identity_and_canonical(self):
  from woocommerce_source_support import recovered_media
  from types import SimpleNamespace
  p=dict(id=12,name='Watch',permalink='https://xcessorieshub.com/product/watch/')
  page='<link rel="canonical" href="'+p['permalink']+'"><h1 class="product_title">Watch</h1><button name="add-to-cart" value="12"></button><div class="woocommerce-product-gallery"><img src="https://xcessorieshub.com/watch.jpg"></div>'
  r=SimpleNamespace(status_code=200,url=p['permalink'],text=page)
  self.assertEqual(recovered_media(p,r)['images'][0]['src'],'https://xcessorieshub.com/watch.jpg')
  r.text=page.replace('value="12"','value="99"');self.assertIsNone(recovered_media(p,r))
 def test_rendered_css_prefix_does_not_remove_actual_numeric_facts(self):
  from woocommerce_source_support import content_text
  from audit804 import tokens
  text='.product-card-container { width:800px; } Handmade Crochet Fruit-Themed Glasses Cover Size: 16 cm'
  self.assertEqual(content_text(text),'Handmade Crochet Fruit-Themed Glasses Cover Size: 16 cm')
  self.assertEqual(tokens(text),{'16'})
