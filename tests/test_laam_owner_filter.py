import copy,json,unittest
from pathlib import Path
from laam_source_support import normalize,HiddenProduct,ConfirmedOutOfStock
class OwnerFilterTests(unittest.TestCase):
 def fixture(self):return json.loads((Path(__file__).parent/'fixtures/laam_public_product_0085.json').read_text())
 def test_only_instock_source_variants_retained(self):
  raw=self.fixture();p=normalize(raw,raw['handle'],active_only=True,in_stock_only=True);self.assertEqual(len(p['variants']),1);self.assertTrue(all(v['available'] for v in p['variants']))
  selected=[v for v in raw['variants'] if v['stock_status'] in ('in-stock','limited-stock')];self.assertEqual(p['variants'][0]['price'],selected[0]['price'])
 def test_hidden_draft_archived_excluded(self):
  for changes in ({'status':'draft'},{'status':'archived'},{'hidden':True},{'is_visible':False},{'published':False},{'visibility':'unlisted'},{'visibility':'private'}):
   raw=self.fixture();raw.update(changes)
   with self.assertRaises(HiddenProduct):normalize(raw,raw['handle'],active_only=True,in_stock_only=True)
 def test_all_outofstock_excluded(self):
  raw=self.fixture()
  for v in raw['variants']:v['stock_status']='sold-out';v['inventory_quantity']=0
  with self.assertRaises(ConfirmedOutOfStock):normalize(raw,raw['handle'],active_only=True,in_stock_only=True)
