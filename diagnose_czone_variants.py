"""Read-only public variant schema capture for the reported Czone iPad."""
import json,sys,sqlite3,hashlib
from pathlib import Path
from bs4 import BeautifulSoup
from czone_source_support import nuxt
URL='https://www.czone.com.pk/apple-11-ipad-pro-m5-chip-256gb-wifi-only-space-black-mdwk4'

def saved_page(root):
    if not root.is_dir():return None
    paths=sorted(root.rglob('pages.sqlite3'),key=lambda path:path.stat().st_mtime,reverse=True)
    for path in paths:
        try:
            db=sqlite3.connect(path.resolve().as_uri()+'?mode=ro',uri=True,timeout=5)
            try:row=db.execute('SELECT body,checksum FROM pages WHERE url=? OR final_url=? LIMIT 1',(URL,URL)).fetchone()
            finally:db.close()
        except sqlite3.Error:continue
        if row and hashlib.sha256(row[0]).hexdigest()==row[1]:return row[0]
    return None

def main():
    body=saved_page(Path.home()/'Desktop'/'ChotuApp_Software'/'saved_runs')
    if body is None:
        raise RuntimeError('The reported iPad page was not found in saved runs. No website request or file change was made.')
    print('Reading already saved iPad page; database opened READ ONLY. No website request.')
    soup=BeautifulSoup(body,'html.parser');values,decode=nuxt(soup)
    records=[]
    for item in values:
        if isinstance(item,dict) and 'productID' in item and 'productPrice' in item:
            product=decode(item)
            records.append({k:product.get(k) for k in ('productID','productName','productURL','isVariant','productOptions','productVariants','productPrice','productStock')})
    if len(records)!=1:raise RuntimeError('Expected one primary product; no variant report written')
    target=Path.home()/'Desktop'/'Czone_Variants_Report.txt'
    target.write_text(json.dumps(records,indent=2,ensure_ascii=False),encoding='utf-8')
    print('Read-only variant report saved:',target)
    import subprocess
    subprocess.Popen(['notepad',str(target)])

if __name__=='__main__':
    try:main()
    except Exception as exc:print('Variant diagnostic stopped:',type(exc).__name__,str(exc));sys.exit(1)
