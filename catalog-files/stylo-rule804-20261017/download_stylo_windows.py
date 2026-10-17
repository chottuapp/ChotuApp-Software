"""Download the reviewed Stylo workbook into the user's existing daily archive."""
import argparse,hashlib,importlib.util,json,os,re,tempfile,urllib.request,zipfile
from pathlib import Path

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--revision',required=True);a=parser.parse_args()
    if not re.fullmatch(r'[0-9a-f]{7,40}',a.revision):raise ValueError('Invalid revision')
    base='https://raw.githubusercontent.com/chottuapp/ChotuApp-Software/'+a.revision+'/catalog-files/stylo-rule804-20261017/'
    with urllib.request.urlopen(base+'verification.json',timeout=60) as response:manifest=json.load(response)
    helper=Path.home()/'Desktop'/'cloud_sync_windows.py'
    if not helper.is_file():raise RuntimeError('Existing daily-archive helper not found: '+str(helper))
    spec=importlib.util.spec_from_file_location('chotu_daily_archive',helper);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    with tempfile.TemporaryDirectory(prefix='stylo-rule804-') as d:
        path=Path(d)/manifest['file']
        urllib.request.urlretrieve(base+manifest['file'],path)
        if hashlib.sha256(path.read_bytes()).hexdigest()!=manifest['sha256']:raise RuntimeError('Workbook checksum mismatch; not saved')
        with zipfile.ZipFile(path) as z:
            if z.testzip() is not None:raise RuntimeError('Workbook archive integrity failed')
        root=Path.home()/'Desktop'/'ANAS_DATA_FETCH'/'Save daily data with dates'
        destination=module.archive_daily_excel(path,root,'rule804-stylo-39020395288',Path(manifest['file']))
        print('Verified Stylo Rule 804 file saved:',destination)
        if os.name=='nt':
            import subprocess
            subprocess.Popen(['explorer','/select,'+str(destination)])
if __name__=='__main__':main()
