import copy,sys,unittest,json
from pathlib import Path
from types import SimpleNamespace
from bs4 import BeautifulSoup
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import website_category_support as cat
import website_order_support as order
BASE='https://store.example'
class StrictCategoryTests(unittest.TestCase):
 def test_named_campaign_sale_is_not_product_taxonomy(self):
  self.assertFalse(cat.substantive('Wedding Season Sale'));self.assertFalse(cat.substantive('10 10 Sale 2026'));self.assertTrue(cat.substantive('LITTLE GIRLS (1-6Y)'))
  html='<nav class="breadcrumb"><a href="/">Home</a><a href="/collections/10-10-sale">10 10 Sale 2026</a></nav>'
  self.assertIsNone(cat.breadcrumb(BeautifulSoup(html,'html.parser'),BASE+'/products/x'))
 def test_title_guesses_and_sale_membership_never_become_categories(self):
  row={'source_url':BASE+'/products/x','category':'Foundation','subcategory':'Guessed','name':'Foundation','base_price (PKR)':100}
  order.apply_order([row],{'x':dict(category='SALE',subcategory='',category_order=1,subcategory_order=1,product_order=1,source_url=BASE+'/collections/sale',checked_at='2026-10-18T00:00:00Z')})
  self.assertEqual(row['category'],'');self.assertEqual(row['website_category_status'],'unverified');self.assertEqual(row['website_order_status'],'observed_default_listing');self.assertEqual(row['base_price (PKR)'],100)
 def test_exact_menu_case_and_deep_path_with_api_membership(self):
  tls=SimpleNamespace(website_category_navigation=[{'category':'MAKEUP','subcategory':'Face / Base','category_path':['MAKEUP','Face / Base'],'url':BASE+'/collections/base'}])
  calls=[]
  def get(url):calls.append(url);return {'products':[{'id':1,'handle':'actual'}]}
  mapping=cat.navigation_membership(tls,BASE,get,lambda:None,lambda _:None)
  self.assertEqual(mapping,{1:['Face / Base']});row={'source_url':BASE+'/products/actual','category':'wrong'};cat.apply(row,tls.website_category_evidence)
  self.assertEqual((row['category'],row['subcategory']),('MAKEUP','Face / Base'));self.assertEqual(row['website_category_status'],'verified_navigation_membership');self.assertIn('products.json',row['website_category_source_url']);self.assertEqual(len(calls),1)
 def test_promo_collections_skipped_and_deeper_membership_wins(self):
  tls=SimpleNamespace(website_category_navigation=[{'category':label,'subcategory':sub,'url':BASE+'/collections/'+handle} for label,sub,handle in [('SALE','','sale'),('MAKEUP','','makeup'),('MAKEUP','Foundation','foundation')]])
  calls=[]
  def get(url):calls.append(url);return {'products':[{'id':1,'handle':'x'}]}
  cat.navigation_membership(tls,BASE,get,lambda:None,lambda _:None)
  self.assertEqual(len(calls),2);self.assertNotIn('/sale/',str(calls));self.assertEqual(tls.website_category_evidence['x']['subcategory'],'Foundation')
 def test_breadcrumb_beats_broad_navigation_without_network(self):
  html='<nav aria-label="breadcrumb"><a href="/">Home</a><a href="/collections/WOMEN">WOMEN</a><a href="/collections/dresses">Dresses & Suits</a><a href="/products/x">Item</a></nav>'
  f=cat.breadcrumb(BeautifulSoup(html,'html.parser'),BASE+'/products/x');self.assertEqual(f['website_category_path'],'WOMEN > Dresses & Suits')
  row=dict(f,source_url=BASE+'/products/x');cat.apply(row,{'x':cat.fact(['WOMEN'],BASE+'/collections/WOMEN','verified_navigation_membership')});self.assertEqual(row['subcategory'],'Dresses & Suits')
 def test_ambiguous_breadcrumbs_rejected(self):
  html='<nav class="breadcrumb"><a href="/collections/women">Women</a></nav><nav class="breadcrumb"><a href="/collections/men">Men</a></nav>'
  self.assertIsNone(cat.breadcrumb(BeautifulSoup(html,'html.parser'),BASE+'/products/x'))
 def test_cross_store_or_missing_provenance_cannot_keep_inferred_category(self):
  row=dict(cat.fact(['Skin'], 'https://other.example/collections/skin','verified_navigation_membership'),source_url=BASE+'/products/x');cat.apply(row);self.assertEqual(row['category'],'')
 def test_robots_denial_blocks_membership_fetch(self):
  from urllib.robotparser import RobotFileParser
  robot=RobotFileParser();robot.parse(['User-agent: *','Disallow: /collections/'])
  tls=SimpleNamespace(website_category_robot=robot,website_category_navigation=[{'category':'Skin','url':BASE+'/collections/skin'}]);calls=[]
  cat.navigation_membership(tls,BASE,lambda u:calls.append(u),lambda:None,lambda _:None);self.assertEqual(calls,[])
 def test_jsonld_breadcrumb_exact_three_level_labels(self):
  data={'@type':'BreadcrumbList','itemListElement':[{'position':i+1,'item':{'@id':BASE+'/collections/'+str(i),'name':name}} for i,name in enumerate(['Women','Clothing','Unstitched'])]}
  f=cat.breadcrumb(BeautifulSoup('<script type="application/ld+json">'+json.dumps(data)+'</script>','html.parser'),BASE+'/products/x');row=dict(f,source_url=BASE+'/products/x');cat.apply(row)
  self.assertEqual(row['website_category_path'],'Women > Clothing > Unstitched');self.assertEqual(row['subcategory'],'Unstitched')
 def test_finalization_preserves_verified_product_category(self):
  row=dict(cat.fact(['Skin','Cleansers'],BASE+'/products/x','verified_product_breadcrumb'),source_url=BASE+'/products/x',product_id='p',analysis_note='Owner note');order.apply_order([row]);self.assertEqual(row['subcategory'],'Cleansers');self.assertIn('Owner note',row['analysis_note'])
if __name__=='__main__':unittest.main()
