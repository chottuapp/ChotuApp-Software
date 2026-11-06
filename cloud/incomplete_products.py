"""Quarantine only exact, source-bound incomplete products; retain independent audit."""
from pathlib import Path
from owner_product_exclusions import apply

INCOMPLETE_ISSUES={
 'Missing product name',
 'Description exceeds Excel cell capacity',
 'Description lacks enough product-specific content for review',
 'Placeholder description',
 'Category blank or unresolved',
 'Category is too broad or promotional for product-purpose classification',
 'Category lacks clear product-purpose evidence; manual review required',
 'Brand name used as product Category',
 'Store name used as product Category',
 'Bundle appears classified as a single component',
}

def exclude(source,output,store,report,stage):
 """Remove eligible Products and all linked rows from BOTH audit inputs.

 Never waive an audit finding. Re-audit the filtered output against the filtered
 source; price, stock, identity, numeric-loss and conflicting-fact errors stay held.
 The caller retains the original source and publishes the exclusion receipt.
 """
 grouped={}
 for finding in report.get('findings',[]):
  pid=str(finding.get('product_id') or '')
  if not pid:continue
  if pid not in grouped:grouped[pid]=dict(finding,issues=list(finding.get('issues') or []))
  else:grouped[pid]['issues']=list(dict.fromkeys(grouped[pid]['issues']+list(finding.get('issues') or [])))
 def eligible(finding):
  issues=set(finding.get('issues') or [])
  allowed=INCOMPLETE_ISSUES|({'Description readability: split dense prose into clear paragraphs without losing facts'} if 'Description exceeds Excel cell capacity' in issues else set())
  return bool(issues) and issues<=allowed
 candidates=[f for f in grouped.values() if eligible(f)]
 if not candidates:return source,output,[]
 from audit804 import rows
 originals={str(r.get('product_id')):r for r in rows(source)}
 selected={}
 for finding in candidates:
  pid=str(finding.get('product_id') or '');issues=finding.get('issues') or []
  if not pid or not eligible(finding):continue
  row=originals.get(pid)
  if row is None or finding.get('source_url')!=row.get('source_url') or finding.get('name')!=str(row.get('name') or ''):raise ValueError('Incomplete product exclusion identity mismatch')
  selected[pid]=dict(source_url=row['source_url'],name=finding['name'],issues=issues)
 if not selected:return source,output,[]
 stage=Path(stage)
 filtered_source,_=apply(source,stage/'source.xlsx',store,incomplete=selected)
 filtered_output,_=apply(output,stage/'output.xlsx',store,incomplete=selected)
 return filtered_source,filtered_output,[dict(product_id=pid,**entry) for pid,entry in selected.items()]


def save_receipt(exclusions,store,campaign,source_run,source_sha,stage,save):
 """Keep every skipped identity/reason durably; bound the public status summary."""
 from openpyxl import Workbook
 book=Workbook();sheet=book.active;sheet.title='Incomplete Products'
 sheet.append(['product_id','name','source_url','reasons','original_source_sha256'])
 for entry in exclusions:
  values=[entry['product_id'],entry['name'],entry['source_url'],'; '.join(entry['issues']),source_sha]
  sheet.append(values)
  for cell in sheet[sheet.max_row]:cell.data_type='s'
 path=Path(stage)/'incomplete-products.xlsx';book.save(path);book.close()
 return save(path,store+'-incomplete-products',campaign,source_run)
