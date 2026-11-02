import ast,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
from openpyxl import Workbook
from product_video_support import extract,export_fields,ensure_fields
URL='https://shop.example/products/item'
class ProductVideos(unittest.TestCase):
 def test_product_media_and_description_only_and_deduplicated(self):
  page='''<link rel="canonical" href="/products/item"><header><video src="https://cdn.example/header.mp4"></video></header><media-gallery><video><source src="https://cdn.example/item.mp4"></video><iframe src="https://www.youtube.com/embed/abc123"></iframe><div class="related-products"><video src="https://cdn.example/other.mp4"></video></div></media-gallery><div class="product__description"><video src="https://cdn.example/item.mp4"></video></div><footer><iframe src="https://youtube.com/embed/global"></iframe></footer>'''
  self.assertEqual(extract(page,URL,URL),['https://cdn.example/item.mp4','https://www.youtube.com/embed/abc123'])
 def test_structured_video_requires_exact_product_binding(self):
  page='''<script type="application/ld+json">{"@graph":[{"@type":"VideoObject","contentUrl":"https://cdn.example/global.mp4"},{"@type":"Product","url":"https://shop.example/products/other","video":{"contentUrl":"https://cdn.example/other.mp4"}},{"@type":"Product","url":"https://shop.example/products/item","video":[{"contentUrl":"https://cdn.example/item.mp4"},{"embedUrl":"https://player.vimeo.com/video/123"}]}]}</script>'''
  self.assertEqual(extract(page,URL,URL),['https://cdn.example/item.mp4','https://player.vimeo.com/video/123'])
 def test_redirect_canonical_mismatch_and_unsafe_links_rejected(self):
  self.assertEqual(extract('<media-gallery><video src="https://cdn.example/item.mp4"></video></media-gallery>',URL+'/other',URL),[])
  self.assertEqual(extract('<link rel="canonical" href="/products/other"><media-gallery><video src="https://cdn.example/item.mp4"></video></media-gallery>',URL,URL),[])
  self.assertEqual(extract('<media-gallery><video src="javascript:alert(1)"></video><iframe src="https://ads.example/banner"></iframe><video src="https://user:pass@cdn.example/a.mp4"></video></media-gallery>',URL,URL),[])
 def test_saved_page_used_without_network_and_failures_reported(self):
  response=SimpleNamespace(url=URL,text='<media-gallery><video src="https://cdn.example/item.webm"></video></media-gallery>',raise_for_status=lambda:None)
  get=Mock();g={'_chotu_tls':SimpleNamespace(saved_response_cache={URL:response}),'S':SimpleNamespace(get=get),'_chotu_wait':Mock()}
  self.assertEqual(export_fields({'source_url':URL},g)['video_fetch_status'],'found');get.assert_not_called()
  get.side_effect=RuntimeError('private error');g['_chotu_tls']=SimpleNamespace()
  self.assertEqual(export_fields({'source_url':URL},g)['video_fetch_status'],'page_unavailable');self.assertEqual(get.call_count,1)
 def test_existing_fields_survive_without_refetch_and_columns_once(self):
  row=dict(video_urls='https://cdn.example/item.mp4',video_fetch_status='found',video_source_url=URL)
  self.assertEqual(export_fields(row,{}),row)
  w=Workbook();s=w.active;s.append(['product_id','name']);ensure_fields(s);ensure_fields(s)
  self.assertEqual([c.value for c in s[1]],['product_id','name','video_urls','video_fetch_status','video_source_url'])

 def test_real_export_writer_keeps_video_fields_and_existing_values(self):
  tree=ast.parse(Path('main.py').read_text());node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='write_row')
  namespace={'discount_export_fields':lambda values:dict(values)}
  exec(compile(ast.Module(body=[node],type_ignores=[]),'main.py','exec'),namespace)
  w=Workbook();s=w.active;s.title='Products';s.append(['product_id','name','source_url','base_price (PKR)'])
  row=dict(product_id='P1',name='Actual product',source_url=URL,video_urls='https://cdn.example/item.mp4',video_fetch_status='found',video_source_url=URL,**{'base_price (PKR)':500})
  namespace['write_row'](s,row)
  values=dict(zip([c.value for c in s[1]],[c.value for c in s[2]]))
  self.assertEqual(values['video_urls'],row['video_urls']);self.assertEqual(values['base_price (PKR)'],500);self.assertEqual(values['source_url'],URL)
