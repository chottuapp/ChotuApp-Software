import tempfile
import unittest
from pathlib import Path
from openpyxl import Workbook, load_workbook
from locked_store_rules import allowed_product, freshbasket_produce
from owner_product_exclusions import apply


class FreshBasketOwnerRuleTests(unittest.TestCase):
 def test_produce_excluded_from_fresh_fetch_only_for_fresh_basket(self):
  for product in [dict(title='Apple Golden 1kg'),dict(title='Aloo 1kg'),dict(title='Frozen Peas'),dict(title='Imported seasonal selection',product_type='Fresh Fruits'),dict(name='Seasonal box',categories=[dict(name='Vegetables')])]:
   with self.subTest(product=product):
    self.assertFalse(allowed_product('https://www.freshbasket.com.pk',product))
    self.assertTrue(allowed_product('https://other.example',product))
 def test_prepared_food_and_unrelated_goods_remain_allowed(self):
  for title in ['Anmol Strawberry Greek Yogurt 500g','Apple Juice','Mango Jam','Potato Chips','Tomato Ketchup','Milk','Rice','Coconut Oil','Mixed Pickle']:
   self.assertTrue(allowed_product('https://freshbasket.com.pk',dict(title=title)),title)
  self.assertFalse(freshbasket_produce(dict(title='Milk',description='Serve with fresh fruits and vegetables')))
 def test_saved_workbook_removes_produce_and_linked_rows_preserving_original(self):
  with tempfile.TemporaryDirectory() as tmp:
   source=Path(tmp)/'source.xlsx';out=Path(tmp)/'out.xlsx';book=Workbook();sheet=book.active;sheet.title='Products'
   sheet.append(['product_id','name','Category','source_url','scraped_image_url (auto)','base_price (PKR)'])
   sheet.append(['fruit','Apple Golden','Fruits','https://freshbasket.com.pk/products/apple','https://freshbasket.com.pk/apple.jpg',100])
   sheet.append(['dairy','Strawberry Yogurt','Dairy','https://freshbasket.com.pk/products/yogurt','https://freshbasket.com.pk/yogurt.jpg',250])
   for title in ['Product Images','Variant Combinations']:
    s=book.create_sheet(title);s.append(['product_id','group_ids']);s.append(['fruit','fruit-options']);s.append(['dairy','dairy-options'])
   for title in ['Option Groups','Options']:
    s=book.create_sheet(title);s.append(['group_id']);s.append(['fruit-options']);s.append(['dairy-options'])
   book.save(source);book.close();before=source.read_bytes()
   result,changes=apply(source,out,'Fresh Basket');self.assertEqual(source.read_bytes(),before)
   self.assertEqual([r['product_id'] for r in changes],['fruit']);self.assertIn('fruits and vegetables',changes[0]['reason'])
   book=load_workbook(result)
   for title in ['Products','Product Images','Variant Combinations']:
    self.assertEqual([r[0] for r in book[title].iter_rows(min_row=2,values_only=True) if r[0]],['dairy'])
   for title in ['Option Groups','Options']:
    self.assertEqual([r[0] for r in book[title].iter_rows(min_row=2,values_only=True) if r[0]],['dairy-options'])
   book.close()
