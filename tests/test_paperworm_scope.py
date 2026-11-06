import tempfile,unittest
from pathlib import Path
from openpyxl import load_workbook
from locked_store_rules import allowed_product,paperworm_school_supply
from owner_product_exclusions import apply
import test_incomplete_products as fixtures

class PaperWormScopeTests(unittest.TestCase):
 def test_school_goods_allowed_without_mutating_source(self):
  for title in ('School Bag','Unicorn Backpack','Lunch Box','Bento Box','Water Bottle','Pencil Pouch','Exercise Book','Colour Pencils','Geometry Box','Crayons','Sketch Book','School Glue','Scissors'):
   p=dict(title=title,variants=[dict(price='456.75',available=True)])
   self.assertTrue(allowed_product('https://www.thepaperworm.com/',p),title)
   self.assertEqual(p['variants'][0]['price'],'456.75')
 def test_unrelated_and_uncertain_goods_not_rescued_by_school_seo(self):
  for title in ('Party Balloons','Gift Bag','Candle','Plush Doll','Travel Bag','Laptop Bag','Baby Feeding Bottle','Toner Cartridge','Mystery Item'):
   p=dict(title=title,body_html='Great for school, lunch box, stationery',tags='school')
   self.assertFalse(allowed_product('https://thepaperworm.com/',p),title)
  self.assertTrue(allowed_product('https://another-store.test/',dict(title='Party Balloons')))
 def test_explicit_taxonomy_can_identify_an_opaque_named_school_item(self):
  self.assertTrue(paperworm_school_supply(dict(title='Astronaut 123',product_type='School Bags')))
  self.assertFalse(paperworm_school_supply(dict(title='Party Decoration',product_type='School Supplies')))
 def test_saved_export_removes_linked_rows_and_preserves_original(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);source=root/'source.xlsx';fixtures.IncompleteProductsTests().workbook(source)
   book=load_workbook(source);p=book['Products'];p['B2']='Party Balloons';p['B3']='School Bag';book.save(source);book.close();before=source.read_bytes()
   out,receipt=apply(source,root/'filtered.xlsx','The Paper Worm')
   self.assertEqual(source.read_bytes(),before);self.assertEqual([r['product_id'] for r in receipt],['bad']);self.assertIn('school-supplies',receipt[0]['reason'])
   b=load_workbook(out);rows=lambda name:[r for r in b[name].iter_rows(min_row=2,values_only=True) if r[0] is not None]
   self.assertEqual(rows('Products')[0][0],'good');self.assertEqual(rows('Products')[0][-1],456.75)
   self.assertEqual(rows('Variant Combinations')[0][0],'good');self.assertEqual(rows('Option Groups'), [('shared',)]);b.close()
