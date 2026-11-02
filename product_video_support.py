"""Product-bound video discovery; never collect site-wide or recommendation videos."""
import json,re
from urllib.parse import urljoin,urlsplit
from bs4 import BeautifulSoup
FIELDS=('video_urls','video_fetch_status','video_source_url')

def identity(url):
 p=urlsplit(str(url));return (p.hostname or '').lower().removeprefix('www.'),p.path.rstrip('/')

def video_url(value,base,embed=False):
 if not isinstance(value,str):return ''
 value=urljoin(base,value.strip());p=urlsplit(value)
 if p.scheme not in ('http','https') or not p.hostname or p.username or p.password:return ''
 if re.search(r'\.(?:mp4|webm|mov|m3u8)$',p.path,re.I):return value
 host=p.hostname.lower().removeprefix('www.')
 if host in {'youtube.com','youtube-nocookie.com','youtu.be','player.vimeo.com','vimeo.com'}:
  if host=='youtu.be' and p.path.strip('/'):return value
  if host.startswith('youtube') and (re.match(r'^/(?:embed|shorts)/[^/]+',p.path) or p.path=='/watch' and 'v=' in p.query):return value
  if 'vimeo' in host and re.search(r'/\d+',p.path):return value
 return ''

def extract(page,page_url,expected_url):
 if identity(page_url)!=identity(expected_url):return []
 soup=BeautifulSoup(page,'html.parser');canonical=soup.select_one('link[rel="canonical"]')
 if canonical and identity(urljoin(page_url,canonical.get('href','')))!=identity(expected_url):return []
 found=[]
 def add(value):
  url=video_url(value,page_url)
  if url and url not in found:found.append(url)
 def videos(value):
  for item in value if isinstance(value,list) else [value]:
   if not isinstance(item,dict):continue
   for key in ('contentUrl','embedUrl'):add(item.get(key))
 # A VideoObject must be explicitly attached to this exact Product.
 for script in soup.select('script[type="application/ld+json"]'):
  try:data=json.loads(script.string or script.get_text())
  except (ValueError,TypeError):continue
  nodes=data if isinstance(data,list) else [data]
  for node in list(nodes):
   if isinstance(node,dict) and isinstance(node.get('@graph'),list):nodes.extend(node['@graph'])
  for node in nodes:
   if not isinstance(node,dict):continue
   types=node.get('@type',[]);types=[types] if isinstance(types,str) else types
   if 'Product' not in types:continue
   subject=node.get('url') or node.get('@id','').split('#')[0]
   if not subject or identity(urljoin(page_url,subject))!=identity(expected_url):continue
   videos(node.get('video',[]))
 # Only explicit product media/detail containers. Exclude cross-sell/global media.
 for scope in soup.select('media-gallery, [id^="MediaGallery"], .product__media, .woocommerce-product-gallery, [data-product-media], .product-single__media, .product__description, #tab-description, [itemprop="description"]'):
  for element in scope.select('video, video source, iframe'):
   ancestors=[element,*element.parents]
   if any(re.search(r'recommend|related|upsell|cross.sell|footer|header',str(a.get('class',''))+' '+str(a.get('id','')),re.I) for a in ancestors if getattr(a,'attrs',None)):continue
   add(element.get('src') or element.get('data-src'))
 return found

def from_page(page,page_url,expected_url):
 urls=extract(page,page_url,expected_url)
 return dict(video_urls='|'.join(urls),video_fetch_status='found' if urls else 'not_found',video_source_url=expected_url)

def export_fields(row,g):
 if 'video_fetch_status' in row:return {key:row.get(key,'') for key in FIELDS}
 url=str(row.get('source_url') or '')
 if not url:return dict(video_urls='',video_fetch_status='page_unavailable',video_source_url='')
 try:
  tls=g.get('_chotu_tls');cache=getattr(tls,'saved_response_cache',None)
  response=cache.get(url) if cache is not None else None
  if response is None:
   if getattr(tls,'image_throttled',False):raise ValueError('Source requests paused')
   g['_chotu_wait']();response=g['S'].get(url,timeout=25)
  if getattr(response,'status_code',200) in (429,503) and tls is not None:tls.image_throttled=True
  response.raise_for_status()
  if identity(getattr(response,'url',url))!=identity(url):raise ValueError('Source identity mismatch')
  return from_page(response.text,getattr(response,'url',url),url)
 except Exception:
  return dict(video_urls='',video_fetch_status='page_unavailable',video_source_url=url)

def ensure_fields(sheet):
 headers=[c.value for c in sheet[1]]
 for field in FIELDS:
  if field not in headers:sheet.cell(1,sheet.max_column+1,field)
 if hasattr(sheet,'_chotu_export_headers'):del sheet._chotu_export_headers
