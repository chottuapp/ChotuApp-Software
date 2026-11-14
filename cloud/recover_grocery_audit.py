"""Rebuild from immutable supplier input; a failed preview is never source truth."""
import hashlib,json,os,runpy,shutil,tempfile
from pathlib import Path
from types import SimpleNamespace
import requests
from openpyxl import load_workbook
from drive_sync import gh,REPO
from chotu_groceries_source_support import STORE,BASE,PublicCatalog,product
from naheed_brand_support import load_request,select_brand_category
from complete_naheed_brand_export import restore_missing_categories,append_source_products,verify_old_values
from legacy_original_schema import normalize
from grocery_scope_repair import repair
from rule804_pipeline import process
from audit804 import run as audit
from incomplete_products import exclude
from resume_support import ResponseCache,SessionProxy
ROOT=Path(__file__).resolve().parents[1]
ALLOWED_AUDIT_ISSUE='Export Category differs from owner grocery scope'

def validate_recovery(report,proof,preview):
 if report.get('status')!='hold' or report.get('details_truncated') or report.get('findings_count')!=len(report.get('findings',[])) or not report.get('findings'):raise ValueError('Saved audit is not a complete category-only recovery finding')
 if report.get('workbook_sha256')!=hashlib.sha256(Path(preview).read_bytes()).hexdigest():raise ValueError('Saved audit does not match the exact preview checksum')
 for finding in report['findings']:
  if set(finding.get('issues',[]))!={ALLOWED_AUDIT_ISSUE}:raise ValueError('Protected audit findings cannot be waived by category recovery')
 scopes={s['url'] for s in load_request()['brands']};coverage=proof.get('coverage',{})
 if set(coverage)!=scopes:raise ValueError('Saved proof omits an approved brand scope')
 for row in coverage.values():
  if row.get('complete') is not True or not (row.get('visible')==row.get('total') or row.get('visible')==0 and row.get('total') is None):raise ValueError('Unresolved source coverage cannot be promoted')

def product_rows(path):
 b=load_workbook(path,read_only=True,data_only=False)
 try:
  it=b['Products'].iter_rows(values_only=True);h=next(it);result={}
  for values in it:
   if not any(v is not None for v in values):continue
   row=dict(zip(h,values));pid=str(row.get('product_id') or '')
   if not pid or pid in result:raise ValueError('Missing/duplicate source product identity')
   result[pid]=row
  return result
 finally:b.close()

def main():
 rid=os.environ['GROCERY_AUDITED_RECOVERY_RUN'];source_run=os.environ['GROCERY_SOURCE_RUN']
 if not rid.isdigit():raise ValueError('Exact saved audit recovery run required')
 run=json.loads(gh('api','repos/'+REPO+'/actions/runs/'+rid))
 if run.get('status')!='completed' or run.get('head_branch')!='main' or run.get('path')!='.github/workflows/cloud-grocery-complete.yml' or run.get('event')!='workflow_dispatch' or run.get('head_repository',{}).get('full_name')!=REPO:raise ValueError('Untrusted saved audit source')
 root=Path(os.environ['GROCERY_AUDITED_RECOVERY_ROOT']);preview=root/'grocery-audited-preview.xlsx';proof=json.loads((root/'grocery-completion-proof.json').read_text());previous=json.loads((root/'grocery-final-audit.json').read_text())
 if proof.get('source_run')!=source_run:raise ValueError('Saved proof belongs to another source fetch')
 validate_recovery(previous,proof,preview)
 originals=list(Path(os.environ['GROCERY_EXPORT_ROOT']).rglob(STORE+'.xlsx'))
 if len(originals)!=1:raise ValueError('Exact original workbook required')
 original=originals[0];before=product_rows(original);saved=product_rows(preview)
 # Preview supplies candidate identities only. Categories, descriptions and
 # commercial values are rebuilt from original data or new exact supplier reads.
 new_candidates={pid:r for pid,r in saved.items() if pid not in before}
 if len(new_candidates)!=proof.get('new_products'):raise ValueError('Saved new-product candidate count mismatch')
 out=Path(os.environ['GROCERY_OUTPUT']);out.mkdir(parents=True,exist_ok=True);codes=json.loads((ROOT/'cloud/confirmed-shop-codes.json').read_text())
 with tempfile.TemporaryDirectory() as tmp:
  temp=Path(tmp);g=runpy.run_path(str(ROOT/'main.py'),run_name='saved_source_audit_recovery');g.update(OUT=temp/'additions',__file__=str(temp/'recovery.py'))
  cache=ResponseCache(temp/'responses.sqlite3');tls=SimpleNamespace(saved_response_cache=cache);g['_chotu_tls']=tls;g['S']=SessionProxy(requests.Session(),tls,g['_chotu_wait']);reader=PublicCatalog(g,print,brand_refresh=True)
  normalized,_=normalize(original,temp/'normalized.xlsx',codes[STORE]);category_proof=restore_missing_categories(normalized,temp/'category-source.xlsx',reader,g);source,_=repair(temp/'category-source.xlsx',temp/'verified-category-source.xlsx',STORE)
  scopes=load_request()['brands'];new_products=[]
  for pid,candidate in new_candidates.items():
   html=reader.read_page(candidate['source_url']);p=product(html,candidate['source_url'])
   if g['uid']('CP',BASE+'|'+str(p['id']))!=pid:raise ValueError('New candidate supplier identity changed')
   p['owner_scope_url'],p['owner_category']=select_brand_category(p,scopes)
   if not p['is_in_stock'] or not p['images']:raise ValueError('New candidate current source availability/image requires review')
   new_products.append(p)
  merged=temp/'complete-source.xlsx';append_source_products(g,source,new_products,merged,codes)
  b=load_workbook(merged);s=b['Products'];h={c.value:c.column for c in s[1]}
  for n in range(2,s.max_row+1):s.cell(n,h['source_scope_coverage_status'],'complete');s.cell(n,h['source_scope_review_count'],0)
  b.save(merged);b.close();verify_old_values(original,merged)
  target=out/(STORE+'.xlsx');shutil.copy2(merged,target)
  checked=out/'grocery-audited-preview.xlsx';process(merged,checked,STORE,codes);report=audit(checked,STORE,codes,{'www.naheed.pk','naheed.pk'},source=merged,strict_commercial=True,findings_limit=None)
  filtered_source,filtered_output,unclear=exclude(merged,checked,STORE,report,temp/'unclear')
  if unclear:
   report=audit(filtered_output,STORE,codes,{'www.naheed.pk','naheed.pk'},source=filtered_source,strict_commercial=True,findings_limit=None);shutil.copy2(filtered_output,checked)
  cache.close();shutil.copy2(temp/'responses.sqlite3',out/'grocery-recovery-source-responses.sqlite3')
  (out/'grocery-final-audit.json').write_text(json.dumps(report,indent=2))
  (out/'grocery-audit-recovery-proof.json').write_text(json.dumps(dict(original_source_run=source_run,original_source_sha256=hashlib.sha256(original.read_bytes()).hexdigest(),prior_failed_audit_run=rid,prior_failed_findings=previous['findings'],scope_proof=proof['coverage'],category_repairs=category_proof,new_supplier_products=len(new_products),current_incomplete_products=unclear,original_commercial_description_and_linked_values_verified=True,failed_preview_used_as_source=False),indent=2))
  if report['status']!='pass':raise ValueError('Independent original-source audit remains held; old verified file retained')
  (out/'completion-manifest.json').write_text(json.dumps({'files':[dict(store=STORE,name=target.name,complete=True,sha256=hashlib.sha256(target.read_bytes()).hexdigest())]}))
  (out/'run-summary.json').write_text(json.dumps(dict(stores=[dict(name=STORE,status='done',file=target.name,products=len(before)+len(new_products),review_required=True)])))
  print('ORIGINAL SOURCE RE-AUDIT PASS:',report['products_checked'],'products; successful scope receipts reused; no complete product refetch')
if __name__=='__main__':main()
