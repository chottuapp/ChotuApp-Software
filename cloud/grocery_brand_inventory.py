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
  brands=Counter();names={};missing=0;count=0;ids=set()
  for values in rows:
   row=dict(zip(headers,values))
   if not any(values):continue
   count+=1
   if count>10000:raise ValueError('Grocery workbook read bound exceeded')
   if urlsplit(str(row.get('source_url') or '')).hostname!='www.naheed.pk':raise ValueError('Non-grocery row; stop inspection')
   pid=str(row.get('product_id') or '')
   if not pid or pid in ids:raise ValueError('Missing/duplicate source product identity')
   ids.add(pid);name=str(row.get('source_manufacturer') or '').strip()
   if not name:missing+=1;continue
   norm=name.casefold();names.setdefault(norm,name);brands[norm]+=1
  report=dict(source_run='42607016680',file='ChotuApp Groceries.xlsx',products=count,missing_manufacturer=missing,brands=[dict(name=names[k],products=brands[k]) for k in sorted(brands)])
 finally:book.close()
 data=json.dumps(report,ensure_ascii=False).encode();lib=ctypes.CDLL(ctypes.util.find_library('sodium'))
 if lib.sodium_init()<0:raise RuntimeError('Encryption unavailable')
 lib.crypto_box_seal.argtypes=[ctypes.c_void_p,ctypes.c_void_p,ctypes.c_ulonglong,ctypes.c_void_p]
 out=ctypes.create_string_buffer(len(data)+48)
 if lib.crypto_box_seal(out,data,len(data),key)!=0:raise RuntimeError('Report encryption failed')
 publish(dict(run_id=os.environ['GITHUB_RUN_ID'],source_run='42607016680',format='libsodium-sealed-box',encrypted_payload=base64.b64encode(out.raw).decode()),branch='chotu-groceries-reports')
 print('Requested grocery brand list encrypted; no plaintext workbook or brands published.')
if __name__=='__main__':main()
