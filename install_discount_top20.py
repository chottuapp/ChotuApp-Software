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

REPLACEMENTS = [("    top_handles = verified_top20(base, log, {urlparse(r['source_url']).path.rsplit('/',1)[-1] for r in rows})", "    # CHOTUAPP_DISCOUNT_TOP20_V1: only genuinely discounted products qualify.\n    discount_handles = {urlparse(r['source_url']).path.rstrip('/').rsplit('/',1)[-1] for r in rows\n                        if money(r.get('sale_price (PKR, agar discount ho)')) is not None\n                        and money(r.get('base_price (PKR)')) is not None\n                        and 0 <= money(r.get('sale_price (PKR, agar discount ho)')) < money(r.get('base_price (PKR)'))}\n    top_handles = verified_top20(base, log, discount_handles)"), ('products follow website best-selling rank across ALL categories; remaining products follow afterward', 'discounted products follow website best-selling rank across ALL categories; remaining products follow afterward')]
MARKER = '# CHOTUAPP_DISCOUNT_TOP20_V1'

def transform(data):
    source=data.decode('utf-8-sig')
    if MARKER in source:return data,0
    changed=source
    for old,new in REPLACEMENTS:
        if changed.count(old)!=1:raise RuntimeError('Unsupported ranking code; no changes made.')
        changed=changed.replace(old,new,1)
    compile(changed,'main.py','exec')
    return changed.encode('utf-8'),len(REPLACEMENTS)


def install(target, dry_run=False):
    destination = Path(target).expanduser().resolve() / 'main.py'
    original = destination.read_bytes()
    updated, count = transform(original)
    print('Installed source SHA256:', hashlib.sha256(original).hexdigest()[:16])
    if not count:
        print('Discounted Top 20 already installed; no changes needed.')
        return
    print('Verified: discounted eligibility and file-order log updated.')
    print('Prices, variants, images, descriptions, saved runs and speed settings preserved.')
    if dry_run:
        print('DRY RUN: application files unchanged.')
        return
    backup = destination.parent / 'backups' / ('main_before_discount_top20_' + datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f') + '.py')
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
    print('SUCCESS: Discounted Top 20 installed. Existing 429/503 backoff and Retry-After handling preserved.')
    print('Backup:', backup)
    print('Takes effect next time the app starts. Title/version remains unchanged.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--target',type=Path,default=Path.home()/'Desktop'/'ChotuApp_Software')
    parser.add_argument('--dry-run',action='store_true')
    args=parser.parse_args()
    try:install(args.target,args.dry_run)
    except Exception as exc:parser.exit(1,'Discount ranking update stopped: '+str(exc)+'\n')
