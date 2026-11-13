import copy,json,unittest
from pathlib import Path
from bs4 import BeautifulSoup
import laam_source_support as source
from test_laam_source import html

class PriceScopeDiscoveryTests(unittest.TestCase):
 def setUp(self):
  self.raw=json.loads((Path(__file__).parent/'fixtures/laam_outside_price_options.json').read_text())
 def parse(self,raw):
  return source.product_state(BeautifulSoup(html(raw),'html.parser'),raw['handle'],owner_price_scope=True)
 def test_exact_outside_scope_product_cannot_block_catalog_on_unused_options(self):
  before=copy.deepcopy(self.raw)
  with self.assertRaises(source.OutsidePriceScope) as caught:self.parse(self.raw)
  self.assertEqual(caught.exception.raw,before);self.assertEqual(self.raw,before)
 def test_in_range_option_conflict_stays_blocked(self):
  raw=copy.deepcopy(self.raw)
  for v in raw['variants']:v['price']='6500'
  with self.assertRaisesRegex(ValueError,'observed variant') as caught:self.parse(raw)
  self.assertNotIsInstance(caught.exception,source.OutsidePriceScope)
 def test_unknown_stock_cannot_be_used_to_exclude_an_unverified_product(self):
  raw=copy.deepcopy(self.raw);raw['variants'][0]['stock_status']='unknown'
  with self.assertRaises(ValueError) as caught:self.parse(raw)
  self.assertNotIsInstance(caught.exception,source.OutsidePriceScope)
