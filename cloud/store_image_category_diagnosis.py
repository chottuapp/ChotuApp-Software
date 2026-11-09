"""Read only two owner-requested catalog files and probe public product photos."""
import collections,hashlib,json,os,tempfile
from pathlib import Path
from urllib.parse import urlsplit,urlunsplit
import requests
from openpyxl import load_workbook
from drive_sync import config_text,drive_command,gh,REPO
from github_json import read_json
from source_research import publish
from hold804_repairs import category
from subcategory_inference_support import infer
STORES={'Mansab':'SE10079','Blackbeiger':'SE10074'}
def safe_url(url):
 p=urlsplit(url);return urlunsplit((p.scheme,p.netloc,p.path,'',''))
def probe(url):
 p=urlsplit(url);allowed={'wvwjldtqorvkgtkunble.supabase.co','mansabpk.com','www.mansabpk.com','cdn.shopify.com'}
 if p.scheme!='https' or p.hostname not in allowed or p.username or p.password:return dict(url=safe_url(url),status='outside_bounded_public_probe')
 result={'url':safe_url(url),'requests':[]}
 for mode,headers in [('normal',{}),('mobile',{'User-Agent':'Dart/3.5 (dart:io)'})]:
  try:
   with requests.get(url,headers=headers,timeout=(10,20),stream=True,allow_redirects=False) as r:
    prefix=next(r.iter_content(1024),b'')
    result['requests'].append(dict(mode=mode,status=r.status_code,content_type=r.headers.get('Content-Type'),bytes_sampled=len(prefix),sample_hex=prefix[:16].hex()))
  except requests.RequestException as exc:result['requests'].append(dict(mode=mode,error=type(exc).__name__))
 return result

def main():
 report=dict(run_id=os.environ['GITHUB_RUN_ID'],status='read_only_diagnosis',stores=[])
 state=read_json(gh,'repos/'+REPO+'/contents/latest.json?ref=drive-sync-reports')
 with tempfile.TemporaryDirectory() as tmp:
  root=Path(tmp);cfg=root/'rclone.conf';cfg.write_text(config_text(os.environ['CHOTU_DRIVE_RCLONE_CONFIG']));cfg.chmod(0o600)
  for store,code in STORES.items():
   entry=state['uploaded'][store]
   if entry['shop_code']!=code:raise ValueError('Requested shop identity mismatch')
   path=root/(store+'.xlsx');drive_command(cfg,'backend','copyid','chotudrive:',entry['file_id'],str(path))
   sha=hashlib.sha256(path.read_bytes()).hexdigest()
   if sha!=entry['sha256']:raise ValueError('Verified file changed since metadata; stop diagnosis')
   book=load_workbook(path,read_only=True,data_only=True);sheet=book['Products'];it=sheet.iter_rows(values_only=True);headers=next(it);rows=[dict(zip(headers,v)) for v in it if any(v)]
   if any(str(r.get('shop_code'))!=code for r in rows):raise ValueError('Mixed shop identity')
   item=dict(store=store,shop_code=code,sha256=sha,verified_utc=entry['verified_utc'],products=len(rows),categories=dict(collections.Counter(str(r.get('Category')) for r in rows)),samples=[],image_probes=[])
   for r in rows:
    if store=='Blackbeiger':
     item['samples'].append({k:r.get(k) for k in ('name','Category','description','source_url','subcategory_source','subcategory_evidence','website_category_path')})
     item['samples'][-1]['current_classifier']=category(r,store) or infer(r.get('name'),r.get('description'))
   if store=='Mansab':
    selected=[r for r in rows if any(w in str(r.get('name','')).lower() for w in ('mustard','ivory','turquoise'))][:3] or rows[:3]
    for r in selected:
     sample={k:r.get(k) for k in ('name','scraped_image_url (cover, auto)','final_image_url (cover/thumbnail — hosted link)','source_url')};item['samples'].append(sample)
     for k in ('scraped_image_url (cover, auto)','final_image_url (cover/thumbnail — hosted link)'):
      url=str(r.get(k) or '').strip()
      if url and url not in [v.get('url') for v in item['image_probes']]:item['image_probes'].append(probe(url))
   book.close();report['stores'].append(item)
 publish(report,branch='category-reports')
 print('Read-only two-store diagnosis published; Drive files unchanged.')
if __name__=='__main__':main()
