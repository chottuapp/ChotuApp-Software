"""Remove daily automation UI/startup while preserving the installed extractor."""
import argparse
import datetime
import json
import os
from pathlib import Path
import shutil
import tempfile

AUTO_HOOK='\n# CHOTUAPP_DAILY_AUTO_V1\nfrom automation_support import enable_automation as _enable_daily_automation\n_enable_daily_automation(globals())\n\n'
MANUAL_HOOK='\n# CHOTUAPP_MANUAL_ONLY_V1\nfrom manual_mode_support import enable_manual_mode as _enable_manual_mode\n_enable_manual_mode(globals())\n\n'
STARTUP_MARKER='REM CHOTUAPP_DAILY_AUTOMATION_V1'


def transform(source):
    if '# CHOTUAPP_DAILY_AUTO_V1' in source:
        if source.count(AUTO_HOOK)!=1:raise RuntimeError('Unexpected automation hook; stopped without replacing source.')
        source=source.replace(AUTO_HOOK,'',1)
    if 'from automation_support import enable_automation' in source:raise RuntimeError('Unknown automation startup; stopped.')
    if '# CHOTUAPP_MANUAL_ONLY_V1' not in source:
        positions=[source.find(x) for x in ("if __name__=='__main__':",'if __name__ == "__main__":',"if __name__ == '__main__':")]
        positions=[x for x in positions if x>=0]
        if not positions:raise RuntimeError('Startup entry point not found.')
        index=min(positions);source=source[:index]+MANUAL_HOOK+source[index:]
    compile(source,'main.py','exec');return source


def atomic_write(path,data):
    path=Path(path);temporary=None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent,prefix='.manual-update-',delete=False) as stream:
            temporary=Path(stream.name);stream.write(data)
        os.replace(temporary,path)
    finally:
        if temporary:temporary.unlink(missing_ok=True)


def disable_settings(target,backups,startup=None):
    target=Path(target);backups=Path(backups)
    settings=target/'daily_automation.json'
    if settings.exists():
        shutil.copy2(settings,backups/'daily_automation.json')
        try:
            state=json.loads(settings.read_text(encoding='utf-8'))
            if not isinstance(state,dict):raise ValueError('Invalid settings')
            state['enabled']=False;state['startup']=False
            atomic_write(settings,json.dumps(state,indent=2).encode())
        except ValueError:
            # The hook is removed, so malformed settings cannot activate fetching.
            print('Automation settings unreadable; preserved. Automatic runtime hook removed.')
    if startup is None and os.name=='nt':
        startup=Path(os.environ['APPDATA'])/'Microsoft/Windows/Start Menu/Programs/Startup/ChotuApp Daily Auto Fetch.cmd'
    if startup is not None:
        startup=Path(startup)
        if startup.exists():
            if STARTUP_MARKER in startup.read_text(encoding='utf-8'):
                shutil.copy2(startup,backups/'daily_startup.cmd');startup.unlink()
            else:print('Unrecognized startup file preserved; no unrelated launcher removed.')


def install(target):
    target=Path(target).expanduser().resolve();main=target/'main.py';data=main.read_bytes();source=data.decode('utf-8-sig')
    if 'class App:' not in source or 'def _launch_jobs(' not in source:raise RuntimeError('Unsupported application; stopped.')
    changed=transform(source).encode();helper=Path(__file__).with_name('manual_mode_support.py').read_bytes();compile(helper,'manual_mode_support.py','exec')
    backups=target/'backups'/('before_manual_only_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f'));backups.mkdir(parents=True)
    shutil.copy2(main,backups/'main.py')
    if (backups/'main.py').read_bytes()!=data:raise RuntimeError('Backup verification failed.')
    destination=target/'manual_mode_support.py'
    if destination.exists():shutil.copy2(destination,backups/destination.name)
    if main.read_bytes()!=data:raise RuntimeError('App code changed while installing; stopped.')
    atomic_write(destination,helper);atomic_write(main,changed)
    disable_settings(target,backups)
    print('SUCCESS: Manual fetching restored; Daily Auto Fetch panel and timers removed.')
    print('Owned Windows login launcher removed; fast fetch, Saved Runs and Excel rules preserved.')
    print('Backups:',backups)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--target',type=Path,default=Path.home()/'Desktop'/'ChotuApp_Software');args=parser.parse_args()
    try:install(args.target)
    except Exception as exc:parser.exit(1,'Manual update stopped: '+str(exc)+'\n')
