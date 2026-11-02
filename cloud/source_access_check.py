"""One robots-aware public API access check; no retries, alternate routes or body dumps."""
import argparse,json,os,re,sys
from pathlib import Path
from urllib.robotparser import RobotFileParser
import requests
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from locked_store_rules import owner_paused
from woocommerce_source_support import HOSTS
from urllib.parse import urlsplit

def check(site,session=None):
 result=dict(store=site['name'],host=urlsplit(site['url']).hostname,status='unchecked')
 if owner_paused(site['name'],site['url']):return dict(result,status='owner_paused')
 if result['host'].removeprefix('www.') not in HOSTS:raise ValueError('This diagnostic supports approved public WooCommerce sources only')
 session=session or requests.Session()
 session.headers.update({'User-Agent':'Mozilla/5.0 (compatible; ChotuAppCatalogRefresh/1.0)','Cache-Control':'no-cache','Pragma':'no-cache'})
 if os.environ.get('SSL_CERT_FILE'):session.verify=os.environ['SSL_CERT_FILE']
 base=site['url'].rstrip('/');api=base+'/wp-json/wc/store/v1/products?per_page=100&page=1'
 robots=session.get(base+'/robots.txt',timeout=(15,30),allow_redirects=False)
 result['robots_status']=robots.status_code
 if robots.status_code not in (200,404):return dict(result,status='source_permissions_unverified')
 policy=RobotFileParser();policy.parse(robots.text.splitlines() if robots.status_code==200 else [])
 if not policy.can_fetch(session.headers['User-Agent'],api):return dict(result,status='robots_disallowed')
 response=session.get(api,timeout=(15,30),allow_redirects=False);result['api_status']=response.status_code
 if response.status_code==200:
  try:data=response.json()
  except ValueError:return dict(result,status='source_schema_unverified')
  if not isinstance(data,list) or not data or not isinstance(data[0],dict) or not data[0].get('id'):return dict(result,status='source_schema_unverified')
  return dict(result,status='public_api_readable')
 result['status']='source_denied' if response.status_code in (401,403) else 'source_unavailable'
 try:
  code=response.json().get('code')
  if isinstance(code,str) and re.fullmatch('[A-Za-z0-9_-]{1,80}',code):result['public_error_code']=code
 except (ValueError,AttributeError):pass
 if response.headers.get('cf-mitigated')=='challenge' or re.search(r'cf-chl-|<title>\s*(?:Just a moment|Attention Required)',response.text,re.I):result['denial_kind']='cloudflare_challenge'
 elif 'wordfence' in response.text.lower():result['denial_kind']='wordfence_denial'
 else:result['denial_kind']='http_access_denial'
 return result

def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--store',required=True);args=parser.parse_args()
 sites=json.loads((ROOT/'cloud/fetch-update-release.json').read_text())['fresh_stores'];matches=[s for s in sites if s['name']==args.store]
 if len(matches)!=1:raise ValueError('Exact approved store name required')
 print(json.dumps(check(matches[0]),sort_keys=True))
if __name__=='__main__':main()
