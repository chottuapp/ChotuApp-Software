"""Simulated multi-fit responses validate routing and rejection; prices are test data."""
import copy,json,sys,unittest
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import parse_qs,urlsplit,urlencode
from bs4 import BeautifulSoup
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import sapphire_source_support as source
MASTER='MSTEKR26V610';URL=source.BASE+'/collections/kurtas/products/'+MASTER+'.html'
def page(fit=None,size=None,wrong_fit=False):
 soup=BeautifulSoup((ROOT/'tests/fixtures/sapphire_public/regular_fit.html').read_text(),'html.parser');main=soup.select_one('.product-wrapper')
 regular=main.select_one('[data-attr="itemType"] input');slim=copy.copy(regular);slim['id']='Slim Fit';slim['data-attr-value']='SLM';regular.parent.append(slim)
 for node in main.select('[data-attr="itemType"] input'):
  node.attrs.pop('checked',None);value=node['data-attr-value'];node['value']=source.BASE+'/on/demandware.store/Product-Variation?'+urlencode({'dwvar_'+MASTER+'_itemType':value})
  if fit and value==('RGL' if wrong_fit else fit):node['checked']=''
 for node in main.select('[data-attr="size"] input.options-select'):
  value=node['data-attr-value'];node['value']=source.BASE+'/on/demandware.store/Product-Variation?'+urlencode({**({'dwvar_'+MASTER+'_itemType':fit} if fit else {}),'dwvar_'+MASTER+'_size':value})
  if size==value:node['checked']=''
 if fit and size:
  pid=MASTER+'-'+fit+'-'+size;main['data-pid']=pid
  for node in main.select('[data-pid]'):node['data-pid']=pid
  soup.select_one('link[rel="canonical"]')['href']=source.BASE+'/collections/kurtas/products/'+pid+'.html'
  button=main.select_one('button.add-to-cart');data=json.loads(button['data-gtmga4data']);data['item_variant']=pid;data['price']=6100 if fit=='RGL' else 6200;button['data-gtmga4data']=json.dumps(data);button.attrs.pop('disabled',None)
  if fit=='RGL':button['disabled']=''
  for n in source.primary_nodes(main,'.price .sales .cc-price[content]'):n['content']=str(data['price'])
 return str(soup)
class FitTests(unittest.TestCase):
 def test_both_fit_and_size_prices_and_stock_come_from_selected_pages(self):
  urls=[]
  def read(url):
   urls.append(url);params=parse_qs(urlsplit(url).query);return SimpleNamespace(text=page(params['dwvar_'+MASTER+'_itemType'][0],params['dwvar_'+MASTER+'_size'][0]))
  product=source.normalize_product(page(),URL,read)
  self.assertEqual([d['name'] for d in product['options']],['Fit','Size']);self.assertEqual(len(product['variants']),8);self.assertEqual(len(set(v['id'] for v in product['variants'])),8)
  for v in product['variants']:
   self.assertEqual(v['available'],v['option1']=='Slim Fit');self.assertEqual(float(v['price']),6100 if v['option1']=='Regular Fit' else 6200);self.assertIn(v['option2'],['S','M','L','XL'])
  self.assertTrue(all('/on/demandware.store/' not in u for u in urls))
 def test_denim_inseam_labels_are_not_exported_as_fit(self):
  def denim(markup):return markup.replace('Regular Fit','Inseam-030').replace('Slim Fit','Inseam-032')
  def read(url):
   params=parse_qs(urlsplit(url).query);return SimpleNamespace(text=denim(page(params['dwvar_'+MASTER+'_itemType'][0],params['dwvar_'+MASTER+'_size'][0])))
  product=source.normalize_product(denim(page()),URL,read)
  self.assertEqual([d['name'] for d in product['options']],['Inseam','Size'])
 def test_unselected_disabled_master_is_not_a_fake_variant(self):
  def read(url):
   params=parse_qs(urlsplit(url).query)
   if params['dwvar_'+MASTER+'_itemType'][0]=='SLM':return SimpleNamespace(text=page())
   return SimpleNamespace(text=page('RGL',params['dwvar_'+MASTER+'_size'][0]))
  product=source.normalize_product(page(),URL,read)
  self.assertEqual(len(product['variants']),4);self.assertEqual(len(product['_unverified_variant_selections']),4)
  self.assertIn('unverified',product['_popularity_page_note'])
 def test_master_price_range_is_allowed_only_before_exact_size_selection(self):
  soup=BeautifulSoup(page(),'html.parser');main=soup.select_one('.product-wrapper');sales=source.primary_nodes(main,'.price .sales .cc-price[content]')
  for node in sales:
   node['content']='6200';wrapper=soup.new_tag('div',attrs={'class':'range'});node.parent.wrap(wrapper)
   extra=soup.new_tag('span',attrs={'class':'sales'});price=soup.new_tag('span',attrs={'class':'cc-price','content':'6100'});extra.append(price);wrapper.append(extra)
  button=source.primary_nodes(main,'button.add-to-cart[data-gtmga4data]')[0];data=json.loads(button['data-gtmga4data']);data['price']=6200;button['data-gtmga4data']=json.dumps(data)
  parsed=source.inspect_page(str(soup),URL);self.assertTrue(parsed['has_price_range'])
  wrapper.unwrap()
  with self.assertRaises(ValueError):source.inspect_page(str(soup),URL)
 def test_server_selecting_wrong_fit_is_rejected(self):
  def read(url):
   params=parse_qs(urlsplit(url).query);return SimpleNamespace(text=page(params['dwvar_'+MASTER+'_itemType'][0],params['dwvar_'+MASTER+'_size'][0],wrong_fit=True))
  with self.assertRaises(ValueError):source.normalize_product(page(),URL,read)
