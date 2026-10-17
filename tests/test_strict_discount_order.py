from pathlib import Path
import importlib.util
import subprocess
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
spec=importlib.util.spec_from_file_location('strict_order_main',ROOT/'main.py');main=importlib.util.module_from_spec(spec);spec.loader.exec_module(main)
import install_strict_discount_order as installer

class StrictOrderTests(unittest.TestCase):
    def test_all_35_discounted_ranked_before_any_blank_sale_even_variant_discount(self):
        discounted=[{'product_id':'d'+str(i),'source_url':'https://shop/products/d'+str(i),'base_price (PKR)':100,'sale_price (PKR, agar discount ho)':80,'description':'unchanged'} for i in range(35)]
        normal={'product_id':'bundle','source_url':'https://shop/products/bundle','base_price (PKR)':1490,'sale_price (PKR, agar discount ho)':None}
        rows=[normal]+discounted
        main._chotu_tls.ranking_evidence={h:{'url':'https://shop/collections/all?sort_by=best-selling','checked_at':'2026-10-17T00:00:00+00:00'} for h in ['d'+str(i) for i in range(35)]}
        ranked=main.prioritize_top_sellers(rows,['d'+str(i) for i in range(34,-1,-1)],{'bundle'})
        self.assertEqual(len(ranked),35)
        self.assertEqual([r['product_id'] for r in rows[:35]],['d'+str(i) for i in range(34,-1,-1)])
        self.assertIs(rows[-1],normal)
        self.assertTrue(all(main.genuine_discount(r) for r in rows[:35]))
    def test_ranking_walks_beyond_20_and_keeps_verified_prefix_on_failure(self):
        def response(handles):
            html='<select><option value="best-selling" selected>Best selling</option></select><ul id="product-grid">'+''.join('<a href="/products/'+h+'">Product</a>' for h in handles)+'</ul>'
            return SimpleNamespace(text=html,raise_for_status=lambda:None)
        all_handles=['d'+str(i) for i in range(35)]
        with patch.object(main.S,'get',side_effect=[response(all_handles[:20]),response(all_handles[20:])]),patch.object(main,'_chotu_backoff'):
            self.assertEqual(main.verified_top20('https://shop',lambda x:None,set(all_handles),rank_all=True),all_handles)
        logs=[]
        with patch.object(main.S,'get',side_effect=[response(all_handles[:20]),RuntimeError('source temporarily unavailable')]),patch.object(main,'_chotu_backoff'):
            self.assertEqual(main.verified_top20('https://shop',logs.append,set(all_handles),rank_all=True),all_handles[:20])
        self.assertTrue(any('UNVERIFIED' in line for line in logs))
    def test_installer_supports_previously_installed_versions_without_replacing_engine(self):
        for version in ['28f80c2','3293422']:
            original=subprocess.check_output(['git','-C',str(ROOT),'show',version+':main.py'])
            changed,count=installer.transform(original)
            self.assertGreater(count,0)
            self.assertIn(installer.MARKER,changed.decode())
            self.assertEqual(installer.transform(changed),(changed,0))
            self.assertIn('def refresh_variant_prices(',changed.decode())
            self.assertIn('def storefront_cover(',changed.decode())
