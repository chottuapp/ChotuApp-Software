"""Validate the owner's explicit grocery category mapping independently of inference."""
import json
from functools import lru_cache
from pathlib import Path
from urllib.parse import urlsplit
STORE='ChotuApp Groceries'
@lru_cache(maxsize=1)
def categories():
 r=json.loads(Path(__file__).with_name('chotu-groceries-request.json').read_text())
 return {p['url']:p['group'] for p in r['pages']}
def authorized_category(row):
 if row.get('subcategory_source')=='owner_brand_search':
  from naheed_brand_support import load_request,brand_key
  request=load_request();scopes={p['url']:p['brand'] for p in request['brands']} if request else {}
  scope=str(row.get('owner_scope_url') or '');expected_brand=scopes.get(scope)
  path=str(row.get('website_category_path') or '');category=path.rsplit(' > ',1)[-1].strip()
  part=urlsplit(str(row.get('source_url') or ''))
  if not expected_brand or brand_key(expected_brand)!=brand_key(row.get('source_manufacturer')) or part.scheme!='https' or part.netloc!='www.naheed.pk' or not category or category!=row.get('Category') or row.get('website_category_status')!='verified_product_breadcrumb' or row.get('website_category_source_url')!=row.get('source_url'):raise ValueError('Exact Naheed brand/product/category evidence missing or changed')
  return category
 url=str(row.get('source_url') or '');scope=str(row.get('owner_scope_url') or '');expected=categories().get(scope)
 if urlsplit(url).scheme!='https' or (urlsplit(url).hostname or '').removeprefix('www.')!='naheed.pk' or not expected or row.get('Category')!=expected or row.get('subcategory_source')!='owner_supplied_scope':raise ValueError('Owner grocery category/source scope missing or changed')
 return expected

def audit(row,source):
 if not source or (urlsplit(str(source.get('source_url') or '')).hostname or '').removeprefix('www.')!='naheed.pk':return None
 if source.get('source_scope_coverage_status')!='complete' or source.get('source_scope_review_count',0)!=0:return ['Grocery source coverage unresolved; complete-catalog approval held']
 try:expected=authorized_category(source)
 except ValueError:return ['Owner grocery category/source scope requires review']
 if row.get('source_url')!=source.get('source_url') or row.get('Category')!=expected:return ['Export Category differs from owner grocery scope']
 if source.get('subcategory_source')=='owner_brand_search':
  if any(row.get(k)!=source.get(k) for k in ('owner_scope_url','source_manufacturer','website_category_path','website_category_source_url','subcategory_source')):return ['Export differs from exact Naheed brand/category evidence']
 return []
