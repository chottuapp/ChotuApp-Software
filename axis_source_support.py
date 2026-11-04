"""Read product objects explicitly embedded in the public Axis Next.js page; never eval JS."""
import json,re
from bs4 import BeautifulSoup

def page_products(html):
 soup=BeautifulSoup(html,'html.parser');payloads=[];decoder=json.JSONDecoder()
 for script in soup.find_all('script'):
  text=script.string or script.get_text()
  if script.get('id')=='__NEXT_DATA__':payloads.append(text)
  for match in re.finditer(r'self\.__next_f\.push\(',text):
   try:value,_=decoder.raw_decode(text[match.end():])
   except ValueError:continue
   if isinstance(value,list) and len(value)>1 and isinstance(value[1],str):payloads.append(value[1])
 joined=''.join(payloads);found=[]
 def clean(value):
  if isinstance(value,dict):return {k:clean(v) for k,v in value.items() if not re.search(r'token|secret|password|authorization|api.?key|email|phone|session|cookie|customer|address',k,re.I)}
  if isinstance(value,list):return [clean(v) for v in value]
  return value
 def collect(value):
  if isinstance(value,list):
   for item in value:collect(item)
  elif isinstance(value,dict):
   if any(k in value for k in ('name','title')) and any(k in value for k in ('id','slug','handle')) and any('price' in k.lower() for k in value):
    value=clean(value)
    if value not in found:found.append(value)
   else:
    for item in value.values():
     if isinstance(item,(dict,list)):collect(item)
 for match in re.finditer(r'"(?:initialProduct|product|initialProducts|products)"\s*:\s*',joined):
  try:value,_=decoder.raw_decode(joined[match.end():]);collect(value)
  except ValueError:continue
 return found
