"""Install manual-only operation and controlled fast fetching together."""
import argparse
from pathlib import Path
from install_fast_fetch import install as install_fast
from remove_daily_auto import install as install_manual


def install(target):
    # Validate both transformations before either installer writes files.
    from install_speed_patch import transform as pace_transform
    from install_fast_fetch import transform as fast_transform
    from remove_daily_auto import transform as manual_transform
    data=(Path(target)/'main.py').read_bytes()
    paced,_=pace_transform(data)
    manual_transform(fast_transform(paced.decode('utf-8-sig')))
    install_fast(target)
    install_manual(target)
    print('SUCCESS: Manual + Fast Fetch installed together. No daily automation.')
    print('Window title will include Fast Fetch (2 workers).')

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--target',type=Path,default=Path.home()/'Desktop'/'ChotuApp_Software')
    args=parser.parse_args()
    try:install(args.target)
    except Exception as exc:parser.exit(1,'Combined update stopped: '+str(exc)+'\n')
