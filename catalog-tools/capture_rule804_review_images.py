"""Fetch only public product-image references for visual product-type review."""
import io,json,hashlib,urllib.parse,urllib.request,concurrent.futures
from pathlib import Path
from PIL import Image,ImageOps,ImageDraw
Image.MAX_IMAGE_PIXELS=10000000
root=Path('catalog-inputs/rule804-20261020-completion')
def capture(pair):
 index,item=pair;item=dict(item);url=item.get('image_url') or ''
 if url.startswith('//'):url='https:'+url
 p=urllib.parse.urlsplit(url)
 if p.scheme!='https' or p.hostname not in {'cdn.shopify.com','rawayat.com.pk','www.rawayat.com.pk','www.junaidjamshed.com','zellbury.com'}:return index,item,None
 q=urllib.parse.parse_qs(p.query);q['width']=['250'];request=urllib.parse.urlunsplit((p.scheme,p.netloc,p.path,urllib.parse.urlencode(q,doseq=True),''));item['image_request_url']=request
 try:
  with urllib.request.urlopen(urllib.request.Request(request,headers={'User-Agent':'ChotuAppRule804/1.0'}),timeout=25) as r:raw=r.read(2000001)
  if len(raw)>2000000:raise ValueError('Image exceeds 2MB budget')
  image=Image.open(io.BytesIO(raw))
  if image.width*image.height>10000000:raise ValueError('Image dimensions exceed review budget')
  image=ImageOps.contain(image.convert('RGB'),(240,240));item['image_response_sha256']=hashlib.sha256(raw).hexdigest();return index,item,image
 except Exception as error:item['image_error']=str(error);return index,item,None
jobs=json.loads((root/'image-jobs.json').read_text());canvas=Image.new('RGB',(1440,300*((len(jobs)+5)//6)),'white');draw=ImageDraw.Draw(canvas);manifest=[]
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
 for index,item,img in pool.map(capture,enumerate(jobs)):
  x=index%6*240;y=index//6*300
  if img:canvas.paste(img,(x+(240-img.width)//2,y))
  else:draw.text((x+10,y+100),'IMAGE UNAVAILABLE',fill='red')
  caption=str(index)+' | '+item['store']+'\n'+item['name'][:35]+'\n'+item['product_id']
  draw.text((x+5,y+245),caption,fill='black');manifest.append(item)
canvas.save(root/'visual-review.jpg',quality=85);(root/'visual-review.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
