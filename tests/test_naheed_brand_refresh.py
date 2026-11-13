import copy,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from naheed_brand_support import BASE,brand_key,load_request,vendor_link,select_brand_category,discover_brand_scope
from test_chotu_groceries import page

class NaheedBrandRefreshTests(unittest.TestCase):
 def test_generated_runtime_receives_brand_module_and_exact_request(self):
  import importlib.util
  from runtime import prepare_engine
  with tempfile.TemporaryDirectory() as tmp:
   engine=prepare_engine(tmp);module=engine.parent/'naheed_brand_support.py'
   spec=importlib.util.spec_from_file_location('isolated_brand_request',module);loaded=importlib.util.module_from_spec(spec);spec.loader.exec_module(loaded)
   self.assertEqual(loaded.load_request(),load_request())
 def test_saved_list_is_exact_and_contains_only_naheed_scope_urls(self):
  request=load_request();self.assertEqual(len(request['brands']),222)
  self.assertNotIn('unbranded',{brand_key(v['brand']) for v in request['brands']})
  self.assertIn('rose petal',{brand_key(v['brand']) for v in request['brands']})
  self.assertNotIn('rose patel',{brand_key(v['brand']) for v in request['brands']})
 def test_vendor_link_requires_matching_manufacturer_canonical_and_exact_host(self):
  html=page().replace('<a>Dawn</a>','<a href="/allproducts/?manufacturer=890">Dawn</a>')
  self.assertEqual(vendor_link(html,BASE+'/item','Dawn'),BASE+'/allproducts/?manufacturer=890')
  self.assertIsNone(vendor_link(html,BASE+'/item','Dawn Foods'))
  self.assertIsNone(vendor_link(html.replace('/allproducts/?manufacturer=890','https://evil.test/allproducts/?manufacturer=890'),BASE+'/item','Dawn'))
  self.assertIsNone(vendor_link(html,BASE+'/another','Dawn'))
 def test_matching_product_manufacturer_can_link_a_named_brand_landing_page(self):
  html=page().replace('<a>Dawn</a>','<a href="/sajiero-undergarments">Sajiero</a>')
  self.assertEqual(vendor_link(html,BASE+'/item','Sajiero'),BASE+'/sajiero-undergarments')
  self.assertIsNone(vendor_link(html,BASE+'/item','Another Brand'))
  self.assertIsNone(vendor_link(html.replace('/sajiero-undergarments','/checkout'),BASE+'/item','Sajiero'))
 def test_brand_match_is_not_a_title_or_partial_name_match(self):
  scope=dict(brand='Dawn',url=BASE+'/catalogsearch/result/?q=Dawn')
  p=dict(manufacturer='Dawn Foods',name='Dawn Bread',categories=[{'name':'Snacks'}])
  with self.assertRaises(ValueError):select_brand_category(p,[scope])
  p['manufacturer']='Dawn';self.assertEqual(select_brand_category(p,[scope]),(scope['url'],'Snacks'))
 def test_stale_vendor_count_uses_complete_brand_search_without_waiving_count(self):
  scope=dict(brand='Dawn',url=BASE+'/catalogsearch/result/?q=Dawn',examples=[BASE+'/item'])
  reader=SimpleNamespace(brand_proofs=[],scope_count_changed=False,scope_totals=[29],scope_partial=(set(),set()),scope_expected=29)
  reader.read_page=lambda _:page().replace('<a>Dawn</a>','<a href="/allproducts/?manufacturer=890">Dawn</a>')
  reader.discover_scope=lambda s:({BASE+'/item'},33,{s['url']}) if 'manufacturer=' in s['url'] else ({BASE+'/item'},1,{s['url']})
  links,total,_=discover_brand_scope(reader,scope)
  self.assertEqual(total,len(links));self.assertEqual(reader.brand_proofs[0]['selected'],'exact_brand_search')
  self.assertEqual(reader.brand_proofs[0]['vendor']['total'],33)
 def test_search_without_total_cannot_be_approved_as_complete(self):
  from grocery_browser_support import ListingRenderIncomplete
  scope=dict(brand='Dawn',url=BASE+'/catalogsearch/result/?q=Dawn',examples=[])
  reader=SimpleNamespace(brand_proofs=[],scope_count_changed=False,scope_totals=[],scope_partial=({BASE+'/item'},set()),scope_expected=None)
  reader.read_page=lambda _:page().replace('<a>Dawn</a>','<a>Another Brand</a>')
  reader.discover_scope=lambda s:({BASE+'/item'},None,{s['url']})
  with self.assertRaises(ListingRenderIncomplete):discover_brand_scope(reader,scope)
 def test_other_brand_search_hits_are_excluded_and_source_category_is_used(self):
  import chotu_groceries_source_support as source
  scope=dict(brand='Dawn',url=BASE+'/catalogsearch/result/?q=Dawn',group='Old heading')
  with tempfile.TemporaryDirectory() as tmp:
   reader=source.PublicCatalog({'__file__':str(Path(tmp)/'main.py'),'_chotu_wait':lambda:None},lambda _:None)
   reader.request={'pages':[scope]};reader.discover_scope=lambda _:({BASE+'/item',BASE+'/other'},2,{scope['url']})
   reader.read_page=lambda u:page() if u.endswith('/item') else page().replace('/item','/other').replace('182197','182198').replace('<a>Dawn</a>','<a>Another Brand</a>')
   with patch('locked_store_rules.record_incomplete_product') as receipt:products=reader.catalog()
   self.assertEqual(len(products),1);self.assertEqual(products[0]['manufacturer'],'Dawn');self.assertEqual(products[0]['owner_category'],'Snacks');self.assertEqual(reader.coverage_status,'complete');receipt.assert_called_once()
 def test_independent_audit_rejects_category_or_manufacturer_mutation(self):
  from grocery_owner_scope import authorized_category,audit
  row=dict(source_url=BASE+'/item',owner_scope_url=BASE+'/catalogsearch/result/?q=Dawn',source_manufacturer='Dawn',Category='Snacks',website_category_path='Groceries > Snacks',website_category_source_url=BASE+'/item',website_category_status='verified_product_breadcrumb',subcategory_source='owner_brand_search',source_scope_coverage_status='complete',source_scope_review_count=0)
  self.assertEqual(authorized_category(row),'Snacks');self.assertEqual(audit(row,row),[])
  self.assertTrue(audit(dict(row,source_manufacturer='Another Brand'),row));self.assertTrue(audit(dict(row,Category='Milk & Dairy'),row))
  with self.assertRaises(ValueError):authorized_category(dict(row,website_category_source_url='https://evil.test/item'))
