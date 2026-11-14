"""Finish saved brand-mode Naheed data: unresolved scopes and missing products only."""
import csv,hashlib,json,os,runpy,shutil,tempfile
from pathlib import Path
from types import SimpleNamespace
from datetime import datetime,timezone
import requests
from bs4 import BeautifulSoup
from openpyxl import load_workbook
from naheed_brand_support import load_request,brand_scope_identity,authorized_brand_category,select_brand_category,brand_key
from chotu_groceries_source_support import PublicCatalog,product,IncompleteProduct,ProductReviewRequired,BASE,STORE,norm
from grocery_browser_support import ListingRenderIncomplete
from resume_support import ResponseCache,SessionProxy
from legacy_original_schema import normalize
from grocery_scope_repair import repair
from complete_grocery_export import merge
from rule804_pipeline import process
from audit804 import run as audit
from incomplete_products import exclude
ROOT=Path(__file__).resolve().parents[1]

def saved_coverage(root,scopes):
 paths=list(Path(root).rglob('*SCOPE COVERAGE.csv'))
 if len(paths)!=1:raise ValueError('Unique original scope receipt required')
 with paths[0].open(encoding='utf-8-sig',newline='') as f:rows=list(csv.DictReader(f))
 result={}
 for row in rows:
  url=row['scope_url']
  if url not in scopes or url in result:raise ValueError('Saved brand scope identity mismatch')
  visible=int(row['products']);pages=int(row['pages']);total=int(row['reported_total']) if row['reported_total'] else None
  if visible<0 or pages<1 or total is not None and total<0:raise ValueError('Invalid scope receipt counts')
  complete=row['coverage_status']=='complete' and (total==visible or total is None and visible==0)
  result[url]=dict(visible=visible,pages=pages,total=total,complete=complete)
 if set(result)!=set(scopes):raise ValueError('Saved receipt does not cover all requested brands')
 return result

def rows(path):
 b=load_workbook(path,read_only=True,data_only=False)
 try:
  iterator=b['Products'].iter_rows(values_only=True);headers=next(iterator)
  return [dict(zip(headers,v)) for v in iterator if any(x is not None for x in v)]
 finally:b.close()

def restore_missing_categories(source,target,reader,g):
 b=load_workbook(source);sheet=b['Products'];h={c.value:c.column for c in sheet[1]};proof=[]
 try:
  for n in range(2,sheet.max_row+1):
   row={k:sheet.cell(n,c).value for k,c in h.items()}
   if not brand_scope_identity(row):raise ValueError('Saved manufacturer identity differs from approved brand scope')
   if row.get('website_category_path') and row.get('website_category_status')=='verified_product_breadcrumb':continue
   html=reader.read_page(row['source_url']);soup=BeautifulSoup(html,'html.parser');canonical=soup.select_one('link[rel=canonical][href]');title=soup.select_one('h1');brand=soup.select_one('.product-info-main .brand-name a');box=soup.select_one('.product-info-main [data-role=priceBox][data-product-id]')
   if not canonical or canonical['href'].rstrip('/')!=row['source_url'].rstrip('/') or not title or norm(title.get_text(' ',strip=True))!=norm(row['name']) or not brand or brand_key(brand.get_text(' ',strip=True))!=brand_key(row['source_manufacturer']) or not box or g['uid']('CP',BASE+'|'+str(box['data-product-id']))!=row['product_id']:raise ValueError('Missing category source product identity cannot be independently verified')
   from website_category_support import breadcrumb
   evidence=breadcrumb(soup,row['source_url'])
   if not evidence:raise ValueError('Current exact product breadcrumb unavailable; no category guessed')
   for key in ('website_category_path','website_category_source_url','website_category_status','website_category_checked_at'):sheet.cell(n,h[key],evidence[key])
   proof.append(dict(source_url=row['source_url'],response_sha256=hashlib.sha256(html.encode()).hexdigest(),website_category_path=evidence['website_category_path']))
  b.save(target)
 finally:b.close()
 return proof

def verify_old_values(before,after):
 allowed={'Category','category','subcategory','subcategory_source','subcategory_evidence','subcategory_checked_at','website_category_path','website_category_source_url','website_category_status','website_category_checked_at','source_scope_coverage_status','source_scope_review_count'}
 left=load_workbook(before,read_only=True,data_only=False);right=load_workbook(after,read_only=True,data_only=False)
 try:
  for name in ('Products','Product Images','Option Groups','Options','Variant Combinations'):
   a=left[name];b=right[name];ah=[c.value for c in a[1]];bh=[c.value for c in b[1]]
   if b.max_row<a.max_row:raise ValueError('Existing grocery rows lost')
   compare=[(i,bh.index(k)) for i,k in enumerate(ah) if name!='Products' or k not in allowed]
   for old,new in zip(a.iter_rows(min_row=2,values_only=True),b.iter_rows(min_row=2,values_only=True)):
    if any(old[i]!=new[j] for i,j in compare):raise ValueError('Existing source commercial/description/linked facts changed during completion')
 finally:left.close();right.close()

def append_source_products(g,source,products,target,codes):
 """Append only independently read new supplier products; old rows stay intact."""
 if not products:shutil.copy2(source,target);return
 from woocommerce_source_support import export
 provider=SimpleNamespace(label='Exact source-verified missing Naheed products',products={p['id']:p for p in products},supports=lambda u:u==BASE,catalog=lambda:products)
 provider.read=lambda path:provider.products[int(path.rsplit('/',1)[-1])]
 export(g,BASE,STORE,ROOT/'importer-files/Chotu_Products_Import_Template_Discount_Tags.xlsx',print,provider=provider)
 extra=g['OUT']/(STORE+' - REFRESH REVIEW.xlsx');b=load_workbook(extra);s=b['Products'];h={c.value:c.column for c in s[1]};byid={g['uid']('CP',BASE+'|'+str(p['id'])):p for p in products}
 for number in range(2,s.max_row+1):
  p=byid[s.cell(number,h['product_id']).value];path=' > '.join(c['name'] for c in p['categories'])
  values=dict(shop_code=codes[STORE],Category=p['owner_category'],source_manufacturer=p['manufacturer'],owner_scope_url=p['owner_scope_url'],subcategory_source='owner_brand_search',subcategory_evidence='Exact selected manufacturer and actual supplier breadcrumb: '+path,website_category_path=path,website_category_source_url=p['permalink'],website_category_status='verified_product_breadcrumb',website_category_checked_at=datetime.now(timezone.utc).isoformat(),source_scope_coverage_status='complete',source_scope_review_count=0)
  for key,value in values.items():
   if key not in h:h[key]=s.max_column+1;s.cell(1,h[key],key)
   s.cell(number,h[key],value)
 b.save(extra);b.close();merge(source,extra,target)

def main():
 csv.field_size_limit(8*1024*1024)
 source_root=Path(os.environ['GROCERY_EXPORT_ROOT']);sources=list(source_root.rglob(STORE+'.xlsx'))
 if len(sources)!=1:raise ValueError('Exact completed grocery workbook required')
 out=Path(os.environ['GROCERY_OUTPUT']);out.mkdir(parents=True,exist_ok=True);request=load_request();scopes={s['url']:s for s in request['brands']};coverage=saved_coverage(source_root,scopes)
 codes=json.loads((ROOT/'cloud/confirmed-shop-codes.json').read_text())
 with tempfile.TemporaryDirectory() as tmp:
  temp=Path(tmp);g=runpy.run_path(str(ROOT/'main.py'),run_name='naheed_saved_completion');g.update(OUT=temp/'additions',__file__=str(temp/'completion.py'))
  cache=ResponseCache(temp/'responses.sqlite3');tls=SimpleNamespace(saved_response_cache=cache);g['_chotu_tls']=tls;g['S']=SessionProxy(requests.Session(),tls,g['_chotu_wait']);reader=PublicCatalog(g,print,brand_refresh=True)
  normalized,_=normalize(sources[0],temp/'normalized.xlsx',codes[STORE]);category_proof=restore_missing_categories(normalized,temp/'category-proof.xlsx',reader,g);normalized,_=repair(temp/'category-proof.xlsx',temp/'source.xlsx',STORE)
  original_rows=rows(normalized);existing={r['source_url'] for r in original_rows};ids={r['product_id'] for r in original_rows};candidates={};failures=[]
  pending=[u for u,v in coverage.items() if not v['complete']]
  if len(pending)!=max(int(r.get('source_scope_review_count') or 0) for r in original_rows):raise ValueError('Original brand review receipts disagree; scope repair must not silently skip a brand')
  for index,url in enumerate(pending,1):
   scope=scopes[url]
   try:
    links,total,pages=reader.discover_scope(scope)
    if reader.scope_count_changed or total is None and links or total is not None and len(links)!=total:raise ListingRenderIncomplete('Source brand count remains inconsistent')
    coverage[url]=dict(visible=len(links),pages=len(pages),total=total,complete=True,evidence=reader.brand_proofs[-1])
    for link in links:
     if link not in existing:candidates.setdefault(link,[]).append(scope)
   except ListingRenderIncomplete as exc:failures.append(dict(scope_url=url,brand=scope['brand'],reason=str(exc)))
   (out/'grocery-scope-progress.json').write_text(json.dumps(dict(source_run=os.environ['GROCERY_SOURCE_RUN'],coverage=coverage,failures=failures,candidate_urls={u:[v['url'] for v in members] for u,members in candidates.items()}),indent=2))
   print('SAVED BRAND REPAIR:',index,'/',len(pending),scope['brand'],'unresolved',len(failures),flush=True)
  if failures:raise ValueError('Unresolved brand scopes retained; no full catalog approval: '+', '.join(v['brand'] for v in failures))
  prior_excluded=set()
  for path in source_root.rglob('*.csv'):
   if not any(s in path.name for s in ('INCOMPLETE PRODUCTS','SOURCE PRODUCT REVIEW','OWNER PHOTO HOLDS')):continue
   with path.open(encoding='utf-8-sig',newline='') as f:
    for row in csv.DictReader(f):
     if row.get('source_url'):prior_excluded.add(row['source_url'])
  additions=[];receipts=[]
  for index,(url,matches) in enumerate(sorted(candidates.items()),1):
   if url in prior_excluded:continue
   html=reader.read_page(url)
   try:
    p=product(html,url);p['owner_scope_url'],p['owner_category']=select_brand_category(p,matches);p['owner_scope_policy']='owner_brand_search'
    from locked_store_rules import incomplete_product_reasons
    reasons=incomplete_product_reasons(p)
    if not p['images']:reasons.append('Missing source image')
    if not p['is_in_stock']:reasons.append('Source out of stock')
    if reasons:raise IncompleteProduct('; '.join(reasons))
    pid=g['uid']('CP',BASE+'|'+str(p['id']))
    if pid in ids:continue
    ids.add(pid);additions.append(p)
   except (IncompleteProduct,ProductReviewRequired,ValueError) as exc:receipts.append(dict(source_url=url,reason=str(exc),response_sha256=hashlib.sha256(html.encode()).hexdigest()))
   if index%25==0:print('MISSING SOURCE PRODUCTS:',index,'/',len(candidates),'new retained',len(additions),flush=True)
  merged=temp/'merged.xlsx'
  if additions:
   from woocommerce_source_support import export
   provider=SimpleNamespace(label='Verified missing selected Naheed brand products',products={p['id']:p for p in additions},supports=lambda u:u==BASE,catalog=lambda:additions)
   provider.read=lambda path:provider.products[int(path.rsplit('/',1)[-1])]
   export(g,BASE,STORE,ROOT/'importer-files/Chotu_Products_Import_Template_Discount_Tags.xlsx',print,provider=provider)
   extra=g['OUT']/(STORE+' - REFRESH REVIEW.xlsx');b=load_workbook(extra);s=b['Products'];h={c.value:c.column for c in s[1]};byid={g['uid']('CP',BASE+'|'+str(p['id'])):p for p in additions}
   for number in range(2,s.max_row+1):
    p=byid[s.cell(number,h['product_id']).value];path=' > '.join(c['name'] for c in p['categories'])
    metadata=dict(shop_code=codes[STORE],Category=p['owner_category'],source_manufacturer=p['manufacturer'],owner_scope_url=p['owner_scope_url'],subcategory_source='owner_brand_search',subcategory_evidence='Verified exact selected source manufacturer; actual product breadcrumb '+path,website_category_path=path,website_category_source_url=p['permalink'],website_category_status='verified_product_breadcrumb',website_category_checked_at=datetime.now(timezone.utc).isoformat(),source_scope_coverage_status='complete',source_scope_review_count=0)
    for key,value in metadata.items():
     if key not in h:h[key]=s.max_column+1;s.cell(1,h[key],key)
     s.cell(number,h[key],value)
   b.save(extra);b.close();merge(normalized,extra,merged)
  else:shutil.copy2(normalized,merged)
  b=load_workbook(merged);s=b['Products'];h={c.value:c.column for c in s[1]}
  for number in range(2,s.max_row+1):s.cell(number,h['source_scope_coverage_status'],'complete');s.cell(number,h['source_scope_review_count'],0)
  b.save(merged);b.close();verify_old_values(sources[0],merged)
  shutil.copy2(merged,out/'grocery-complete-source.xlsx')
  preview=out/'grocery-audited-preview.xlsx';process(merged,preview,STORE,codes);report=audit(preview,STORE,codes,{'www.naheed.pk','naheed.pk'},source=merged,strict_commercial=True,findings_limit=None)
  filtered_source,filtered_output,unclear=exclude(merged,preview,STORE,report,temp/'unclear')
  if unclear:
   report=audit(filtered_output,STORE,codes,{'www.naheed.pk','naheed.pk'},source=filtered_source,strict_commercial=True,findings_limit=None);shutil.copy2(filtered_output,preview)
  (out/'grocery-final-audit.json').write_text(json.dumps(report,indent=2))
  (out/'grocery-completion-proof.json').write_text(json.dumps(dict(source_run=os.environ['GROCERY_SOURCE_RUN'],coverage=coverage,category_repairs=category_proof,new_products=len(additions),prior_exclusion_receipts_reused=len(prior_excluded),new_exclusions=receipts,unclear_products=unclear),indent=2))
  if report['status']!='pass':raise ValueError('Independent grocery audit still held; original source and checked evidence preserved')
  target=out/(STORE+'.xlsx');shutil.copy2(merged,target)
  cache.close();shutil.copy2(temp/'responses.sqlite3',out/'grocery-recovery-responses.sqlite3')
  old_audits=source_root/'audits'
  if old_audits.exists():shutil.copytree(old_audits,out/'previous-audits')
  (out/'completion-manifest.json').write_text(json.dumps({'files':[dict(store=STORE,name=target.name,complete=True,sha256=hashlib.sha256(target.read_bytes()).hexdigest())]}))
  (out/'run-summary.json').write_text(json.dumps(dict(stores=[dict(name=STORE,status='done',file=target.name,products=len(rows(target)),review_required=True,audited_preview_products=report['products_checked'])])))
  print('SAVED NAHEED BRANDS COMPLETE; independent Drive pipeline must persist original and re-audit before replacement.',flush=True)
if __name__=='__main__':main()
