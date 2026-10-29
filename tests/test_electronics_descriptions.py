import re,unittest
from bs4 import BeautifulSoup
from electronics_description_support import html_text,warranty_months,warranty_panels,format_electronics
from description_readability import issues

class ElectronicsDescriptions(unittest.TestCase):
 def test_flattened_features_preserve_units_and_warranty(self):
  source='Slim phone case. Ultra-Slim Thickness: Approximately 1.05 mm (±0.2 mm). Feather-Light Weight: 21.8 g (±2 g). Warranty: 1 year official warranty.\nDimensions: N/A'
  after=format_electronics(source)
  self.assertIn('Specifications\n',after);self.assertIn('Warranty\n',after)
  self.assertNotIn('N/A',after)
  self.assertEqual(re.findall(r'\d+(?:[.,]\d+)?',source),re.findall(r'\d+(?:[.,]\d+)?',after))
 def test_warranty_is_not_inferred_from_returns_or_conflicting_terms(self):
  for text in ('7 day returns','Lifetime warranty','No warranty','1 year warranty; 6 months seller warranty'):
   self.assertEqual(warranty_months(text),'')
  self.assertEqual(warranty_months('1-Year Official Warranty'),12)
  self.assertEqual(warranty_months('Warranty: 18 months'),18)
 def test_source_html_keeps_blocks_but_inline_brand_text_together(self):
  self.assertEqual(html_text('<p>USB <b>Type-C</b> cable.</p><ul><li>Length: 1.5m</li><li>Warranty: 6 months</li></ul>'),'USB Type-C cable.\nLength: 1.5m\nWarranty: 6 months')
 def test_only_product_scoped_warranty_is_harvested(self):
  soup=BeautifulSoup('<footer>All products 5 years warranty</footer><div class="woocommerce-Tabs-panel"><h2>Warranty</h2><p>1 year limited seller warranty. Excludes liquid damage.</p></div>','html.parser')
  result=warranty_panels(soup);self.assertIn('Excludes liquid damage',result);self.assertNotIn('5 years',result)
 def test_metadata_newline_cannot_mask_dense_paragraph(self):
  source=' '.join(['A speaker has 2 drivers and USB charging.']*20)+'\nWeight: 1kg'
  self.assertTrue(issues(source));self.assertFalse(issues(format_electronics(source)))
 def test_negative_operating_temperature_is_preserved(self):
  self.assertIn('-10°C',format_electronics('-10°C operating temperature.\nWarranty: None.'))
