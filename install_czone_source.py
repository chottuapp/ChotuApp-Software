"""Install Czone-only fetching support, preserving existing code and saved runs."""
import argparse,ast,datetime,os,shutil,tempfile,subprocess,sys
from pathlib import Path
HOOK='\n# CHOTUAPP_CZONE_WEBX_V1\nfrom czone_source_support import enable_czone_source as _enable_czone_source\n_enable_czone_source(globals())\n\n'

def transform(source):
    ast.parse(source)
    if '# CHOTUAPP_CZONE_WEBX_V1' in source:return source
    if '_chotuapp_run_site_original' not in source:raise RuntimeError('Unsupported app version; no changes made')
    points=[source.find(s) for s in ("if __name__=='__main__':",'if __name__ == "__main__":',"if __name__ == '__main__':")];points=[p for p in points if p>=0]
    if not points:raise RuntimeError('Startup entry point missing')
    i=min(points);result=source[:i]+HOOK+source[i:];compile(result,'main.py','exec');return result

def atomic(path,content):
    fd,name=tempfile.mkstemp(prefix='.czone-',dir=path.parent)
    try:
        with os.fdopen(fd,'wb') as stream:stream.write(content);stream.flush();os.fsync(stream.fileno())
        os.replace(name,path)
    finally:Path(name).unlink(missing_ok=True)

def install(target):
    target=Path(target).resolve();main=target/'main.py';before=main.read_bytes()
    after=transform(before.decode('utf-8-sig')).encode('utf-8')
    if before.startswith(b'\xef\xbb\xbf'):after=b'\xef\xbb\xbf'+after
    module=(Path(__file__).parent/'czone_source_support.py').read_bytes();compile(module,'czone_source_support.py','exec')
    backup=target/'backups'/('before_czone_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f'));backup.mkdir(parents=True)
    for path in (main,target/'czone_source_support.py'):
        if path.exists():
            shutil.copy2(path,backup/path.name)
            if path.read_bytes()!=(backup/path.name).read_bytes():raise RuntimeError('Backup verification failed')
    if main.read_bytes()!=before:raise RuntimeError('App source changed during installation; stopped')
    atomic(target/'czone_source_support.py',module)
    try:
        if before!=after:atomic(main,after)
    except Exception:
        # Main remains on its earlier compatible version; backup is retained.
        raise
    print('SUCCESS: Czone Webx adapter installed. Other stores, speed settings, templates and saved work retained.')
    print('Czone uses public pages, checks three price sources, and preserves gallery images and warranty text.')
    print('Browser fallback requires: py -m pip install playwright; then py -m playwright install chromium')
    print('Choose Computer Zone only and New Fresh Run. Unknown variants/specifications or incomplete catalogs stop safely.')
    print('Backup:',backup)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--target',type=Path,default=Path.home()/'Desktop'/'ChotuApp_Software');p.add_argument('--with-browser',action='store_true',help='Install the browser dependency used for Czone infinite-scroll discovery');a=p.parse_args()
    try:
        if a.with_browser:
            subprocess.run([sys.executable,'-m','pip','install','playwright'],check=True)
            subprocess.run([sys.executable,'-m','playwright','install','chromium'],check=True)
        install(a.target)
    except Exception as exc:p.exit(1,'Czone update stopped: '+str(exc)+'\n')
