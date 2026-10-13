"""Add optional daily fetching and Windows login startup without replacing the engine."""
import argparse
import ast
import datetime
import os
from pathlib import Path
import shutil
import tempfile

RESUME_HOOK='\n# CHOTUAPP_DURABLE_RUNS_V1\nfrom resume_support import enable_resume as _enable_saved_runs\n_enable_saved_runs(globals())\n\n'
AUTO_HOOK='\n# CHOTUAPP_DAILY_AUTO_V1\nfrom automation_support import enable_automation as _enable_daily_automation\n_enable_daily_automation(globals())\n\n'


def transform(source):
    ast.parse(source)
    for expected in ('class App:', 'def _launch_jobs(', 'def _run_checked(', 'def _chotu_open_checkpoint('):
        if expected not in source:raise RuntimeError('Unsupported app source; nothing replaced.')
    hooks=''
    if '# CHOTUAPP_DURABLE_RUNS_V1' not in source:hooks+=RESUME_HOOK
    if '# CHOTUAPP_DAILY_AUTO_V1' not in source:hooks+=AUTO_HOOK
    if hooks:
        positions=[source.find(x) for x in ("if __name__=='__main__':",'if __name__ == "__main__":',"if __name__ == '__main__':")]
        positions=[x for x in positions if x>=0]
        if not positions:raise RuntimeError('Startup entry point missing; nothing replaced.')
        index=min(positions);source=source[:index]+hooks+source[index:]
    compile(source,'main.py','exec');return source


def install(target):
    target=Path(target).expanduser().resolve();main=target/'main.py';original=main.read_bytes()
    updated=transform(original.decode('utf-8-sig')).encode('utf-8')
    here=Path(__file__).resolve().parent
    payloads=[(target/'resume_support.py',(here/'resume_support.py').read_bytes()),(target/'automation_support.py',(here/'automation_support.py').read_bytes()),(main,updated)]
    for destination,data in payloads:compile(data,str(destination),'exec')
    backups=target/'backups';backups.mkdir(exist_ok=True);stamp=datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    for destination,data in payloads:
        if destination.exists():
            backup=backups/(destination.stem+'_before_daily_auto_'+stamp+'.py');shutil.copy2(destination,backup)
            if backup.read_bytes()!=destination.read_bytes():raise RuntimeError('Backup verification failed; stopped.')
    if main.read_bytes()!=original:raise RuntimeError('App source changed during install; stopped.')
    for destination,data in payloads:
        temporary=None
        try:
            with tempfile.NamedTemporaryFile(dir=target,prefix='.daily-auto-',delete=False) as stream:
                temporary=Path(stream.name);stream.write(data)
            os.replace(temporary,destination)
        finally:
            if temporary:temporary.unlink(missing_ok=True)
    print('SUCCESS: Daily Auto Fetch panel installed. Automation is OFF until enabled and saved in the app.')
    print('Extraction, prices, template preferences and saved run files preserved.')
    print('Backups:',backups)
    print('Tick stores, choose template, enable daily/login options, then Save selected stores.')

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--target',type=Path,default=Path.home()/'Desktop'/'ChotuApp_Software')
    args=parser.parse_args()
    try:install(args.target)
    except Exception as exc:parser.exit(1,'Daily update stopped: '+str(exc)+'\n')
