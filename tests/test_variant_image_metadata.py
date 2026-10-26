import unittest
from openpyxl import Workbook
from test_product_stock_images import main
class ImageMetadataTests(unittest.TestCase):
 def test_fallback_is_explicit_and_does_not_fabricate_variant_association(self):
  p={'images':[{'src':'https://shop.example/general.jpg'}]};v={'id':1,'available':False}
  image=main.variant_image_url(p,v);self.assertEqual(image,'')
  result=main.variant_image_metadata(image,'https://shop.example/general.jpg')
  self.assertEqual(result['variant_image_status'],'product_photo_fallback')
  self.assertEqual(result['fallback_image_url'],'https://shop.example/general.jpg')
  self.assertEqual(v,{'id':1,'available':False})
 def test_exact_variant_image_uses_source_link_not_generic_cover(self):
  p={'images':[]};v={'id':1,'featured_image':{'src':'//cdn.example/black.jpg'}}
  image=main.variant_image_url(p,v);self.assertEqual(image,'https://cdn.example/black.jpg')
  self.assertEqual(main.variant_image_metadata(image,'https://shop.example/general.jpg')['fallback_image_url'],'')
 def test_missing_images_never_change_stock(self):
  self.assertEqual(main.variant_image_metadata('','')['variant_image_status'],'unavailable')
  self.assertEqual(main.variant_image_metadata('javascript:alert(1)','')['fallback_image_url'],'')
 def test_old_template_additive_headers_are_idempotent(self):
  b=Workbook();s=b.active;s.append(['variant_image_url','available (yes/no)'])
  main.ensure_variant_image_fields(s);main.ensure_variant_image_fields(s)
  self.assertEqual([c.value for c in s[1]],['variant_image_url','available (yes/no)',*main.VARIANT_IMAGE_FIELDS])

 def test_audit_rejects_wrong_product_cover_and_false_specific_image(self):
  from price_stock_gate import image_metadata_issues
  product={'final_image_url (main photo)':'https://shop.example/one.jpg'}
  row={'variant_image_url':'','variant_image_status':'product_photo_fallback','fallback_image_url':'https://shop.example/one.jpg'}
  self.assertEqual(image_metadata_issues(row,product),[])
  self.assertTrue(image_metadata_issues(dict(row,fallback_image_url='https://shop.example/other-product.jpg'),product))
  self.assertTrue(image_metadata_issues(dict(row,variant_image_status='source_linked'),product))
