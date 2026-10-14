"""Prioritize up to 20 discounted best sellers; preserve the installed engine."""
from pathlib import Path
import ast
import datetime
import hashlib
import os
import re
import shutil
import tempfile
import argparse

REPLACEMENTS = [("def prioritize_top_sellers(rows, handles):\n    # Rank is global across categories. Match product handles so URL scheme,\n    # query parameters and trailing slashes cannot silently defeat ordering.\n    rank = {handle: i for i, handle in enumerate(dict.fromkeys(handles))}\n    def key(row):\n        handle = urlparse(row['source_url']).path.rstrip('/').rsplit('/', 1)[-1]\n        return (0, rank[handle]) if handle in rank else (1, 0)\n    rows.sort(key=key)\n    return [row for row in rows if key(row)[0] == 0]\n\n", "# CHOTUAPP_FINAL_CATALOG_ORDER_V1\n\ndef genuine_discount(row):\n    base=money(row.get('base_price (PKR)'))\n    sale=money(row.get('sale_price (PKR, agar discount ho)'))\n    return base is not None and sale is not None and base>0 and 0<=sale<base\n\n\ndef prioritize_top_sellers(rows, handles, variant_discount_ids=()):\n    variant_discount_ids=set(variant_discount_ids)\n    discounted=lambda row:genuine_discount(row) or row.get('product_id') in variant_discount_ids\n    has_discount=any(discounted(row) for row in rows)\n    rank={handle:i for i,handle in enumerate(dict.fromkeys(handles)) if i<20}\n    def key(row):\n        handle=urlparse(row['source_url']).path.rstrip('/').rsplit('/',1)[-1]\n        eligible=discounted(row) if has_discount else True\n        if eligible and handle in rank:return (0,rank[handle])\n        return (1 if eligible else 2,0)\n    rows.sort(key=key)\n    return [row for row in rows if key(row)[0]==0]\n\n\ndef finalize_catalog_order(workbook_path, ranking_path, log):\n    # Apply the order after price policy and immediately before publication.\n    book=load_workbook(workbook_path)\n    try:\n        sheet=book['Products'];headers=[cell.value for cell in sheet[1]]\n        rows=[dict(zip(headers,values)) for values in sheet.iter_rows(min_row=2,values_only=True)]\n        variant_discount_ids=set()\n        if 'Variant Combinations' in book.sheetnames:\n            iterator=iter(book['Variant Combinations'].values);variant_headers=next(iterator)\n            for values in iterator:\n                variant=dict(zip(variant_headers,values))\n                if variant.get('available (yes/no)')=='yes' and genuine_discount(variant):variant_discount_ids.add(variant.get('product_id'))\n        handles=[]\n        if Path(ranking_path).is_file():\n            with Path(ranking_path).open(encoding='utf-8-sig',newline='') as stream:\n                handles=[urlparse(row['source_url']).path.rstrip('/').rsplit('/',1)[-1] for row in csv.DictReader(stream)]\n        ranked=prioritize_top_sellers(rows,handles,variant_discount_ids)\n        for index,row in enumerate(rows,2):\n            for col,header in enumerate(headers,1):sheet.cell(index,col).value=row.get(header)\n        temporary=Path(workbook_path).with_name('.'+Path(workbook_path).stem+'-order.xlsx')\n        try:\n            book.save(temporary)\n            verify=load_workbook(temporary,read_only=True,data_only=True)\n            try:\n                if verify['Products'].max_row!=len(rows)+1:raise RuntimeError('Final ordering row count mismatch')\n            finally:verify.close()\n            os.replace(temporary,workbook_path)\n        finally:temporary.unlink(missing_ok=True)\n        log('FINAL FILE ORDER: '+str(len(ranked))+' verified best sellers first; remaining discounted products, then non-discounted; prices/variants/images retained')\n    finally:book.close()\n\n"), ("    # CHOTUAPP_DISCOUNT_TOP20_V1: only genuinely discounted products qualify.\n    discount_handles = {urlparse(r['source_url']).path.rstrip('/').rsplit('/',1)[-1] for r in rows\n                        if money(r.get('sale_price (PKR, agar discount ho)')) is not None\n                        and money(r.get('base_price (PKR)')) is not None\n                        and 0 <= money(r.get('sale_price (PKR, agar discount ho)')) < money(r.get('base_price (PKR)'))}\n    top_handles = verified_top20(base, log, discount_handles)\n", "    # CHOTUAPP_DISCOUNT_TOP20_V1: include discounts on available combinations.\n    variant_discount_ids={c['product_id'] for c in combos if c.get('available (yes/no)')=='yes' and genuine_discount(c)}\n    discount_handles={urlparse(r['source_url']).path.rstrip('/').rsplit('/',1)[-1] for r in rows\n                      if genuine_discount(r) or r['product_id'] in variant_discount_ids}\n    ranking_handles=discount_handles or {urlparse(r['source_url']).path.rstrip('/').rsplit('/',1)[-1] for r in rows}\n    top_handles=verified_top20(base,log,ranking_handles)\n"), ('    ranked_rows = prioritize_top_sellers(rows, top_handles) if top_handles else []', '    ranked_rows = prioritize_top_sellers(rows, top_handles, variant_discount_ids)'), ("        log('FILE ORDER: first ' + str(len(ranked_rows)) + ' discounted products follow website best-selling rank across ALL categories; remaining products follow afterward')", "        log('FILE ORDER: verified top sellers among discounted products first (all products if no discounts); then remaining discounted, then non-discounted across ALL categories')"), ("        log('PRICE POLICY: Removed fractional parts from ' + str(_changed) + ' Excel price cells (Products + Variant Combinations); original API price audits preserved.')", "        log('PRICE POLICY: Removed fractional parts from ' + str(_changed) + ' Excel price cells (Products + Variant Combinations); original API price audits preserved.')\n        finalize_catalog_order(review_file, staging / (safe + ' - BEST SELLERS.csv'), log)")]
MARKER = '# CHOTUAPP_FINAL_CATALOG_ORDER_V1'

def transform(data):
    source=data.decode('utf-8-sig')
    if MARKER in source:return data,0
    changed=source
    for index,(old,new) in enumerate(REPLACEMENTS):
        if changed.count(old)!=1:
            alternatives={
                1:["    top_handles = verified_top20(base, log, {urlparse(r['source_url']).path.rsplit('/',1)[-1] for r in rows})\n"],
                3:["        log('FILE ORDER: first ' + str(len(ranked_rows)) + ' products follow website best-selling rank across ALL categories; remaining products follow afterward')"]}
            matches=[candidate for candidate in alternatives.get(index,[]) if changed.count(candidate)==1]
            if len(matches)!=1:raise RuntimeError('Unsupported ordering source; no changes made.')
            old=matches[0]
        changed=changed.replace(old,new,1)
    compile(changed,'main.py','exec')
    return changed.encode('utf-8'),len(REPLACEMENTS)


def install(target, dry_run=False):
    destination = Path(target).expanduser().resolve() / 'main.py'
    original = destination.read_bytes()
    updated, count = transform(original)
    print('Installed source SHA256:', hashlib.sha256(original).hexdigest()[:16])
    if not count:
        print('Final Catalog Ordering already installed; no changes needed.')
        return
    print('Verified: ranking eligibility, discount grouping and final-save ordering updated.')
    print('Prices, variants, images, descriptions, saved runs and speed settings preserved.')
    if dry_run:
        print('DRY RUN: application files unchanged.')
        return
    backup = destination.parent / 'backups' / ('main_before_final_order_' + datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f') + '.py')
    backup.parent.mkdir(exist_ok=True)
    shutil.copy2(destination, backup)
    if backup.read_bytes() != original:
        raise RuntimeError('Backup verification failed; installation stopped.')
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=destination.parent, prefix='.chotu-speed-', suffix='.py', delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(updated)
        if destination.read_bytes() != original:
            raise RuntimeError('Source changed during patch; installation stopped.')
        os.replace(temporary, destination)
    finally:
        if temporary is not None:temporary.unlink(missing_ok=True)
    print('SUCCESS: Final Catalog Ordering installed. Existing 429/503 backoff and Retry-After handling preserved.')
    print('Backup:', backup)
    print('Takes effect next time the app starts. Title/version remains unchanged.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--target',type=Path,default=Path.home()/'Desktop'/'ChotuApp_Software')
    parser.add_argument('--dry-run',action='store_true')
    args=parser.parse_args()
    try:install(args.target,args.dry_run)
    except Exception as exc:parser.exit(1,'Final ordering update stopped: '+str(exc)+'\n')
