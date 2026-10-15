"""Retain full source descriptions and product-only detail panels; preserve engine."""
import argparse
import ast
import datetime
from pathlib import Path
import shutil
from remove_daily_auto import atomic_write

OLD_PANEL="""        product['_storefront_specs_html'] = ''.join(str(node) for node in soup.select(
            'product-info table, .product__info-container table, [id^="ProductInfo"] table, .product-specifications, #specifications, [data-product-specifications]'))"""
NEW_PANEL="""        # CHOTUAPP_COMPLETE_DETAIL_PANELS_V1
        from complete_description_support import collect_product_details
        product['_storefront_specs_html'] = collect_product_details(soup)"""
NEW_DESCRIPTION="""def friendly_description(p):
    # CHOTUAPP_COMPLETE_DESCRIPTIONS_V1: no short cosmetic/category cutoff.
    from complete_description_support import complete_description
    return complete_description(p, txt, detailed_description, _chotu_debug)
"""

def transform(source):
    ast.parse(source)
    if '# CHOTUAPP_COMPLETE_DESCRIPTIONS_V1' not in source:
        nodes=[n for n in ast.parse(source).body if isinstance(n,ast.FunctionDef) and n.name=='friendly_description']
        if len(nodes)!=1:raise RuntimeError('Unknown description function; stopped.')
        node=nodes[0];lines=source.splitlines(keepends=True)
        source=''.join(lines[:node.lineno-1])+NEW_DESCRIPTION+''.join(lines[node.end_lineno:])
    if '# CHOTUAPP_COMPLETE_DETAIL_PANELS_V1' not in source:
        if source.count(OLD_PANEL)!=1:raise RuntimeError('Unknown product-detail extraction block; stopped.')
        source=source.replace(OLD_PANEL,NEW_PANEL,1)
    compile(source,'main.py','exec');return source

def install(target):
    target=Path(target).expanduser().resolve();main=target/'main.py';before=main.read_bytes()
    updated=transform(before.decode('utf-8-sig'));after=(b'\xef\xbb\xbf' if before.startswith(b'\xef\xbb\xbf') else b'')+updated.encode()
    payload=(Path(__file__).parent/'complete_description_support.py').read_bytes();compile(payload,'complete_description_support.py','exec')
    backup=target/'backups'/('before_complete_descriptions_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f'));backup.mkdir(parents=True)
    for path in (main,target/'complete_description_support.py'):
        if path.exists():
            shutil.copy2(path,backup/path.name)
            if (backup/path.name).read_bytes()!=path.read_bytes():raise RuntimeError('Backup verification failed.')
    if main.read_bytes()!=before:raise RuntimeError('App changed during installation; stopped.')
    atomic_write(target/'complete_description_support.py',payload)
    if before!=after:atomic_write(main,after)
    print('SUCCESS: Full source descriptions enabled for all product categories.')
    print('Ingredients, usage, care and specification panels are retained when present in the fetched product page.')
    print('Prices, variants, images, sorting, fetching workers and saved runs preserved. No extra page request added.')
    print('Existing Excel files are unchanged. Restart and Continue Saved Run or use New Fresh Run for current source data.')
    print('Backup:',backup)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--target',type=Path,default=Path.home()/'Desktop'/'ChotuApp_Software');a=p.parse_args()
    try:install(a.target)
    except Exception as exc:p.exit(1,'Description update stopped: '+str(exc)+'\n')
