import unittest
from unittest.mock import patch
from bs4 import BeautifulSoup
from complete_description_support import collect_maali_plant_details
from hold804_repairs import category,description
from audit804_semantics import review
from sapphire_source_support import confirmed_unavailable_redirect,BASE
from types import SimpleNamespace
class PlantRecoveryTests(unittest.TestCase):
 def page(self):
  return BeautifulSoup('<link rel="canonical" href="https://hellomaali.com/products/coryphantha"><div class="maali-prod-wrapper-test"><h1>Coryphantha</h1><div class="maali-stats-test"><div><div>light</div><div>Bright light</div></div><div><div>water</div><div>Every 2–3 weeks</div></div><div><div>pet-safe</div><div>No</div></div></div></div>','html.parser')
 def test_product_care_is_identity_scoped_and_keeps_pet_warning(self):
  x=collect_maali_plant_details(self.page(),'Coryphantha','https://hellomaali.com/products/coryphantha')
  self.assertIn('Every 2–3 weeks',x);self.assertIn('pet-safe: No',x)
  self.assertEqual(collect_maali_plant_details(self.page(),'Other plant','https://hellomaali.com/products/coryphantha'),'')
  self.assertEqual(collect_maali_plant_details(self.page(),'Coryphantha','https://other.example/products/coryphantha'),'')
 def test_unknown_name_is_not_classified_from_store_alone(self):
  with patch('hold804_repairs.public_facts',return_value=None):self.assertIsNone(category({'name':'Unknown 123','description':''},'Hello Maali'))
 def test_bundle_keeps_set_identity_and_original_contents(self):
  row={'name':'Set of 3 Easy Care Indoor Plants','description':'China Palm, Snake Dwarf and Money Plant.'}
  with patch('hold804_repairs.public_facts',return_value={'product_type':'PLANTS'}):
   text,_=description(row,'Hello Maali');label=category(dict(row,description=text),'Hello Maali')[0]
  self.assertIn(row['description'],text);self.assertEqual(label,'Live Plant Sets');self.assertEqual(review(row['name'],text,label),[])
 def test_collection_product_undefined_redirect_is_recognized_without_guessing_stock(self):
  url=BASE+'/search?cgid=undefined';r=SimpleNamespace(status_code=200,url=url,text='<link rel="canonical" href="'+url+'">')
  self.assertTrue(confirmed_unavailable_redirect(r,BASE+'/collections/sale/products/3FELXS26V217.html'))
