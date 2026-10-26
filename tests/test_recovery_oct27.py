import unittest
from types import SimpleNamespace
from hold804_repairs import category
from audit804_semantics import review
from sapphire_source_support import confirmed_unavailable_redirect,BASE
class RecoveryTests(unittest.TestCase):
 def test_primary_garment_outranks_styling_companion(self):
  for title,body,label in [('Women Tank Tops','Pair this tank top with high-waisted trousers.','Tank Tops'),('Skirt fit Jeans','Skirt fit Women Jeans; cotton elastane.','Jeans')]:
   self.assertEqual(category({'name':title,'description':body},'Gul Ahmed')[0],label)
   self.assertEqual(review(title,body,label),[])
 def test_specific_household_purpose_and_companion_contents(self):
  for title,body,label in [('Mattress Topper 26','100% Polyester','Mattress Toppers'),('Aurora Red Jacquard Bed Spread','2 Pillow Cases, 2 Cushion Covers','Bedspread Sets'),('Lapis Terry Turban','Wrap the hair after washing.','Hair Towels'),('Quilted Mat','Padded cushioning for exercise','Quilted Multipurpose Mats'),('Georgette Embellished Inner','Layers well under abayas.','Abaya Inners')]:
   self.assertEqual(category({'name':title,'description':body},'Gul Ahmed')[0],label)
   self.assertEqual(review(title,body,label),[])
 def test_undefined_category_redirect_is_not_arbitrary_missing_price_skip(self):
  landing=BASE+'/search?cgid=undefined';html='<link rel="canonical" href="'+landing+'">'
  r=SimpleNamespace(status_code=200,url=landing,text=html);requested=BASE+'/products/PRW2SCSTV819_999.html'
  self.assertTrue(confirmed_unavailable_redirect(r,requested))
  for url,body in [(BASE+'/search?cgid=valid',html),(BASE+'/products/X.html',html),(landing,html+'<div class="product-wrapper" data-pid="X"></div>')]:
   self.assertFalse(confirmed_unavailable_redirect(SimpleNamespace(status_code=200,url=url,text=body),requested))
