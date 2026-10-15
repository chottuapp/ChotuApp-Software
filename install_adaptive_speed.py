"""Install adaptive request recovery and equivalent plain-text processing."""
from pathlib import Path
import argparse
import datetime
import shutil
from install_manual_fast import install as install_base
from install_speed_patch import transform as pace_transform
from install_fast_fetch import transform as fast_transform
from remove_daily_auto import transform as manual_transform, atomic_write

OLD_TEXT = "def txt(v):\n    return re.sub(r'\\s+', ' ', html.unescape(BeautifulSoup(str(v or ''), 'html.parser').get_text(' ', strip=True))).strip()\n"
NEW_TEXT = "def txt(v):\n    # CHOTUAPP_TEXT_FAST_V1: plain strings need no HTML tree.\n    value=str(v or '')\n    if '<' not in value and '&' not in value:\n        return re.sub(r'\\s+', ' ', value).strip()\n    return re.sub(r'\\s+', ' ', html.unescape(BeautifulSoup(value, 'html.parser').get_text(' ', strip=True))).strip()\n"

def text_transform(data):
    source=data.decode('utf-8-sig')
    if '# CHOTUAPP_TEXT_FAST_V1' in source:return data
    if source.count(OLD_TEXT)!=1:raise RuntimeError('Unsupported text normalizer; stopped without changes.')
    source=source.replace(OLD_TEXT,NEW_TEXT,1)
    compile(source,'main.py','exec');return source.encode('utf-8')


def install(target):
    target=Path(target).expanduser().resolve();main=target/'main.py'
    data=main.read_bytes();paced,_=pace_transform(data)
    text_transform(manual_transform(fast_transform(paced.decode('utf-8-sig'))).encode())
    install_base(target)
    installed=main.read_bytes();updated=text_transform(installed)
    if updated!=installed:
        backup=target/'backups'/('main_before_text_fast_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f')+'.py')
        shutil.copy2(main,backup)
        if backup.read_bytes()!=installed:raise RuntimeError('Text update backup failed.')
        if main.read_bytes()!=installed:raise RuntimeError('Source changed; stopped.')
        atomic_write(main,updated)
    print('SUCCESS: High Speed V3 + durable cache processing update installed. No new dependency required.')
    print('After 20 consecutive HTTP 200 replies, request spacing recovers 25% toward the source-safe floor.')
    print('Prices, variants, images, final ordering and saved work preserved. Continue Saved Run after restart.')

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--target',type=Path,default=Path.home()/'Desktop'/'ChotuApp_Software');args=parser.parse_args()
    try:install(args.target)
    except Exception as exc:parser.exit(1,'Adaptive update stopped: '+str(exc)+'\n')
