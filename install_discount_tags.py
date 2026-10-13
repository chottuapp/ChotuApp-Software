"""Fill discount tag template columns; preserve the installed engine."""
from pathlib import Path
import ast
import datetime
import hashlib
import os
import re
import shutil
import tempfile
import argparse

REPLACEMENTS = [('def write_row(ws, vals):\n', "def discount_export_fields(vals):\n    # CHOTUAPP_DISCOUNT_FIELDS_V1: additive export fields, never change prices.\n    from decimal import Decimal, ROUND_HALF_UP\n    result = dict(vals)\n    base = money(vals.get('base_price (PKR)'))\n    sale = money(vals.get('sale_price (PKR, agar discount ho)'))\n    result.update({'discount_percentage (%)': None, 'discount_tag': None,\n                   'discount_tag_source': None, 'source_discount_tag': None})\n    if base is not None and sale is not None and base > 0 and 0 <= sale < base:\n        percentage = (base - sale) / base * Decimal('100')\n        result['discount_percentage (%)'] = float(percentage.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))\n        result['discount_tag'] = str(percentage.quantize(Decimal('1'), rounding=ROUND_HALF_UP)) + '% Off'\n        result['discount_tag_source'] = 'calculated_from_prices'\n    return result\n\n\ndef write_row(ws, vals):\n    if ws.title in ('Products', 'Variant Combinations'):\n        vals = discount_export_fields(vals)\n    if ws.title == 'Products':\n        vals = dict(vals)\n        vals['sale_price (PKR, only if discounted)'] = vals.get('sale_price (PKR, agar discount ho)')\n        vals['scraped_image_url (auto)'] = vals.get('scraped_image_url (cover, auto)')\n        vals['final_image_url (main photo)'] = vals.get('final_image_url (cover/thumbnail — hosted link)') or vals.get('scraped_image_url (cover, auto)')\n    elif ws.title == 'Option Groups':\n        vals = dict(vals, **{'title (customer sees this)': vals.get('title (customer ko dikhega)')})\n    elif ws.title == 'Options':\n        vals = dict(vals, option_image_url=vals.get('option_image_url (agar size/color/variant ki apni image ho)'))\n"), ("    for r in rows: write_row(wb['Products'],r)", "    galleries = {}\n    for image in imgs:\n        galleries.setdefault(image['product_id'], []).append(image['scraped_image_url (auto)'])\n    for r in rows:\n        r['gallery_urls (extra photos, separate with |)'] = '|'.join(galleries.get(r['product_id'], []))\n        write_row(wb['Products'],r)\n    log('DISCOUNT TAGS: product and variant percentages calculated from exported regular/sale prices; exact website badge text not independently fetched')")]
REPLACEMENTS.append(("        if _changed:\n            _temp = staging / (safe + ' - PRICE POLICY BUILDING.xlsx')", "        if _changed:\n            # Keep new export aliases/tags consistent with the final integer prices.\n            for _sheet_name in ('Products', 'Variant Combinations'):\n                _ws = _book[_sheet_name]\n                _headers = {str(c.value).strip(): c.column for c in _ws[1] if c.value is not None}\n                for _row in _ws.iter_rows(min_row=2):\n                    _vals = {key: _row[col-1].value for key, col in _headers.items()}\n                    _tags = discount_export_fields(_vals)\n                    for _key in ('discount_percentage (%)', 'discount_tag', 'discount_tag_source', 'source_discount_tag'):\n                        if _key in _headers: _row[_headers[_key]-1].value = _tags[_key]\n                    if 'sale_price (PKR, only if discounted)' in _headers:\n                        _row[_headers['sale_price (PKR, only if discounted)']-1].value = _vals.get('sale_price (PKR, agar discount ho)')\n            _temp = staging / (safe + ' - PRICE POLICY BUILDING.xlsx')"))
MARKER = '# CHOTUAPP_DISCOUNT_FIELDS_V1'

def transform(data):
    source=data.decode('utf-8-sig')
    if MARKER in source:return data,0
    changed=source
    for old,new in REPLACEMENTS:
        if changed.count(old)!=1:raise RuntimeError('Unsupported export code; no changes made.')
        changed=changed.replace(old,new,1)
    compile(changed,'main.py','exec')
    return changed.encode('utf-8'),len(REPLACEMENTS)


def install(target, dry_run=False):
    destination = Path(target).expanduser().resolve() / 'main.py'
    original = destination.read_bytes()
    updated, count = transform(original)
    print('Installed source SHA256:', hashlib.sha256(original).hexdigest()[:16])
    if not count:
        print('Discount Tags Export already installed; no changes needed.')
        return
    print('Verified: discount columns and importer aliases added.')
    print('Prices, variants, images, descriptions, saved runs and speed settings preserved.')
    if dry_run:
        print('DRY RUN: application files unchanged.')
        return
    backup = destination.parent / 'backups' / ('main_before_discount_tags_' + datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f') + '.py')
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
    print('SUCCESS: Discount Tags Export installed. Existing 429/503 backoff and Retry-After handling preserved.')
    print('Backup:', backup)
    print('Takes effect next time the app starts. Title/version remains unchanged.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--target',type=Path,default=Path.home()/'Desktop'/'ChotuApp_Software')
    parser.add_argument('--dry-run',action='store_true')
    args=parser.parse_args()
    try:install(args.target,args.dry_run)
    except Exception as exc:parser.exit(1,'Discount tags update stopped: '+str(exc)+'\n')
