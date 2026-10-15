"""Install source-aware pacing and accurate mixed-run status; retain main.py."""
import argparse
import datetime
from pathlib import Path
import shutil
from remove_daily_auto import atomic_write


def install(target):
    target=Path(target).expanduser().resolve();main=target/'main.py';before=main.read_bytes();source=before.decode('utf-8-sig')
    if not all(marker in source for marker in ('CHOTUAPP_DURABLE_RUNS_V1','CHOTUAPP_CONTROLLED_FAST_V1')):
        raise RuntimeError('Saved Runs + Fast Fetch hooks not found; stopped without changes.')
    payload={name:(Path(__file__).parent/name).read_bytes() for name in ('resume_support.py','fast_fetch_support.py')}
    for name,data in payload.items():compile(data,name,'exec')
    backup=target/'backups'/('before_source_stability_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f'));backup.mkdir(parents=True)
    for name in payload:
        path=target/name
        if not path.is_file():raise RuntimeError('Missing '+name+'; stopped.')
        shutil.copy2(path,backup/name)
        if (backup/name).read_bytes()!=path.read_bytes():raise RuntimeError('Backup verification failed.')
    if main.read_bytes()!=before:raise RuntimeError('App changed during installation; stopped.')
    for name,data in payload.items():atomic_write(target/name,data)
    print('SUCCESS: Stable source pacing installed; main.py and saved work retained.')
    print('Shop Modest uses one worker; recent rate limits hold learned spacing for 30 minutes.')
    print('Other stores retain bounded parallel fetching. Existing cooldowns are respected.')
    print('Failed endpoints and website cooldowns are shown separately; Farda 404 still needs a compatible source endpoint.')
    print('Backup:',backup)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--target',type=Path,default=Path.home()/'Desktop'/'ChotuApp_Software');a=p.parse_args()
    try:install(a.target)
    except Exception as exc:p.exit(1,'Stability update stopped: '+str(exc)+'\n')
