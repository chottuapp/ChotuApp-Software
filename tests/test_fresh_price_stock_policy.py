import importlib.util,unittest
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch
root=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('fresh_price_policy',root/'main.py');main=importlib.util.module_from_spec(spec);spec.loader.exec_module(main)
class FreshPricePolicyTests(unittest.TestCase):
 def test_failed_live_price_never_falls_back_to_cached_price(self):
  product={'id':1,'handle':'item','variants':[{'id':4,'price':'100','available':True}]}
  with patch.object(main,'refresh_variant_prices',side_effect=RuntimeError('HTTP 503')),patch.object(main,'confirmed_removed_product',return_value=False):
   with self.assertRaisesRegex(RuntimeError,'cached prices not exported'):main.verified_sellable_variants('https://example.com',product,lambda _:None)
  self.assertEqual(product['variants'][0]['price'],'100')
 def test_restocked_product_uses_current_price_and_stock(self):
  product={'id':1,'handle':'item','variants':[{'id':4,'price':'100','available':False}]};live=[{'id':4,'price':'125.50','available':True,'inventory_quantity':3}]
  with patch.object(main,'refresh_variant_prices',return_value=live):
   variants,available=main.verified_sellable_variants('https://example.com',product,lambda _:None)
  self.assertEqual(available,live);self.assertEqual(variants[0]['price'],'125.50')
 def test_live_sold_out_is_excluded_without_invented_inventory(self):
  live=[{'id':4,'price':'125','available':False,'inventory_quantity':0}]
  with patch.object(main,'refresh_variant_prices',return_value=live):
   variants,available=main.verified_sellable_variants('https://example.com',{'handle':'x'},lambda _:None)
  self.assertEqual(available,[]);self.assertEqual(variants[0]['inventory_quantity'],0)
 def test_only_source_confirmed_removed_product_can_be_skipped_after_price_failure(self):
  with patch.object(main,'refresh_variant_prices',side_effect=RuntimeError('HTTP 404')),patch.object(main,'confirmed_removed_product',return_value=True):
   self.assertIsNone(main.verified_sellable_variants('https://example.com',{'handle':'removed'},lambda _:None))
