import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest
from bs4 import BeautifulSoup
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import complete_description_support as details
import install_complete_descriptions as installer
import main
ROOT=Path(__file__).resolve().parents[1]

class DescriptionTests(unittest.TestCase):
    def test_non_electronic_ingredients_usage_and_cautions_not_cut(self):
        p={'title':'Food Mix','body_html':'<p>'+('Product information. '*40)+'</p><h3>Ingredients</h3><p>Salt, cumin and coriander.</p><h3>Directions</h3><p>Use 10 g per 500 g serving.</p><h3>Allergen Information</h3><p>Contains wheat.</p><h3>Storage</h3><p>Store below 25 C.</p>'}
        result=main.friendly_description(p)
        self.assertGreater(len(result),300)
        for expected in ('Salt, cumin and coriander.','10 g per 500 g','Contains wheat.','Store below 25 C.'):self.assertIn(expected,result)
    def test_product_scoped_accordions_include_care_but_not_other_products(self):
        page=BeautifulSoup('''<product-info><details><summary>Usage</summary><div class="accordion__content"><p>Apply twice daily.</p></div></details><details><summary>Care Instructions</summary><div class="accordion__content">Hand wash only.</div></details><details><summary>Shipping</summary><div class="accordion__content">Shipping fee 999</div></details><div class="product-specifications"><table><tr><th>Capacity</th><td>250 ml</td></tr></table></div></product-info><product-recommendations><div class="product__description">Another product 999 W</div></product-recommendations><div class="accordion__content">Global footer 99</div>''','html.parser')
        collected=details.collect_product_details(page)
        for expected in ('Apply twice daily.','Hand wash only.','250 ml','Care Instructions'):self.assertIn(expected,collected)
        for unwanted in ('999 W','fee 999','Global footer'):self.assertNotIn(unwanted,collected)
        result=main.friendly_description({'title':'Bottle','body_html':'<p>Original details.</p>','_storefront_specs_html':collected})
        self.assertIn('Original details.',result);self.assertIn('Capacity: 250 ml',result)
    def test_observed_options_included_without_adding_prices_or_mutating(self):
        import copy
        p={'title':'Product','body_html':'<p>Actual description.</p>','options':[{'name':'Size'}],'variants':[{'option1':'S','price':'12.34','available':True},{'option1':'M','price':'15.00','available':False}]};old=copy.deepcopy(p)
        result=main.friendly_description(p);self.assertIn('Size: S, M',result);self.assertNotIn('12.34',result);self.assertEqual(p,old)
    def test_installer_only_changes_description_paths_and_preserves_user_data(self):
        import subprocess
        legacy=subprocess.check_output(['git','show','HEAD:main.py'],cwd=ROOT,text=True)
        updated=installer.transform(legacy);self.assertEqual(installer.transform(updated),updated)
        before=__import__('ast').parse(legacy);after=__import__('ast').parse(updated)
        for name in ('get_json','refresh_variant_prices','discover','collections','prioritize_top_sellers','finalize_catalog_order'):
            def body(tree):return __import__('ast').dump(next(n for n in tree.body if getattr(n,'name',None)==name),include_attributes=False)
            self.assertEqual(body(before),body(after))
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);(p/'main.py').write_text(legacy);(p/'saved.sqlite3').write_bytes(b'keep');installer.install(p)
            self.assertEqual((p/'saved.sqlite3').read_bytes(),b'keep');self.assertEqual(next((p/'backups').glob('*/main.py')).read_text(),legacy)
