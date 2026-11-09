"""Inspect only public grocery listing metadata from a stopped saved checkpoint."""
import json,os,re,sqlite3,tempfile,zipfile
from pathlib import Path
from urllib.parse import urlsplit,parse_qs
from bs4 import BeautifulSoup
from download_checkpoint import download
from resume_support import ResponseCache
from source_research import publish
from drive_sync import gh,REPO

def main():
 rid=os.environ['GROCERY_CHECKPOINT_RUN']
 if not re.fullmatch(r'\d{1,30}',rid):raise ValueError('Numeric completed grocery run required')
 run=json.loads(gh('api','repos/'+REPO+'/actions/runs/'+rid))
 if run.get('status')!='completed' or run.get('head_branch')!='main' or not str(run.get('display_title','')).startswith('Cloud group chotu-groceries-'):raise ValueError('Untrusted or active checkpoint source')
 report=dict(run_id=os.environ['GITHUB_RUN_ID'],source_run=rid,status='checkpoint_inspected',pages=[])
 with tempfile.TemporaryDirectory() as tmp:
  root=Path(tmp);download(rid,REPO,root/'download',attempts=2,deadline_seconds=180)
  files=list((root/'download').rglob('checkpoint.zip'))
  if len(files)!=1:raise ValueError('Unique small checkpoint required for bounded inspection')
  with zipfile.ZipFile(files[0]) as archive:
   entries=[i for i in archive.infolist() if i.filename.startswith('saved_runs/') and i.filename.endswith('/pages.sqlite3')]
   if not 1<=len(entries)<=2 or sum(i.file_size for i in entries)>128*1024*1024:raise ValueError('Listing diagnostic checkpoint bound exceeded')
   for index,item in enumerate(entries):
    if '..' in Path(item.filename).parts:raise ValueError('Unsafe cache identity')
    path=root/('pages-'+str(index)+'.sqlite3');path.write_bytes(archive.read(item));cache=ResponseCache(path)
    try:
     urls=[r[0] for r in cache.db.execute('SELECT url FROM pages')]
     for url in urls:
      p=urlsplit(url)
      if p.hostname!='www.naheed.pk' or p.path.rstrip('/')!='/allproducts' or parse_qs(p.query).get('manufacturer')!=['890']:continue
      response=cache.get(url)
      if response is None:raise ValueError('Saved listing checksum invalid')
      soup=BeautifulSoup(response.text,'html.parser');count=soup.select_one('.toolbar-amount')
      selector='#product_result a[href], .products-grid .product-item a.product-item-link[href], .products.list.items .product-item a.product-item-link[href]'
      report['pages'].append(dict(url=url,toolbar_text=count.get_text(' ',strip=True) if count else '',toolbar_html=str(count),product_links=[a.get('href') for a in soup.select(selector)],pagination=[dict(text=a.get_text(' ',strip=True),href=a.get('href')) for a in soup.select('.pages a[href],a.next[href]')]))
    finally:cache.close()
 publish(report,branch='chotu-groceries-reports');print(json.dumps(report,ensure_ascii=False)[:12000])
if __name__=='__main__':main()
