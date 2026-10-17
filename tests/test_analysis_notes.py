import unittest
from unittest.mock import patch
from bs4 import BeautifulSoup
import main
from ranking_support import order_rows, product_page_evidence, collection_evidence

class AnalysisNoteTests(unittest.TestCase):
    def row(self):return {'product_id':'p','category':'Lipstick','source_url':'https://shop/products/p','base_price (PKR)':100}
    def test_every_product_gets_unknown_note_without_invented_rank(self):
        row=self.row();order_rows([row]);self.assertIn('No verified bestseller-order evidence',row['analysis_note']);self.assertIn('not proof of low sales',row['analysis_note']);self.assertIsNone(row.get('product_priority'));self.assertIsNone(row.get('popularity_basis'))
    def test_verified_sort_note_has_url_time_and_scope_and_is_idempotent(self):
        row=self.row();facts={'p':{'url':'https://shop/collections/all?sort_by=best-selling&page=1','checked_at':'2026-10-17T00:00:00+00:00'}}
        order_rows([row],['p'],facts);note=row['analysis_note'];self.assertIn('Verified position 1',note);self.assertIn(facts['p']['url'],note);self.assertIn(facts['p']['checked_at'],note);self.assertIn('not independently verified sales volume',note)
        order_rows([row]);self.assertEqual(note,row['analysis_note'])
    def test_collection_name_signal_never_assigns_verified_popularity(self):
        row=self.row();row['analysis_note']=collection_evidence('Top Collections','https://shop/collections/top','https://shop/collections/top/products.json?page=1');order_rows([row]);self.assertIn('Top Collections',row['analysis_note']);self.assertIn('merchant signal only',row['analysis_note']);self.assertIsNone(row.get('popularity_basis'));self.assertEqual(collection_evidence('Summer Sale','https://shop/sale','https://shop/sale.json'),'')
    def test_badges_scoped_to_product_not_navigation_or_recommendations(self):
        html='<nav><span class="badge">Bestseller</span></nav><aside><span class="badge">Trending</span></aside><div class="product__info"><span class="badge">30% Off</span><span class="badge">Top Selling</span></div>'
        note=product_page_evidence(BeautifulSoup(html,'html.parser'),'https://shop/products/p');self.assertIn('Top Selling',note);self.assertNotIn('Trending',note);self.assertNotIn('30%',note);self.assertIn('not an independently verified sales count',note)
        self.assertEqual(product_page_evidence(BeautifulSoup('<nav><span class="badge">Bestseller</span></nav>','html.parser'),'https://shop/products/p'),'')
    def test_collection_membership_only_attaches_to_products_in_response(self):
        responses=[{'collections':[{'handle':'top','title':'Top Collections'},{'handle':'plain','title':'Plain'}]},{'products':[{'id':1}]},{'products':[{'id':2}]}]
        with patch.object(main,'get_json',side_effect=responses),patch.object(main,'_chotu_wait'):
            mapped=main.collections('https://shop',lambda _:None)
        self.assertEqual(mapped,{1:['Top Collections'],2:['Plain']});notes=main._chotu_tls.collection_popularity_evidence;self.assertIn('products.json?limit=250&page=1',notes[1][0]);self.assertNotIn(2,notes)
    def test_existing_human_and_label_notes_preserved(self):
        row=self.row();row['analysis_note']='Manual review: confirm material.\nMerchant label: Featured.';order_rows([row]);self.assertTrue(row['analysis_note'].startswith('Manual review: confirm material.'));before=row['analysis_note'];order_rows([row]);self.assertEqual(row['analysis_note'],before)
