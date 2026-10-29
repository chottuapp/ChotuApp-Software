"""Use Breakout's publicly advertised Shopify checkout storefront for exact catalog data."""
from urllib.parse import urlsplit
SHOP='https://checkout.breakout.com.pk'
def enable_breakout_source(g):
 original=g['_chotuapp_run_site_original']
 def run(base,name,template,log):
  if (urlsplit(base).hostname or '').removeprefix('www.')!='breakout.com.pk':return original(base,name,template,log)
  g['_chotu_wait']();response=g['S'].get(base.rstrip('/')+'/',timeout=30)
  if response.status_code!=200 or (urlsplit(response.url).hostname or '').removeprefix('www.')!='breakout.com.pk':raise ValueError('Breakout official source identity unavailable')
  if 'checkout.breakout.com.pk' not in response.text or 'bktt.myshopify.com' not in response.text:raise ValueError('Breakout no longer advertises verified Shopify origin; no guessed source fallback')
  data=g['get_json'](SHOP+'/products.json?limit=1&page=1')
  if not isinstance(data,dict) or not data.get('products') or not all(p.get('id') and p.get('handle') and p.get('variants') for p in data['products']):raise ValueError('Breakout advertised source catalog schema incomplete')
  log('BREAKOUT SOURCE: verified official advertised checkout storefront; canonical price, currency, variant and stock checks retained.')
  return original(SHOP,name,template,log)
 g['_chotuapp_run_site_original']=run
