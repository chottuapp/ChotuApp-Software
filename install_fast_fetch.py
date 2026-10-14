"""Add two-worker preloading without replacing existing extraction logic."""
from pathlib import Path
import argparse
import ast
import datetime
import os
import shutil
import tempfile

RESUME_HOOK='\n# CHOTUAPP_DURABLE_RUNS_V1\nfrom resume_support import enable_resume as _enable_saved_runs\n_enable_saved_runs(globals())\n\n'
FAST_HOOK='\n# CHOTUAPP_CONTROLLED_FAST_V1\nfrom fast_fetch_support import enable_fast_fetch as _enable_fast_fetch\n_enable_fast_fetch(globals())\n\n'


def transform(source):
    ast.parse(source)
    for expected in ('class App:', 'def get_json(', 'def discover(', 'def collections(', 'def _run_checked('):
        if expected not in source:raise RuntimeError('Unsupported application code; no replacement made.')
    hooks=''
    if '# CHOTUAPP_DURABLE_RUNS_V1' not in source:hooks+=RESUME_HOOK
    if '# CHOTUAPP_CONTROLLED_FAST_V1' not in source:hooks+=FAST_HOOK
    if hooks:
        positions=[source.find(x) for x in ("if __name__=='__main__':",'if __name__ == "__main__":',"if __name__ == '__main__':")]
        positions=[x for x in positions if x>=0]
        if not positions:raise RuntimeError('Startup entry point missing.')
        index=min(positions);source=source[:index]+hooks+source[index:]
    compile(source,'main.py','exec');return source


def install(target):
    from install_speed_patch import transform as speed_transform
    root=Path(__file__).resolve().parent;target=Path(target).expanduser().resolve();main=target/'main.py';original=main.read_bytes()
    paced,count=speed_transform(original)
    updated=transform(paced.decode('utf-8-sig')).encode()
    payloads=[(target/'resume_support.py',(root/'resume_support.py').read_bytes()),(target/'fast_fetch_support.py',(root/'fast_fetch_support.py').read_bytes()),(main,updated)]
    for dest,data in payloads:compile(data,str(dest),'exec')
    stamp=datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f');backups=target/'backups'/('before_fast_fetch_'+stamp);backups.mkdir(parents=True)
    for dest,data in payloads:
        if dest.exists():
            shutil.copy2(dest,backups/dest.name)
            if (backups/dest.name).read_bytes()!=dest.read_bytes():raise RuntimeError('Backup verification failed.')
    if main.read_bytes()!=original:raise RuntimeError('Source changed while installing; stopped.')
    for dest,data in payloads:
        temp=None
        try:
            with tempfile.NamedTemporaryFile(dir=target,prefix='.fast-fetch-',delete=False) as stream:temp=Path(stream.name);stream.write(data)
            os.replace(temp,dest)
        finally:
            if temp:temp.unlink(missing_ok=True)
    print('SUCCESS: Controlled Fast Fetch installed: 2 workers, shared pacing and rate-limit cooldown.')
    print('Canonical prices/variants/images/categories/audits, daily settings and saved files retained.')
    print('Backup:',backups)
    print('Restart and Continue Saved Run. Log shows FAST FETCH when preloading starts.')

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--target',type=Path,default=Path.home()/'Desktop'/'ChotuApp_Software');args=parser.parse_args()
    try:install(args.target)
    except Exception as exc:parser.exit(1,'Fast Fetch update stopped: '+str(exc)+'\n')
