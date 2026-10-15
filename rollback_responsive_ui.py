"""Remove only the known Smooth UI startup hook; preserve current engine."""
import argparse
import ast
import datetime
from pathlib import Path
import shutil
from remove_daily_auto import atomic_write
HOOK='\n# CHOTUAPP_RESPONSIVE_UI_V1\nfrom responsive_ui_support import enable_responsive_ui as _enable_smooth_ui\n_enable_smooth_ui(globals())\n\n'


def transform(source):
    ast.parse(source)
    if '# CHOTUAPP_RESPONSIVE_UI_V1' not in source:return source
    if source.count(HOOK)!=1:raise RuntimeError('Unrecognized UI hook; stopped without changes.')
    result=source.replace(HOOK,'',1);ast.parse(result);return result


def install(target):
    target=Path(target).expanduser().resolve();main=target/'main.py';before=main.read_bytes()
    text=before.decode('utf-8-sig');updated=transform(text)
    after=(b'\xef\xbb\xbf' if before.startswith(b'\xef\xbb\xbf') else b'')+updated.encode('utf-8')
    if updated==text:
        print('Smooth UI is already disabled; no changes needed.');return
    backup=target/'backups'/('before_ui_rollback_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f'));backup.mkdir(parents=True)
    shutil.copy2(main,backup/'main.py')
    if (backup/'main.py').read_bytes()!=before:raise RuntimeError('Backup verification failed.')
    if main.read_bytes()!=before:raise RuntimeError('App changed during rollback; stopped.')
    atomic_write(main,after)
    print('SUCCESS: Smooth UI disabled. Only its startup hook was removed.')
    print('Current engine, workers, saved runs, templates and exports retained.')
    print('Backup:',backup)
    print('Restart the app; Smooth UI should no longer appear in the title.')

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--target',type=Path,default=Path.home()/'Desktop'/'ChotuApp_Software');args=parser.parse_args()
    try:install(args.target)
    except Exception as exc:parser.exit(1,'UI rollback stopped: '+str(exc)+'\n')
