"""Add persistent resume support without replacing existing extraction code."""
from pathlib import Path
import argparse
import ast
import datetime
import os
import shutil
import tempfile

HOOK = "\n# CHOTUAPP_DURABLE_RUNS_V1\nfrom resume_support import enable_resume as _enable_saved_runs\n_enable_saved_runs(globals())\n\n"

def install(target):
    target=Path(target).expanduser().resolve();main=target/'main.py'
    data=main.read_bytes();text=data.decode('utf-8-sig')
    for expected in ('class App:', 'def _launch_jobs(', 'def _run_checked(', 'def _chotu_open_checkpoint('):
        if expected not in text:raise RuntimeError('Unsupported source; stopped without replacing main.py.')
    ast.parse(text)
    if '# CHOTUAPP_DURABLE_RUNS_V1' not in text:
        positions=[text.find("if __name__=='__main__':"),text.find('if __name__ == "__main__":'),text.find("if __name__ == '__main__':")]
        positions=[p for p in positions if p>=0]
        if not positions:raise RuntimeError('Startup entry point not found.')
        p=min(positions);updated=text[:p]+HOOK+text[p:]
    else:updated=text
    compile(updated,str(main),'exec')
    helper=Path(__file__).resolve().with_name('resume_support.py');compile(helper.read_bytes(),str(helper),'exec')
    stamp=datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    backups=target/'backups';backups.mkdir(exist_ok=True)
    backup=backups/('main_before_saved_runs_'+stamp+'.py');shutil.copy2(main,backup)
    if backup.read_bytes()!=data:raise RuntimeError('Backup verification failed.')
    destination=target/'resume_support.py'
    if destination.exists():shutil.copy2(destination,backups/('resume_support_before_'+stamp+'.py'))
    for dest,payload in [(destination,helper.read_bytes()),(main,updated.encode('utf-8'))]:
        temp=None
        try:
            with tempfile.NamedTemporaryFile(dir=target,prefix='.chotu-resume-',delete=False) as f:temp=Path(f.name);f.write(payload)
            os.replace(temp,dest)
        finally:
            if temp:temp.unlink(missing_ok=True)
    print('SUCCESS: Saved Runs support installed; original extraction and speed settings preserved.')
    print('Backup:',backup)
    print('New buttons: New Fresh Run (selected) / Continue Saved Run')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--target',type=Path,default=Path.home()/'Desktop'/'ChotuApp_Software');a=p.parse_args()
    try:install(a.target)
    except Exception as exc:p.exit(1,'Resume update stopped: '+str(exc)+'\n')
