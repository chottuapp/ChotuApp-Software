"""Read-only public variant schema capture for the reported Czone iPad."""
import json,sys
from pathlib import Path
from bs4 import BeautifulSoup
import requests
from czone_source_support import nuxt
URL='https://www.czone.com.pk/apple-11-ipad-pro-m5-chip-256gb-wifi-only-space-black-mdwk4'

def main():
    response=requests.get(URL,timeout=45);response.raise_for_status()
    soup=BeautifulSoup(response.content,'html.parser');values,decode=nuxt(soup)
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
