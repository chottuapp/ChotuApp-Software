import unittest,tempfile
from pathlib import Path
from openpyxl import Workbook
from price_stock_gate import check,workbook_issues
class PriceStockTests(unittest.TestCase):
 def row(self,**extra):return dict({'product_id':'P1','base_price (PKR)':100,'sale_price (PKR, agar discount ho)':80,'available (yes/no)':'yes'},**extra)
 def test_exact_decimal_prices_and_unknown_quantity_are_preserved(self):
  row=self.row(**{'base_price (PKR)':'100.25','sale_price (PKR, agar discount ho)':'80.10'});before=row.copy();self.assertEqual(check(row),[]);self.assertEqual(row,before)
 def test_invalid_prices_and_discounts_fail(self):
  for change in [{'base_price (PKR)':0},{'base_price (PKR)':'NaN'},{'sale_price (PKR, agar discount ho)':101},{'sale_price (PKR, agar discount ho)':-1},{'sale_price (PKR, only if discounted)':70}]:self.assertTrue(check(self.row(**change)))
 def test_zero_price_allowed_only_for_exact_verified_unavailable_variant(self):
  from unittest.mock import patch
  identity=('Store','P1','https://example.com/products/item','123','sku')
  product=self.row(source_url=identity[2],source_variant_id='124',sku='product')
  zero=dict(product,source_variant_id='123',sku='sku',**{'base_price (PKR)':0,'available (yes/no)':'no','sale_price (PKR, agar discount ho)':None})
  with tempfile.TemporaryDirectory() as tmp,patch('price_stock_gate.unpriced_variant_evidence',return_value={identity}):
   path=Path(tmp)/'verified.xlsx';book=Workbook();sheet=book.active;sheet.title='Products';sheet.append(list(product));sheet.append(list(product.values()))
   variety=book.create_sheet('Variant Combinations');variety.append(list(product));variety.append(list(product.values()));variety.append(list(zero.values()));book.save(path)
   self.assertEqual(workbook_issues(path,store='Store'),{})
   self.assertIn('P1',workbook_issues(path,store='Other Store'))
   variety.cell(3,list(product).index('available (yes/no)')+1,'yes');book.save(path)
   self.assertIn('P1',workbook_issues(path,store='Store'))

 def test_unknown_and_conflicting_stock_fail_without_becoming_in_stock(self):
  for change in [{'available (yes/no)':''},{'stock_quantity (agar public ho)':0},{'stock_quantity (agar public ho)':-1}]:self.assertTrue(check(self.row(**change)))
  self.assertEqual(check(self.row(**{'available (yes/no)':'no','stock_quantity (agar public ho)':0})),[])
 def test_mixed_variant_stock_product_remains_available(self):
  with tempfile.TemporaryDirectory() as tmp:
   path=Path(tmp)/'x.xlsx';book=Workbook();sheet=book.active;sheet.title='Products';headers=list(self.row());sheet.append(headers);sheet.append(list(self.row().values()));variants=book.create_sheet('Variant Combinations');variants.append(headers);variants.append(list(self.row(**{'available (yes/no)':'no'}).values()));variants.append(list(self.row().values()));book.save(path)
   self.assertEqual(workbook_issues(path),{})
   sheet.cell(2,headers.index('available (yes/no)')+1).value='no';book.save(path);self.assertIn('product and variant availability disagree',' '.join(workbook_issues(path)['P1']))

 def test_fully_sold_out_product_is_rejected_but_unavailable_variants_are_retained(self):
  with tempfile.TemporaryDirectory() as tmp:
   path=Path(tmp)/'soldout.xlsx';book=Workbook();products=book.active;products.title='Products';headers=list(self.row());products.append(headers);products.append(list(self.row(**{'available (yes/no)':'no'}).values()));variants=book.create_sheet('Variant Combinations');variants.append(headers);variants.append(list(self.row(**{'available (yes/no)':'no'}).values()));book.save(path)
   self.assertIn('fully out-of-stock',' '.join(workbook_issues(path)['P1']))
   products.cell(2,headers.index('available (yes/no)')+1).value='yes';variants.append(list(self.row().values()));book.save(path);self.assertEqual(workbook_issues(path),{})
