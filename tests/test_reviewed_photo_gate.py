import hashlib,unittest
from unittest.mock import patch
from audit804 import reviewed_photo_purpose,issues_for

class ReviewedPhotoGate(unittest.TestCase):
 def fixture(self):
  source={'product_id':'CP-test','name':'Opaque model','source_url':'https://shop.example/products/a','description':'Original details: 20 cm.','scraped_image_url (cover, auto)':'https://cdn.example/a.jpg'}
  fact={'product_id':source['product_id'],'name':source['name'],'source_url':source['source_url'],'category':'Reviewed Object','overview':'The inspected product is an object.','image_url':source['scraped_image_url (cover, auto)'],'image_sha256':'a'*64,'input_description_sha256':hashlib.sha256(source['description'].encode()).hexdigest(),'reviewed_utc':'2026-10-29T13:00:00+00:00','scope':'Source product photo inspected.'}
  row=dict(source,Category=fact['category'],description=fact['overview']+'\n\n'+source['description'])
  return source,fact,row
 def test_image_evidence_requires_original_identity_body_and_cover(self):
  source,fact,row=self.fixture()
  with patch('review_evidence_cache.read_review_evidence',return_value={'products':[fact]}):
   self.assertTrue(reviewed_photo_purpose(row,source))
   self.assertFalse(reviewed_photo_purpose(row,None))
   for key,value in [('description','Changed source'),('source_url','https://shop.example/products/b'),('scraped_image_url (cover, auto)','https://cdn.example/other.jpg')]:
    self.assertFalse(reviewed_photo_purpose(row,dict(source,**{key:value})))
   self.assertFalse(reviewed_photo_purpose(dict(row,Category='Different object'),source))
 def test_image_purpose_cannot_override_explicit_piece_count_conflict(self):
  source,fact,row=self.fixture();source.update(name='1 Piece Printed Shirt',description='A black 2-piece stitched suit.');fact.update(name=source['name'],category='Shirts',overview='A shirt.',input_description_sha256=hashlib.sha256(source['description'].encode()).hexdigest());row=dict(source,Category='Shirts',description=fact['overview']+'\n\n'+source['description'])
  with patch('review_evidence_cache.read_review_evidence',return_value={'products':[fact]}):
   self.assertIn('Complete outfit classified as one component',issues_for(row,source))
 def test_quantity_correction_is_exact_and_retains_all_other_specs(self):
  import json
  from pathlib import Path
  doc=json.loads((Path(__file__).resolve().parents[1]/'cloud/audit804-image-reviews.json').read_text())
  fact=next(x for x in doc['products'] if x.get('source_url')=='https://www.beyondeast.com/products/wtse361039' and x.get('replace_wrong_product_body'))
  self.assertEqual(fact['confirmed_public_title'],'1 Piece Embroidered Lawn Shirt')
  self.assertIn('WTSE361039',fact['overview']);self.assertIn('Fabric: Lawn',fact['overview']);self.assertIn('XS, S, M, L, XL',fact['overview']);self.assertNotIn('2-piece',fact['overview'])
