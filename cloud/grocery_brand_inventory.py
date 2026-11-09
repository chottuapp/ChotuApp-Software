"""Read the requested grocery workbook; publish only a sealed-box encrypted brand list."""
import base64,ctypes,ctypes.util,json,os
from collections import Counter
from pathlib import Path
from urllib.parse import urlsplit
from openpyxl import load_workbook
from source_research import publish

def main():
 paths=list(Path(os.environ['GROCERY_EXPORT_ROOT']).rglob('ChotuApp Groceries.xlsx'))
 if len(paths)!=1:raise ValueError('Unique requested grocery workbook required')
 key=base64.b64decode(os.environ['REPORT_PUBLIC_KEY'],validate=True)
 if len(key)!=32:raise ValueError('Invalid report encryption public key')
 book=load_workbook(paths[0],read_only=True,data_only=True)
 try:
  sheet=book['Products'];rows=sheet.iter_rows(values_only=True);headers=next(rows)
  if 'source_manufacturer' not in headers:raise ValueError('Original manufacturer evidence column missing; no title guessing')
  brands=Counter();names={};missing=0;count=0;ids=set();coverage=Counter()
  for values in rows:
   row=dict(zip(headers,values))
   if not any(values):continue
   count+=1
   if count>10000:raise ValueError('Grocery workbook read bound exceeded')
   if urlsplit(str(row.get('source_url') or '')).hostname!='www.naheed.pk':raise ValueError('Non-grocery row; stop inspection')
   pid=str(row.get('product_id') or '')
   if not pid or pid in ids:raise ValueError('Missing/duplicate source product identity')
   coverage[(str(row.get('source_scope_coverage_status')),str(row.get('source_scope_review_count')))]+=1
   ids.add(pid);name=str(row.get('source_manufacturer') or '').strip()
   if not name:missing+=1;continue
   norm=name.casefold();names.setdefault(norm,name);brands[norm]+=1
  report=dict(source_run='42607016680',file='ChotuApp Groceries.xlsx',products=count,missing_manufacturer=missing,brands=[dict(name=names[k],products=brands[k]) for k in sorted(brands)])
 finally:book.close()
 report['coverage_statuses']=[dict(status=k[0],review_count=k[1],products=v) for k,v in coverage.items()]
 import tempfile,csv
 from legacy_original_schema import normalize
 from rule804_pipeline import process
 from audit804 import run as audit
 root=Path(__file__).resolve().parents[1];codes=json.loads((root/'cloud/confirmed-shop-codes.json').read_text())
 with tempfile.TemporaryDirectory() as tmp:
  normalized,_=normalize(paths[0],Path(tmp)/'normalized.xlsx',codes['ChotuApp Groceries'])
  output=Path(tmp)/'reviewed.xlsx';processing=process(normalized,output,'ChotuApp Groceries',codes)
  result=audit(output,'ChotuApp Groceries',codes,{'naheed.pk','www.naheed.pk'},source=normalized,strict_commercial=True,findings_limit=12)
  report['audit']=result;report['processing']=processing
 report['scope_files']=[]
 for path in Path(os.environ['GROCERY_EXPORT_ROOT']).rglob('*SCOPE COVERAGE.csv'):
  with path.open(encoding='utf-8-sig',newline='') as stream:report['scope_files'].append(dict(name=path.name,rows=list(csv.DictReader(stream))))
 checkpoint_root=os.environ.get('GROCERY_CHECKPOINT_ROOT')
 if checkpoint_root:
  import zipfile
  from resume_support import ResponseCache
  files=list(Path(checkpoint_root).rglob('checkpoint.zip'))
  if len(files)!=1:raise ValueError('Exact grocery checkpoint required')
  scope_map={}
  with zipfile.ZipFile(files[0]) as archive,tempfile.TemporaryDirectory() as tmp:
   entries=[v for v in archive.infolist() if v.filename.startswith('saved_runs/') and v.filename.endswith('/pages.sqlite3')]
   if not 1<=len(entries)<=2 or sum(v.file_size for v in entries)>256*1024**2:raise ValueError('Checkpoint diagnostic exceeds bounds')
   for index,entry in enumerate(entries):
    path=Path(tmp)/(str(index)+'.sqlite3');path.write_bytes(archive.read(entry));cache=ResponseCache(path)
    try:
     urls=[v[0] for v in cache.db.execute('SELECT url FROM pages') if '#chotu-scope-snapshot-v1' in v[0]]
     for url in urls:
      response=cache.get(url)
      if response is None:raise ValueError('Scope checkpoint checksum failed')
      value=response.json();scope_map[value['scope_url']]=dict(visible_products=len(value['links']),reported_total=value['total'],pages=len(value['pages']),count_changed=value['count_changed'],reported_totals=value['totals'])
    finally:cache.close()
  scope_request=json.loads((root/'cloud/chotu-groceries-request.json').read_text())
  report['scope_checkpoint']=[dict(**scope,checkpoint=scope_map.get(scope['url'])) for scope in scope_request['pages']]
 data=json.dumps(report,ensure_ascii=False).encode();lib=ctypes.CDLL(ctypes.util.find_library('sodium'))
 if lib.sodium_init()<0:raise RuntimeError('Encryption unavailable')
 lib.crypto_box_seal.argtypes=[ctypes.c_void_p,ctypes.c_void_p,ctypes.c_ulonglong,ctypes.c_void_p]
 out=ctypes.create_string_buffer(len(data)+48)
 if lib.crypto_box_seal(out,data,len(data),key)!=0:raise RuntimeError('Report encryption failed')
 publish(dict(run_id=os.environ['GITHUB_RUN_ID'],source_run='42607016680',format='libsodium-sealed-box',encrypted_payload=base64.b64encode(out.raw).decode()),branch='chotu-groceries-reports')
 print('Requested grocery brand list encrypted; no plaintext workbook or brands published.')
if __name__=='__main__':main()
