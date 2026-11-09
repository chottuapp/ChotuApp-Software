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
 url=str(row.get('source_url') or '');scope=str(row.get('owner_scope_url') or '');expected=categories().get(scope)
 if urlsplit(url).scheme!='https' or (urlsplit(url).hostname or '').removeprefix('www.')!='naheed.pk' or not expected or row.get('Category')!=expected or row.get('subcategory_source')!='owner_supplied_scope':raise ValueError('Owner grocery category/source scope missing or changed')
 return expected

def audit(row,source):
 if not source or (urlsplit(str(source.get('source_url') or '')).hostname or '').removeprefix('www.')!='naheed.pk':return None
 if source.get('source_scope_coverage_status')!='complete' or source.get('source_scope_review_count',0)!=0:return ['Grocery source coverage unresolved; complete-catalog approval held']
 try:expected=authorized_category(source)
 except ValueError:return ['Owner grocery category/source scope requires review']
 if row.get('source_url')!=source.get('source_url') or row.get('Category')!=expected:return ['Export Category differs from owner grocery scope']
 return []
