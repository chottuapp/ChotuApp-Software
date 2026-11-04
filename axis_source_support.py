"""Read product objects explicitly embedded in the public Axis Next.js page; never eval JS."""
import json,re
from bs4 import BeautifulSoup

def public_products(value):
 # Restrict extraction to product-shaped objects; unrelated session/config
 # JSON is never retained. Escaping prevents data from creating HTML tags.
 text=json.dumps({'product':value},ensure_ascii=True).replace('</','<\\/')
 return page_products('<script id="__NEXT_DATA__">'+text+'</script>')

def flight_values(html):
 soup=BeautifulSoup(html,'html.parser');payloads=[];decoder=json.JSONDecoder()
 for script in soup.find_all('script'):
  text=script.string or script.get_text()
  if script.get('id')=='__NEXT_DATA__':payloads.append(text)
  for match in re.finditer(r'self\.__next_f\.push\(',text):
   try:value,_=decoder.raw_decode(text[match.end():])
   except ValueError:continue
   if isinstance(value,list) and len(value)>1 and isinstance(value[1],str):payloads.append(value[1])
 joined=''.join(payloads);values=[]
 for payload in payloads:
  try:values.append(json.loads(payload))
  except ValueError:pass
 for match in re.finditer(r'(?m)^[0-9a-f]+:',joined):
  try:value,_=decoder.raw_decode(joined[match.end():]);values.append(value)
  except ValueError:continue
 return joined,values

def public_render_props(html):
 _,values=flight_values(html);found=[]
 def scrub(value):
  if isinstance(value,dict):return {k:scrub(v) for k,v in value.items() if not re.search(r'token|secret|password|authorization|api.?key|email|phone|session|cookie|customer|address',k,re.I)}
  if isinstance(value,list):return [scrub(v) for v in value]
  return value
 def walk(value):
  if isinstance(value,list):
   for v in value:walk(v)
  elif isinstance(value,dict):
   fields={k:v for k,v in value.items() if re.search(r'product|variant|size|colou?r|price|stock|inventory|currency|sku|slug',k,re.I) and not re.search(r'token|secret|password|authorization|api.?key|email|phone|session|cookie|customer|address',k,re.I)}
   fields=scrub(fields)
   if fields and len(json.dumps(fields))<40000 and fields not in found:found.append(fields)
   for v in value.values():
    if isinstance(v,(dict,list)):walk(v)
 for value in values:walk(value)
 return found[:12]

def page_products(html):
 joined,values=flight_values(html);decoder=json.JSONDecoder();found=[]
 def clean(value):
  if isinstance(value,dict):return {k:clean(v) for k,v in value.items() if not re.search(r'token|secret|password|authorization|api.?key|email|phone|session|cookie|customer|address',k,re.I)}
  if isinstance(value,list):return [clean(v) for v in value]
  return value
 def collect(value):
  if isinstance(value,list):
   for item in value:collect(item)
  elif isinstance(value,dict):
   if any(k in value for k in ('name','title','productName','product_name')) and any(k in value for k in ('id','_id','productId','product_id','slug','handle')) and any('price' in k.lower() for k in value):
    value=clean(value)
    if value not in found:found.append(value)
   else:
    for item in value.values():
     if isinstance(item,(dict,list)):collect(item)
 for match in re.finditer(r'"(?:initialProduct|product|initialProducts|products)"\s*:\s*',joined):
  try:value,_=decoder.raw_decode(joined[match.end():]);collect(value)
  except ValueError:continue
 for value in values:collect(value)
 return found
