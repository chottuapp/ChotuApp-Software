import copy
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
from openpyxl import load_workbook
import test_magento_source as fixtures
from magento_source_support import BASE,PublicCatalog,normalize,verified_page_options
from woocommerce_source_support import export


class MissingOptionPriceTests(unittest.TestCase):
 def fixture(self):
  raw=fixtures.MagentoTests().product()
  raw['options']=[dict(__typename='CustomizableRadioOption',option_id=7,title='Storage',required=True,value=[dict(option_type_id=71,title='16 GB',price=None,price_type='DYNAMIC'),dict(option_type_id=72,title='32 GB',price=500,price_type='FIXED')])]
  option_config={'7':{'71':dict(name='16 GB',type=None,prices={k:dict(amount=0) for k in ('oldPrice','basePrice','finalPrice')})}}
  configs=[{'#product_addtocart_form':{'priceOptions':dict(optionConfig=option_config,priceHolderSelector="[data-product-id='10'][data-role=priceBox]")}}, {'price-box':{'priceBox':{'priceConfig':dict(productId=10,prices=dict(oldPrice=dict(amount=59500),finalPrice=dict(amount=58500)))}}}, {'provider':dict(id=10,currency_code='PKR',url=BASE+'/lenovo-used-laptop.html')}]
  return raw,configs
 def page(self,raw,configs):
  url=BASE+'/'+raw['url_key']+raw['url_suffix']
  html='<link rel="canonical" href="'+url+'"><h1>'+raw['name']+'</h1><div class="product attribute sku"><div class="value">'+raw['sku']+'</div></div>'
  html+=''.join('<script type="text/x-magento-init">'+json.dumps(c)+'</script>' for c in configs)
  return SimpleNamespace(status_code=200,url=url,text=html)
 def test_missing_api_fee_requires_evidence_and_never_defaults_to_zero(self):
  raw,configs=self.fixture()
  with self.assertRaisesRegex(ValueError,'public-page verification'):normalize(raw)
  before=copy.deepcopy(raw);fixed=verified_page_options(raw,self.page(raw,configs));p=normalize(fixed)
  self.assertEqual([str(c['extra_price']) for c in p['custom_options'][0]['choices']],['0','500']);self.assertEqual(raw,before)
 def test_wrong_product_currency_labels_base_price_and_unsupported_percentage_are_rejected(self):
  for failure in ('id','currency','label','base_price','percentage','nonzero_dynamic','missing_fee'):
   with self.subTest(failure=failure):
    raw,c=self.fixture();proof=c[0]['#product_addtocart_form']['priceOptions']['optionConfig']['7']['71']
    if failure=='id':c[1]['price-box']['priceBox']['priceConfig']['productId']=99
    if failure=='currency':c[2]['provider']['currency_code']='USD'
    if failure=='label':proof['name']='Different option'
    if failure=='base_price':c[1]['price-box']['priceBox']['priceConfig']['prices']['finalPrice']['amount']=58000
    if failure=='percentage':proof['type']='percent'
    if failure=='nonzero_dynamic':
     for v in proof['prices'].values():v['amount']=100
    if failure=='missing_fee':del proof['prices']['finalPrice']
    with self.assertRaises(ValueError):verified_page_options(raw,self.page(raw,c))
 def test_denied_redirected_and_wrong_sku_pages_are_rejected(self):
  for failure in ('denied','redirect','sku'):
   raw,c=self.fixture();page=self.page(raw,c)
   if failure=='denied':page.status_code=403
   if failure=='redirect':page.url=BASE+'/another-product.html'
   if failure=='sku':page.text=page.text.replace(raw['sku'],'ANOTHER-SKU')
   with self.subTest(failure=failure),self.assertRaises(ValueError):verified_page_options(raw,page)
 def test_provider_verifies_page_before_normalizing_and_reuses_same_response(self):
  raw,c=self.fixture();get=Mock(return_value=self.page(raw,c));reader=PublicCatalog({'S':SimpleNamespace(get=get),'_chotu_wait':lambda:None},BASE,lambda _:None)
  reader.byid[10]=copy.deepcopy(raw);reader.robot=SimpleNamespace(can_fetch=lambda *a:True);reader.query=Mock(return_value={'items':[raw]})
  product=reader.read('/wp-json/wc/store/v1/products/10');self.assertEqual(product['custom_options'][0]['choices'][0]['extra_price'],0);get.assert_called_once()
 def test_provider_never_fetches_disallowed_option_page(self):
  raw,c=self.fixture();get=Mock();reader=PublicCatalog({'S':SimpleNamespace(get=get)},BASE,lambda _:None);reader.byid[10]=copy.deepcopy(raw);reader.robot=SimpleNamespace(can_fetch=lambda *a:False);reader.query=Mock(return_value={'items':[raw]})
  with self.assertRaisesRegex(ValueError,'disallowed'):reader.read('/wp-json/wc/store/v1/products/10')
  get.assert_not_called()
 def test_verified_options_reach_real_excel_without_invented_variant_skus(self):
  from test_app import main
  raw,c=self.fixture();product=normalize(verified_page_options(raw,self.page(raw,c)))
  provider=SimpleNamespace(label='verified page fixture',supports=lambda _:True,catalog=lambda:[product],read=lambda _:product)
  with tempfile.TemporaryDirectory() as tmp:
   g=dict(vars(main),OUT=Path(tmp),_chotu_wait=lambda:None)
   export(g,BASE,'Paklap',Path(__file__).resolve().parents[1]/'importer-files/Chotu_Products_Import_Template_Discount_Tags.xlsx',lambda _:None,provider=provider)
   book=load_workbook(Path(tmp)/'Paklap - REFRESH REVIEW.xlsx',read_only=True)
   iterator=book['Options'].iter_rows(values_only=True);headers=next(iterator);rows=[dict(zip(headers,row)) for row in iterator]
   self.assertEqual([r['extra_price (PKR)'] for r in rows],[0,500]);self.assertEqual(book['Variant Combinations'].max_row,2);book.close()
