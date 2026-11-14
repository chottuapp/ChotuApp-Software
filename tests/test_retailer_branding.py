import unittest
from retailer_branding_support import customer_fields,issues

class RetailerBrandingTests(unittest.TestCase):
 def test_customer_fields_remove_brand_across_markup_but_preserve_product_facts(self):
  title='Fresh Chicken Boneless 1kg — Barkat Meat House';description='<p>From Barkat <b>Meat</b> House</p><p>Chicken breast, 500g. Keep at -18°C. Use within 6 months.</p>'
  row=customer_fields('https://barkatmeathouse.com/product/1',title,description)
  self.assertEqual(row['name'],'Fresh Chicken Boneless 1kg');self.assertIn('500g',row['description']);self.assertIn('-18°C',row['description']);self.assertIn('6 months',row['description']);self.assertEqual(row['original_source_description'],description)
  self.assertEqual(issues(dict(row,source_url='https://barkatmeathouse.com/product/1')),[])
 def test_independent_lock_catches_case_spacing_and_domain_branding(self):
  for value in ('BARKAT MEAT HOUSE','BarkatMeatHouse','barkat-meat-house','https://barkatmeathouse.com'):
   self.assertTrue(issues(dict(source_url='https://www.barkatmeathouse.com/item',name='Chicken',description=value)))
 def test_other_hosts_and_source_links_are_not_rewritten(self):
  row=customer_fields('https://another.test/item','Barkat Meat House','Original source')
  self.assertEqual(row['name'],'Barkat Meat House')
