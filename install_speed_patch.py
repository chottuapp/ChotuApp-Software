"""Patch only adaptive request pacing; preserve installed application behavior."""
from pathlib import Path
import ast
import datetime
import hashlib
import os
import re
import shutil
import tempfile
import argparse

PATTERNS = {
    "getattr(_chotu_tls, 'adaptive_pace', 1.5)": "getattr(_chotu_tls, 'adaptive_pace', 0.35)",
    "max(1.5, pace * 0.95)": "max(0.35, pace * 0.95)",
}
MARKER = '# CHOTUAPP_SPEED_S1: pacing only; extraction and validation rules unchanged.'


def transform(data):
    source = data.decode('utf-8-sig')
    if MARKER in source:
        return data, 0
    if 'def get_json(' not in source or 'def storefront_cover(' not in source:
        raise RuntimeError('Unsupported source version; no changes made.')
    changed = source
    count = 0
    for old, new in PATTERNS.items():
        occurrences = changed.count(old)
        if not occurrences:
            raise RuntimeError('Expected pacing settings missing; no changes made.')
        count += occurrences
        changed = changed.replace(old, new)
    # Verify that the entire AST differs ONLY in intended pacing literals.
    before = ast.parse(source)
    after = ast.parse(changed)
    differences = []
    def compare(a, b, path='root'):
        if type(a) is not type(b):
            raise RuntimeError('Unexpected source structure change: ' + path)
        if isinstance(a, ast.AST):
            if isinstance(a, ast.Constant) and a.value == 1.5 and b.value == 0.35:
                differences.append(path)
                return
            for field in a._fields:
                compare(getattr(a, field), getattr(b, field), path + '.' + field)
        elif isinstance(a, list):
            if len(a) != len(b):raise RuntimeError('Unexpected source structure change')
            for i, (left, right) in enumerate(zip(a, b)):compare(left, right, path + '[' + str(i) + ']')
        elif a != b:
            raise RuntimeError('Unexpected non-pacing source change: ' + path)
    compare(before, after)
    if len(differences) != count:
        raise RuntimeError('Pacing change verification failed; no changes made.')
    changed += '\n' + MARKER + '\n'
    compile(changed, 'main.py', 'exec')
    return changed.encode('utf-8'), count


def install(target, dry_run=False):
    destination = Path(target).expanduser().resolve() / 'main.py'
    original = destination.read_bytes()
    updated, count = transform(original)
    print('Installed source SHA256:', hashlib.sha256(original).hexdigest()[:16])
    if not count:
        print('Speed S1 already installed; no changes needed.')
        return
    print('Verified: only', count, 'pacing literals change from 1.5s to 0.35s.')
    print('Prices, variants, images, descriptions, categories, audits and ordering code unchanged.')
    if dry_run:
        print('DRY RUN: application files unchanged.')
        return
    backup = destination.parent / 'backups' / ('main_before_speed_S1_' + datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f') + '.py')
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
    print('SUCCESS: Speed S1 installed. Existing 429/503 backoff and Retry-After handling preserved.')
    print('Backup:', backup)
    print('Takes effect next time the app starts. Title/version remains unchanged.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--target',type=Path,default=Path.home()/'Desktop'/'ChotuApp_Software')
    parser.add_argument('--dry-run',action='store_true')
    args=parser.parse_args()
    try:install(args.target,args.dry_run)
    except Exception as exc:parser.exit(1,'Speed patch stopped: '+str(exc)+'\n')
