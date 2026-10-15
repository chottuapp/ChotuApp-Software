"""Add Farda's verified shop-link routing without replacing the extraction engine."""
import argparse
import ast
import datetime
from pathlib import Path
import shutil
from remove_daily_auto import atomic_write

HOOK='\n# CHOTUAPP_FARDA_SHOP_SOURCE_V1\nfrom farda_source_support import enable_farda_source as _enable_farda_shop\n_enable_farda_shop(globals())\n\n'
def transform(source):
    ast.parse(source)
    if '# CHOTUAPP_FARDA_SHOP_SOURCE_V1' in source:return source
    if 'def run_site(' not in source or 'def get_json(' not in source:raise RuntimeError('Unsupported extraction source; no changes made.')
    points=[source.find(s) for s in ("if __name__=='__main__':",'if __name__ == "__main__":',"if __name__ == '__main__':")];points=[p for p in points if p>=0]
    if not points:raise RuntimeError('Startup entry point missing.')
    i=min(points);result=source[:i]+HOOK+source[i:];compile(result,'main.py','exec');return result

def install(target):
    target=Path(target).expanduser().resolve();main=target/'main.py';before=main.read_bytes();source=before.decode('utf-8-sig');updated=transform(source)
    after=(b'\xef\xbb\xbf' if before.startswith(b'\xef\xbb\xbf') else b'')+updated.encode()
    module=(Path(__file__).parent/'farda_source_support.py').read_bytes();compile(module,'farda_source_support.py','exec')
    backup=target/'backups'/('before_farda_shop_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f'));backup.mkdir(parents=True)
    for path in (main,target/'farda_source_support.py'):
        if path.exists():
            shutil.copy2(path,backup/path.name)
            if (backup/path.name).read_bytes()!=path.read_bytes():raise RuntimeError('Backup verification failed.')
    if main.read_bytes()!=before:raise RuntimeError('Source changed during installation; stopped.')
    atomic_write(target/'farda_source_support.py',module)
    if after!=before:atomic_write(main,after)
    print('SUCCESS: Farda Shop Now routing installed; other stores and saved work retained.')
    print('Farda validates https://shop.fardafoods.com/products.json before running existing extraction checks.')
    print('An empty or incompatible catalog stops without replacing an existing Excel file.')
    print('Backup:',backup)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--target',type=Path,default=Path.home()/'Desktop'/'ChotuApp_Software');a=p.parse_args()
    try:install(a.target)
    except Exception as exc:p.exit(1,'Farda update stopped: '+str(exc)+'\n')
