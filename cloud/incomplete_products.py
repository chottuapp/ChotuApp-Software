"""Quarantine only exact, source-bound incomplete products; retain independent audit."""
from pathlib import Path
from owner_product_exclusions import apply

INCOMPLETE_ISSUES={
 'Missing product name',
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
 candidates=[f for f in report.get('findings',[]) if f.get('product_id') and f.get('issues') and set(f['issues'])<=INCOMPLETE_ISSUES]
 if not candidates:return source,output,[]
 from audit804 import rows
 originals={str(r.get('product_id')):r for r in rows(source)}
 selected={}
 for finding in candidates:
  pid=str(finding.get('product_id') or '');issues=finding.get('issues') or []
  if not pid or not issues or not set(issues)<=INCOMPLETE_ISSUES:continue
  row=originals.get(pid)
  if row is None or finding.get('source_url')!=row.get('source_url') or finding.get('name')!=str(row.get('name') or ''):raise ValueError('Incomplete product exclusion identity mismatch')
  selected[pid]=dict(source_url=row['source_url'],name=finding['name'],issues=issues)
 if not selected:return source,output,[]
 stage=Path(stage)
 filtered_source,_=apply(source,stage/'source.xlsx',store,incomplete=selected)
 filtered_output,_=apply(output,stage/'output.xlsx',store,incomplete=selected)
 return filtered_source,filtered_output,[dict(product_id=pid,**entry) for pid,entry in selected.items()]
