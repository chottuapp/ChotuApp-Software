"""Download both verified Rule 804 results to Desktop without overwriting files."""
import argparse,hashlib,json,re,shutil,tempfile,urllib.request,zipfile
from pathlib import Path

def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def save_copy(source,desktop,expected):
    if digest(source)!=expected:raise RuntimeError('Checksum mismatch: '+source.name)
    desktop=Path(desktop);index=0
    while True:
        destination=desktop/(source.stem+(' ('+str(index)+')' if index else '')+source.suffix)
        if destination.exists():
            if destination.is_file() and digest(destination)==expected:return destination
            index+=1;continue
        try:stream=destination.open('xb')
        except FileExistsError:continue
        try:
            with stream,source.open('rb') as incoming:shutil.copyfileobj(incoming,stream)
            if digest(destination)!=expected:raise RuntimeError('Saved file verification failed')
        except BaseException:
            destination.unlink(missing_ok=True);raise
        return destination

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--revision',required=True);a=parser.parse_args()
    if not re.fullmatch('[0-9a-f]{7,40}',a.revision):raise ValueError('Invalid revision')
    base='https://raw.githubusercontent.com/chottuapp/ChotuApp-Software/'+a.revision+'/catalog-files/rule804-run39047054601/'
    with urllib.request.urlopen(base+'verification.json',timeout=60) as response:manifest=json.load(response)
    files=manifest['files'];expected_names={'Miss_Rose_Rule804_ShopCode.xlsx','Rivaj_UK_Rule804_ShopCode.xlsx'}
    if len(files)!=2 or {r['file'] for r in files}!=expected_names:raise RuntimeError('Unexpected download manifest')
    desktop=Path.home()/'Desktop';saved=[]
    with tempfile.TemporaryDirectory(prefix='chotu-rule804-desktop-') as d:
        for row in files:
            p=Path(d)/row['file'];urllib.request.urlretrieve(base+row['file'],p)
            if digest(p)!=row['sha256']:raise RuntimeError('Download verification failed: '+p.name)
            with zipfile.ZipFile(p) as z:
                if z.testzip() is not None:raise RuntimeError('Invalid workbook: '+p.name)
        for row in files:saved.append(save_copy(Path(d)/row['file'],desktop,row['sha256']))
    for p in saved:print('Saved verified file:',p)
    print('Original files preserved. These are Rule 804 results from run 39047054601.')
    import os
    if os.name=='nt':
        import subprocess
        subprocess.Popen(['explorer',str(desktop)])
if __name__=='__main__':main()
