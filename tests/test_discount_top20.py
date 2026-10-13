import importlib.util
from pathlib import Path
import sys
import unittest
from urllib.parse import urlparse
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import install_discount_top20 as patch

class DiscountRankingTests(unittest.TestCase):
    def test_discount_filter_and_order_preserve_remaining_products(self):
        source=(ROOT/'main.py').read_text()
        block=source[source.index('    discount_handles = '):source.index('    safe_name = ',source.index('    discount_handles = '))]
        rows=[{'source_url':'https://shop/products/'+h,'base_price (PKR)':base,'sale_price (PKR, agar discount ho)':sale} for h,base,sale in [('full',100,None),('equal',100,100),('higher',100,120),('cheap',100,50),('free-sale',100,0)]]
        observed=[]
        def verified(base,log,eligible):
            observed.append(eligible)
            return [h for h in ['full','free-sale','cheap'] if h in eligible]
        scope=dict(rows=rows,money=lambda x:float(x) if x is not None else None,urlparse=urlparse,verified_top20=verified,base='https://shop',log=lambda x:None)
        exec('\n'.join(line[4:] for line in block.splitlines()),scope)
        self.assertEqual(observed,[{'cheap','free-sale'}])
        self.assertEqual(scope['top_handles'],['free-sale','cheap'])

    def test_patch_preserves_saved_run_hook_and_speed_and_is_idempotent(self):
        source=(ROOT/'main.py').read_text()
        for old,new in patch.REPLACEMENTS:source=source.replace(new,old,1)
        source+="\n# saved-run hook stays\n# adaptive_pace 0.35\n"
        updated,count=patch.transform(source.encode())
        self.assertEqual(count,2)
        expected=source
        for old,new in patch.REPLACEMENTS:expected=expected.replace(old,new,1)
        self.assertEqual(updated.decode(),expected)
        self.assertEqual(patch.transform(updated),(updated,0))
