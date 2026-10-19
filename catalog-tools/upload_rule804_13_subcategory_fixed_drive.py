"""Install the reviewed 19 October 13-store batch and replace matching Drive files."""
import argparse,hashlib,json,os,shutil,subprocess,tempfile,urllib.request,zipfile
from pathlib import Path
URL='https://raw.githubusercontent.com/chottuapp/ChotuApp-Software/ab47e6bfa1f12617d0a37a4a578c277bb631e632/catalog-files/rule804-20261019-13-subcategory-fixed/Rule804_13_Stores_Subcategory_Fixed_2026-10-19.zip'
SHA256='d3f0217fd67f6d6a712aabfc6fd2e29e6e970a7f99b85ef13b425faccf2f11b8'
FILES={'Adam Cheese.xlsx': 'a2193f8878684bd6e54c3c555749eacbb776512847229b79a338a6c1f3e798eb', 'Cool and Cool.xlsx': 'bc0a7256ecf621ad10f6f419da48cc61262cb28f553383806006a2f94a0df981', 'Denim Leftover.xlsx': '75ea4ad33feb2a150dbf4c447243e9e884ab08660df92409c0fc61606defd8b7', 'Farda Foods.xlsx': '1383037c4c4a67aba7628657f4e9300e995f1b0fe9c3cc0b1fe124c6b919db09', 'Islamabad Tea.xlsx': '5712b176a7dda37ff572719b380d225a4525273e29213b5d791a01c9fdb77021', 'Miss Rose.xlsx': '72cfdf41ee9613086eacf582fe70e264fe5888d83b447b15d43f87381e6959a0', 'Nisa Naturals.xlsx': 'a41ad2a62f1852708373c8bf0836f5ac643612b2bdca98b4e8a0534c50dcc98c', 'Rivaj UK.xlsx': '68f89de9ca15d68340810d79a3fb22f825e42586e5c46b25798788ceaddc1ea7', 'Seran.xlsx': 'c15363ae86cadd6146781556bea86a02a6eec189501291e19921c4196f3cfb91', 'Shop Modest.xlsx': '260d85944e8786659d20666a5fa5d415aecf80d27eeae13393d35afae335c9d9', 'Skin Factor.xlsx': 'ec0f890ba4c23610b71a58181b735cf69846eb39339a4ece932cc55f6b9e622d', 'The Hanger Pakistan.xlsx': '199950f07228cf8ae33a06c8097a92cd0f3cb6c73e45a81470fdebb4d94b6dac', 'Vince Care.xlsx': 'dfeada4a2423c70d648aece54aadafcafa73bfbbf1ffc4aaf1c0f2b5a8cb500a'}
REMOTE='chotudrive:ChotuApp 19-10-2026 11-36AM'

def digest(payload):return hashlib.sha256(payload).hexdigest()
def prepare(archive,folder):
    if digest(archive.read_bytes())!=SHA256:raise ValueError('ZIP checksum mismatch; no upload attempted')
    with zipfile.ZipFile(archive) as z:
        if len(z.infolist())!=13 or set(z.namelist())!=set(FILES) or z.testzip() is not None:
            raise ValueError('Unexpected archive contents; no upload attempted')
        for name,checksum in FILES.items():
            if digest(z.read(name))!=checksum:raise ValueError('Workbook checksum mismatch: '+name)
            target=folder/name
            if target.exists() and digest(target.read_bytes())!=checksum:
                raise ValueError('Different local file already exists; keep it safe before retrying: '+str(target))
        folder.mkdir(parents=True,exist_ok=True)
        for name in FILES:
            target=folder/name
            if not target.exists():
                staging=folder/(name+'.downloading');staging.write_bytes(z.read(name));staging.replace(target)
    return folder

def find_rclone():
    found=shutil.which('rclone')
    if found:return found
    local=os.environ.get('LOCALAPPDATA')
    if local:
        candidates=sorted((Path(local)/'Microsoft/WinGet/Packages').glob('Rclone.Rclone_*/rclone-*-windows-amd64/rclone.exe'))
        if candidates:return str(candidates[-1])
    raise FileNotFoundError('Rclone executable not found')
def remote_names(exe):
    result=subprocess.run([exe,'lsjson',REMOTE,'--files-only','--max-depth','1'],capture_output=True,text=True,check=True,timeout=120)
    return [x['Name'] for x in json.loads(result.stdout) if not x.get('IsDir') and x['Name'].lower().endswith('.xlsx')]
def upload(folder,exe):
    remotes=subprocess.run([exe,'listremotes'],capture_output=True,text=True,check=True,timeout=60)
    if 'chotudrive:' not in remotes.stdout.splitlines():raise ValueError('chotudrive remote is not configured')
    before=remote_names(exe)
    if len(before)!=13 or set(before)!=set(FILES):
        raise ValueError('Drive folder does not contain exactly the expected 13 original Excel names; stopped without deleting anything')
    # Same names replace the original versions. Originals remain in the previous Desktop folder.
    # Copy only this validated batch, never unrelated local files or reports.
    with tempfile.TemporaryDirectory(prefix='rule804-drive-') as temp:
        staging=Path(temp)
        for name,checksum in FILES.items():
            payload=(folder/name).read_bytes()
            if digest(payload)!=checksum:raise ValueError('Local file changed: '+name)
            (staging/name).write_bytes(payload)
        subprocess.run([exe,'copy',str(staging),REMOTE,'--include','*.xlsx','--checksum','--progress'],check=True)
        subprocess.run([exe,'check',str(staging),REMOTE,'--include','*.xlsx','--one-way'],check=True)
    after=remote_names(exe)
    if len(after)!=13 or set(after)!=set(FILES):raise ValueError('Unexpected final Drive file listing; inspect before claiming completion')
    print('VERIFIED: 13 corrected subcategory-only Rule 804 Excel files replaced the old Drive versions. No reports or duplicate filenames.',flush=True)
    print('Drive folder: ChotuApp 19-10-2026 11-36AM',flush=True)
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--archive',type=Path);parser.add_argument('--folder',type=Path,default=Path.home()/'Desktop'/'ChotuApp 19-10-2026 11-36AM Rule804 Subcategory Fixed');parser.add_argument('--prepare-only',action='store_true');args=parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='rule804-download-') as temp:
        archive=args.archive or Path(temp)/'catalogs.zip'
        if args.archive is None:
            print('Downloading verified Rule 804 batch...',flush=True);urllib.request.urlretrieve(URL,archive)
        folder=prepare(archive,args.folder)
    print('13 verified Rule 804 workbooks: '+str(folder),flush=True)
    print('2034 products; 8894 variants. 515 subcategories filled from verified website paths; 448 remain source-unverified and blank. Shop codes and website order preserved.',flush=True)
    if not args.prepare_only:upload(folder,find_rclone())
if __name__=='__main__':main()
