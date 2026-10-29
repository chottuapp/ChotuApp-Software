"""Owner-selected collection scopes; never fall back to a whole-store catalog."""
from urllib.parse import urlsplit
SCOPES={'habitt.com':'kitchen'}
def collection_for(base):return SCOPES.get((urlsplit(base).hostname or '').lower().removeprefix('www.'))
def scoped_discover(g,base,handle,log):
 products={}
 for page in range(1,101):
  url=base.rstrip('/')+'/collections/'+handle+'/products.json?limit=250&page='+str(page)
  data=g['get_json'](url)
  if not isinstance(data,dict) or not isinstance(data.get('products'),list):raise ValueError('Selected collection catalog unavailable; no whole-store fallback')
  batch=data['products']
  for p in batch:
   if p.get('id') is None or not p.get('handle'):raise ValueError('Scoped product identity missing')
   if p['id'] in products:raise ValueError('Duplicate scoped pagination identity')
   products[p['id']]=p
  log('COLLECTION SCOPE: '+handle+' page '+str(page)+'; '+str(len(products))+' distinct products')
  if len(batch)<250:
   if not products:raise ValueError('Selected collection empty; no whole-store fallback')
   return list(products.values()),True
 raise ValueError('Selected collection pagination limit; completeness not confirmed')
def enable_collection_scope(g):
 original=g['_chotuapp_run_site_original']
 def run(base,name,template,log):
  scope=collection_for(base)
  if not scope:return original(base,name,template,log)
  previous=g['discover']
  def discover(source,logger):
   result=scoped_discover(g,source,scope,logger);g['_chotu_tls'].fast_products=result[0];return result
  g['discover']=discover
  try:return original(base,name,template,log)
  finally:g['discover']=previous
 g['_chotuapp_run_site_original']=run
