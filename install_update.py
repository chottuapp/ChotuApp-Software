"""Install this main.py while preserving an existing installation and its data."""
import argparse
import datetime
import hashlib
import os
from pathlib import Path
import shutil
import tempfile

def install(target):
    source = Path(__file__).resolve().with_name('main.py')
    data = source.read_bytes()
    compile(data, str(source), 'exec')
    destination = Path(target).expanduser().resolve() / 'main.py'
    if not destination.is_file():
        raise RuntimeError('Existing main.py not found. Supply --target with your existing ChotuApp_Software folder.')
    if destination == source:
        raise RuntimeError('Extract this update into a separate folder before installing.')
    if destination.read_bytes() == data:
        print('Already installed; no changes needed.')
        return
    stamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    backup = destination.parent / 'backups' / ('main_before_tested_update_' + stamp + '.py')
    backup.parent.mkdir(exist_ok=True)
    shutil.copy2(destination, backup)
    if hashlib.sha256(backup.read_bytes()).digest() != hashlib.sha256(destination.read_bytes()).digest():
        raise RuntimeError('Backup verification failed; installation stopped.')
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=destination.parent, prefix='.chotu-update-', suffix='.py', delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(data)
        compile(temporary.read_bytes(), str(destination), 'exec')
        os.replace(temporary, destination)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    print('SUCCESS: updated main.py')
    print('Backup:', backup)
    print('Start:', destination)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--target', type=Path, default=Path.home()/'Desktop'/'ChotuApp_Software')
    args = parser.parse_args()
    try:
        install(args.target)
    except Exception as exc:
        parser.exit(1, 'Installation stopped: ' + str(exc) + '\n')
