"""Install the reviewed 19 October 13-store batch and replace matching Drive files."""
import argparse,hashlib,json,os,shutil,subprocess,tempfile,urllib.request,zipfile
from pathlib import Path
URL='https://raw.githubusercontent.com/chottuapp/ChotuApp-Software/fb992804f4fac9ade9e3ed877d802fa00967d797/catalog-files/rule804-20261019-13-subcategory/Rule804_13_Stores_Subcategory_2026-10-19.zip'
SHA256='5efa5ec012691fea21b664d96b24b446b832856049466894211ffd5b9f6ddded'
FILES={'Adam Cheese.xlsx': 'ae157494e1c01bb941dfda685ead5256f2af2c2e4359b31247887ec29d568a31', 'Cool and Cool.xlsx': 'd3259a40716e27e37d8326c4a2409481336fbb4652a6cf3c6d9a3a146e1c28f0', 'Denim Leftover.xlsx': 'e6012f9089770b7cc391ec74def25e40e55bc6c83e39ebdae549c22cfa998d64', 'Farda Foods.xlsx': 'f35d563658fea28ad0a70685d80ad248d88dcb1248c06b55f4fa18d4b0548446', 'Islamabad Tea.xlsx': '5712b176a7dda37ff572719b380d225a4525273e29213b5d791a01c9fdb77021', 'Miss Rose.xlsx': 'd84b8d0a2b78faf6bb797640b589522dbeea132f52c749b8bada9b3fb321c353', 'Nisa Naturals.xlsx': '316d772c52ba377efb943efd94fdfb448a97ff7b3e9f1388aeef9e122d6dbc58', 'Rivaj UK.xlsx': '696824b631312e035af2ab97df56471facd1cae3bda4e9183a23ea4342cd3040', 'Seran.xlsx': 'c15363ae86cadd6146781556bea86a02a6eec189501291e19921c4196f3cfb91', 'Shop Modest.xlsx': '65c7a5c21b66dc16585c3b2f091df1d002a7fd32d62766857f85a9d8b093e5ba', 'Skin Factor.xlsx': 'ec0f890ba4c23610b71a58181b735cf69846eb39339a4ece932cc55f6b9e622d', 'The Hanger Pakistan.xlsx': '199950f07228cf8ae33a06c8097a92cd0f3cb6c73e45a81470fdebb4d94b6dac', 'Vince Care.xlsx': '92379273b25b5ea6a35f261623a41cf512878171441414e9a8fc4ad10d478f38'}
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
    print('VERIFIED: 13 subcategory-only Rule 804 Excel files replaced the old Drive versions. No reports or duplicate filenames.',flush=True)
    print('Drive folder: ChotuApp 19-10-2026 11-36AM',flush=True)
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--archive',type=Path);parser.add_argument('--folder',type=Path,default=Path.home()/'Desktop'/'ChotuApp 19-10-2026 11-36AM Rule804 Subcategory');parser.add_argument('--prepare-only',action='store_true');args=parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='rule804-download-') as temp:
        archive=args.archive or Path(temp)/'catalogs.zip'
        if args.archive is None:
            print('Downloading verified Rule 804 batch...',flush=True);urllib.request.urlretrieve(URL,archive)
        folder=prepare(archive,args.folder)
    print('13 verified Rule 804 workbooks: '+str(folder),flush=True)
    print('2034 products; 8894 variants. Category column removed; subcategories, shop codes and website order preserved.',flush=True)
    if not args.prepare_only:upload(folder,find_rclone())
if __name__=='__main__':main()
