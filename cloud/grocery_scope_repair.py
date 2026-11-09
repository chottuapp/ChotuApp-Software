"""Restore owner headings from retained exact grocery scope metadata; preserve coverage holds."""
from pathlib import Path
from urllib.parse import urlsplit
from openpyxl import load_workbook
from openpyxl.utils import get_column_letter
from grocery_owner_scope import categories

def repair(source,out,store):
 if store!='ChotuApp Groceries':return source,0
 from rule804_pipeline import toolkit
 tools=toolkit();book=load_workbook(source,read_only=True,data_only=False);patches={};count=0
 try:
  sheet=book['Products'];headers=list(next(sheet.iter_rows(values_only=True)));cols={k:i+1 for i,k in enumerate(headers)}
  required={'Category','owner_scope_url','source_url','source_manufacturer','subcategory_source','subcategory_evidence','source_scope_coverage_status','source_scope_review_count'}
  if not required<=set(headers):raise ValueError('Original grocery scope evidence missing; no guessed category repair')
  for number,values in enumerate(sheet.iter_rows(min_row=2,values_only=True),2):
   if not any(v is not None for v in values):continue
   row=dict(zip(headers,values));expected=categories().get(row['owner_scope_url']);url=urlsplit(str(row['source_url'] or ''))
   if not expected or url.scheme!='https' or url.hostname!='www.naheed.pk' or not row['source_manufacturer'] or row['source_scope_coverage_status'] not in ('complete','review_required'):raise ValueError('Grocery source scope identity cannot be restored')
   if row['subcategory_source'] in ('manual','owner','manual_override'):
    if row['Category']!=expected:raise ValueError('Owner category override conflict; review required')
    continue
   if row['Category']==expected and row['subcategory_source']=='owner_supplied_scope' and ('subcategory' not in cols or row.get('subcategory')==expected):continue
   changes={'Category':expected,'subcategory_source':'owner_supplied_scope','subcategory_evidence':'Owner-provided heading restored from exact retained scope '+row['owner_scope_url']+'; source coverage status and review count preserved. Original metadata: '+str(row.get('subcategory_evidence') or '')}
   if 'subcategory' in cols:changes['subcategory']=expected
   changed=False
   for key,value in changes.items():
    if row.get(key)!=value:patches[get_column_letter(cols[key])+str(number)]=value;changed=True
   count+=int(changed)
 finally:book.close()
 if not patches:return source,0
 out=Path(out);out.parent.mkdir(parents=True,exist_ok=True);part=tools.patch_sheet(source,out,patches);tools.verify(source,out,part,patches)
 return out,count
