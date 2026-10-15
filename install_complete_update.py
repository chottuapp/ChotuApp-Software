"""Install the complete ChotuApp bundle; retain templates, saved runs and exports."""
import argparse
import datetime
import os
from pathlib import Path
import shutil
import tempfile


def install(target):
    source=Path(__file__).resolve().parent;target=Path(target).expanduser().resolve()
    if source==target:raise RuntimeError('Extract the ZIP separately from your installed software folder.')
    program=['resume_support.py','manual_mode_support.py','remove_daily_auto.py','fast_fetch_support.py','farda_source_support.py','complete_description_support.py','requirements.txt','main.py']
    payloads={name:(source/name).read_bytes() for name in program}
    for name,data in payloads.items():
        if name.endswith('.py'):compile(data,name,'exec')
    target.mkdir(parents=True,exist_ok=True)
    stamp=datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    backup=target/'backups'/('complete_before_'+stamp);backup.mkdir(parents=True)
    previous={}
    for name in program:
        path=target/name
        if path.exists():
            previous[name]=path.read_bytes();shutil.copy2(path,backup/name)
            if (backup/name).read_bytes()!=previous[name]:raise RuntimeError('Backup verification failed.')
    # Existing user templates and all configuration/output/checkpoint files are retained.
    for name in ('ChotuApp_Template.xlsx','Chotu_Products_Import_Template_Discount_Tags.xlsx'):
        if not (target/name).exists():shutil.copy2(source/name,target/name)
    for name,data in payloads.items():
        destination=target/name;temporary=None
        if name in previous and destination.read_bytes()!=previous[name]:raise RuntimeError('Program changed during installation; stopped.')
        try:
            with tempfile.NamedTemporaryFile(dir=target,delete=False,prefix='.complete-update-') as stream:
                temporary=Path(stream.name);stream.write(data)
            os.replace(temporary,destination)
        finally:
            if temporary:temporary.unlink(missing_ok=True)
    from remove_daily_auto import disable_settings
    disable_settings(target,backup)
    print('SUCCESS: Complete manual software installed. User files and saved runs retained; automation disabled.')
    print('Backup:',backup)
    print('Start:',target/'main.py')

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--target',type=Path,default=Path.home()/'Desktop'/'ChotuApp_Software')
    args=parser.parse_args()
    try:install(args.target)
    except Exception as exc:parser.exit(1,'Complete update stopped: '+str(exc)+'\n')
