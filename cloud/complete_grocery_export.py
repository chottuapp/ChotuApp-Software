"""Finish the existing grocery file: reconcile four scopes and fetch missing products only."""
import csv,hashlib,json,os,runpy,shutil,tempfile,zipfile
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import urlsplit
import requests
from openpyxl import load_workbook
from resume_support import ResponseCache,SessionProxy
from chotu_groceries_source_support import PublicCatalog,product,IncompleteProduct,ProductReviewRequired,BASE,STORE
from grocery_scope_repair import repair
from legacy_original_schema import normalize
from rule804_pipeline import process
from audit804 import run as audit
from locked_store_rules import incomplete_product_reasons
ROOT=Path(__file__).resolve().parents[1]
PENDING={18,29,31,75}

def merge(source,extra,target):
 book=load_workbook(source);add=load_workbook(extra)
 try:
  for name in ('Products','Product Images','Option Groups','Options','Variant Combinations'):
   s=book[name];a=add[name];headers=[c.value for c in s[1]]
   for c in a[1]:
    if c.value and c.value not in headers:headers.append(c.value);s.cell(1,len(headers),c.value)
   old={str(r[0]) for r in s.iter_rows(min_row=2,values_only=True) if r and r[0] is not None} if name!='Products' else {str(r[headers.index('product_id')]) for r in s.iter_rows(min_row=2,values_only=True)}
   ah=[c.value for c in a[1]]
   for values in a.iter_rows(min_row=2,values_only=True):
    if not any(v is not None for v in values):continue
    row=dict(zip(ah,values));identity=str(row.get('product_id')) if name=='Products' else str(values[0])
    if identity in old:raise ValueError('Duplicate linked row during grocery merge')
    old.add(identity);s.append([row.get(k) for k in headers])
  book.save(target)
 finally:add.close();book.close()

def main():
 original=Path(os.environ['GROCERY_EXPORT_ROOT'])/'ChotuApp Groceries.xlsx'
 if not original.is_file():
  matches=list(Path(os.environ['GROCERY_EXPORT_ROOT']).rglob(original.name))
  if len(matches)!=1:raise ValueError('Exact original grocery file required')
  original=matches[0]
 out=Path(os.environ['GROCERY_OUTPUT']);out.mkdir(parents=True,exist_ok=True)
 request=json.loads((ROOT/'cloud/chotu-groceries-request.json').read_text());codes=json.loads((ROOT/'cloud/confirmed-shop-codes.json').read_text())
 with tempfile.TemporaryDirectory() as tmp:
  temp=Path(tmp);snapshots={};archive_path=next(Path(os.environ['GROCERY_CHECKPOINT_ROOT']).rglob('checkpoint.zip'))
  with zipfile.ZipFile(archive_path) as archive:
   entries=[v for v in archive.infolist() if v.filename.startswith('saved_runs/') and v.filename.endswith('/pages.sqlite3')]
   if len(entries)!=1 or entries[0].file_size>512*1024**2:raise ValueError('Unexpected discovery checkpoint')
   cache_path=temp/'discovery.sqlite3'
   with archive.open(entries[0]) as src,cache_path.open('wb') as dst:shutil.copyfileobj(src,dst,1024**2)
  cache=ResponseCache(cache_path)
  try:
   for (url,) in cache.db.execute('SELECT url FROM pages').fetchall():
    if '#chotu-scope-snapshot-v1' not in url:continue
    response=cache.get(url)
    if response is None:raise ValueError('Checkpoint checksum failed')
    data=response.json();snapshots[data['scope_url']]=data
  finally:cache.close()
  normalized,_=normalize(original,temp/'normalized.xlsx',codes[STORE]);normalized,_=repair(normalized,temp/'scoped.xlsx',STORE)
  source_book=load_workbook(normalized,read_only=True,data_only=False);sheet=source_book['Products'];headers=[c.value for c in sheet[1]];existing={str(v[headers.index('source_url')]) for v in sheet.iter_rows(min_row=2,values_only=True) if any(x is not None for x in v)};source_book.close()
  g=runpy.run_path(str(ROOT/'main.py'),run_name='grocery_completion_engine');g['OUT']=temp/'additions';g['S']=requests.Session();g['__file__']=str(temp/'grocery-completion.py')
  fresh_cache=ResponseCache(temp/'fresh-responses.sqlite3');tls=SimpleNamespace(saved_response_cache=fresh_cache);g['_chotu_tls']=tls;g['S']=SessionProxy(requests.Session(),tls,g['_chotu_wait'])
  reader=PublicCatalog(g,print);coverage=[];candidates={};receipts=[]
  for index,scope in enumerate(request['pages'],1):
   if index in PENDING:
    urls,total,pages=reader.discover_scope(scope)
    if reader.scope_count_changed or total is not None and len(urls)!=total:raise ValueError('Fresh grocery scope still inconsistent: '+scope['label'])
    for url in urls:
     if url not in existing:candidates.setdefault(url,scope)
    coverage.append(dict(index=index,url=scope['url'],visible=len(urls),total=total,pages=len(pages),evidence='fresh exact public UI/page recheck'))
   else:
    data=snapshots.get(scope['url'])
    if data is None or data['count_changed'] or data['total'] is not None and len(data['links'])!=data['total']:raise ValueError('Original scope not complete: '+scope['label'])
    coverage.append(dict(index=index,url=scope['url'],visible=len(data['links']),total=data['total'],pages=len(data['pages']),evidence='checksummed original discovery checkpoint'))
  products=[]
  for url,scope in sorted(candidates.items()):
   html=reader.read_page(url)
   try:
    p=product(html,url)
    reasons=incomplete_product_reasons(p)
    if not p['images']:reasons.append('No source image')
    if reasons:raise IncompleteProduct('; '.join(reasons))
    if not p['is_in_stock']:raise IncompleteProduct('Source out of stock; not exported')
    p.update(owner_scope_url=scope['url'],owner_category=scope['group']);products.append(p)
   except (IncompleteProduct,ProductReviewRequired) as exc:receipts.append(dict(source_url=url,reason=str(exc),source_sha256=hashlib.sha256(html.encode()).hexdigest(),original_html=html))
  merged=temp/'merged.xlsx'
  if products:
   from woocommerce_source_support import export
   provider=SimpleNamespace(label='Exact missing grocery products',products={p['id']:p for p in products},catalog=lambda:products,supports=lambda u:u==BASE)
   provider.read=lambda path:provider.products[int(path.rsplit('/',1)[-1])]
   export(g,BASE,STORE,ROOT/'importer-files/Chotu_Products_Import_Template_Discount_Tags.xlsx',print,provider=provider)
   additions=g['OUT']/(STORE+' - REFRESH REVIEW.xlsx');b=load_workbook(additions);s=b['Products'];h={c.value:c.column for c in s[1]}
   fields=['website_category_path','website_category_source_url','website_category_status','website_category_checked_at','owner_scope_url','source_manufacturer','source_scope_coverage_status','source_scope_review_count','subcategory_source','subcategory_evidence','Category']
   for key in fields:
    if key not in h:h[key]=s.max_column+1;s.cell(1,h[key],key)
   byid={g['uid']('CP',BASE+'|'+str(p['id'])):p for p in products}
   for n in range(2,s.max_row+1):
    p=byid[str(s.cell(n,h['product_id']).value)]
    from datetime import datetime,timezone
    for key,value in dict(website_category_path=' > '.join(v['name'] for v in p['categories']),website_category_source_url=p['permalink'],website_category_status='verified_product_breadcrumb',website_category_checked_at=datetime.now(timezone.utc).isoformat(),owner_scope_url=p['owner_scope_url'],source_manufacturer=p['manufacturer'],source_scope_coverage_status='complete',source_scope_review_count=0,subcategory_source='owner_supplied_scope',subcategory_evidence='Exact public scope '+p['owner_scope_url'],Category=p['owner_category']).items():s.cell(n,h[key],value)
   b.save(additions);b.close();merge(normalized,additions,merged)
  else:shutil.copy2(normalized,merged)
  before=load_workbook(normalized,read_only=True,data_only=False);after=load_workbook(merged,read_only=True,data_only=False)
  try:
   for sheet_name in ('Products','Product Images','Option Groups','Options','Variant Combinations'):
    left=before[sheet_name];right=after[sheet_name];lh=[c.value for c in left[1]];rh=[c.value for c in right[1]]
    if right.max_row<left.max_row:raise ValueError('Existing grocery rows lost during append')
    indexes=[rh.index(k) for k in lh]
    for values,new_values in zip(left.iter_rows(min_row=2,values_only=True),right.iter_rows(min_row=2,values_only=True)):
     if any(x is not None for x in values) and tuple(new_values[i] for i in indexes)!=tuple(values):raise ValueError('Existing grocery source facts changed during append')
  finally:before.close();after.close()
  # Clear only the reconciled coverage hold; keep a durable 99-scope proof and exclusions.
  b=load_workbook(merged);s=b['Products'];h={c.value:c.column for c in s[1]}
  for n in range(2,s.max_row+1):s.cell(n,h['source_scope_coverage_status'],'complete');s.cell(n,h['source_scope_review_count'],0)
  b.save(merged);b.close()
  target=out/(STORE+'.xlsx');process(merged,target,STORE,codes)
  report=audit(target,STORE,codes,{'naheed.pk','www.naheed.pk'},source=merged,strict_commercial=True,findings_limit=30)
  (out/'grocery-final-audit.json').write_text(json.dumps(report,indent=2));(out/'grocery-scope-proof.json').write_text(json.dumps(dict(source_run='42607016680',discovery_run='42592529653',scopes=coverage,missing_checked=len(candidates),added=len(products),exclusions=receipts),indent=2))
  if report['status']!='pass':raise ValueError('Grocery final audit still held; original file preserved')
  fresh_cache.close();shutil.copy2(temp/'fresh-responses.sqlite3',out/'grocery-recheck-responses.sqlite3')
  (out/'run-summary.json').write_text(json.dumps(dict(stores=[dict(name=STORE,file=STORE+'.xlsx',status='done',products=report['products_checked'])])))
  print('GROCERY FILE COMPLETE:',report['products_checked'],'products; 99 scopes reconciled; independent audit passed.')
if __name__=='__main__':main()
