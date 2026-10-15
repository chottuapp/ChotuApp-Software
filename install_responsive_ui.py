"""Install GUI-only responsiveness improvements; keep fetching settings intact."""
import argparse
import ast
import datetime
from pathlib import Path
import shutil
from remove_daily_auto import atomic_write

HOOK='\n# CHOTUAPP_RESPONSIVE_UI_V1\nfrom responsive_ui_support import enable_responsive_ui as _enable_smooth_ui\n_enable_smooth_ui(globals())\n\n'
def transform(source):
    ast.parse(source)
    if '# CHOTUAPP_RESPONSIVE_UI_V1' in source:return source
    for expected in ('class App:','def poll(self):','def _animate_dashboard(self):','def debug_watchdog(self):'):
        if expected not in source:raise RuntimeError('Unsupported UI source; no changes made.')
    points=[source.find(s) for s in ("if __name__=='__main__':",'if __name__ == "__main__":',"if __name__ == '__main__':")];points=[p for p in points if p>=0]
    if not points:raise RuntimeError('Startup entry point missing.')
    i=min(points);updated=source[:i]+HOOK+source[i:];compile(updated,'main.py','exec');return updated

def install(target):
    target=Path(target).expanduser().resolve();main=target/'main.py';original=main.read_bytes()
    updated=transform(original.decode('utf-8-sig')).encode();module=(Path(__file__).parent/'responsive_ui_support.py').read_bytes();compile(module,'responsive_ui_support.py','exec')
    backup=target/'backups'/('before_smooth_ui_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f'));backup.mkdir(parents=True)
    for path in (main,target/'responsive_ui_support.py'):
        if path.exists():
            shutil.copy2(path,backup/path.name)
            if (backup/path.name).read_bytes()!=path.read_bytes():raise RuntimeError('Backup verification failed.')
    if main.read_bytes()!=original:raise RuntimeError('App changed during installation; stopped.')
    atomic_write(target/'responsive_ui_support.py',module)
    if updated!=original:atomic_write(main,updated)
    print('SUCCESS: Smooth UI installed. Fetching, prices, workers and saved runs unchanged.')
    print('Backup:',backup)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--target',type=Path,default=Path.home()/'Desktop'/'ChotuApp_Software');args=parser.parse_args()
    try:install(args.target)
    except Exception as exc:parser.exit(1,'UI update stopped: '+str(exc)+'\n')
