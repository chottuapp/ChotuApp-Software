import json,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'cloud'))
from source_research import describe,clean_html,public_product_state
from bs4 import BeautifulSoup
class ResearchTests(unittest.TestCase):
 def test_product_links_and_country_controls_parse(self):
  html='<main><div class="product" data-pid="1"><a href="/collections/all/products/1.html">Product</a></div></main><select name="country"><option value="PK">Pakistan</option></select>'
  d=describe(html,'https://pk.sapphireonline.pk/');self.assertEqual(d['product_links'],['https://pk.sapphireonline.pk/collections/all/products/1.html']);self.assertIn('Pakistan',d['locale_controls'][0])
 def test_sensitive_bootstrap_and_fields_removed_from_visible_html(self):
  h=clean_html('<main><input value="private"><script>secret</script><p>Product details</p></main>');self.assertNotIn('private',h);self.assertNotIn('secret',h);self.assertIn('Product details',h)
 def test_decode_only_product_structures_without_credential_fields(self):
  data=[{'id':1,'title':2,'variants':3,'secret_token':4},123,'Product',[5], 'private',{'price':6,'id':7},100,42]
  d=public_product_state(BeautifulSoup('<script id="__NUXT_DATA__">'+json.dumps(data)+'</script>','html.parser'));self.assertEqual(d[0]['title'],'Product');self.assertEqual(d[0]['variants'][0]['price'],100);self.assertNotIn('private',str(d))
if __name__=='__main__':unittest.main()
