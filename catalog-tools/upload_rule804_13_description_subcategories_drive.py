"""Install the reviewed 19 October 13-store batch and replace matching Drive files."""
import argparse,hashlib,json,os,shutil,subprocess,tempfile,urllib.request,zipfile
from pathlib import Path
URL='https://raw.githubusercontent.com/chottuapp/ChotuApp-Software/416af8230b7bab3234e6df60fa8874ae184f18f9/catalog-files/rule804-20261019-13-description-subcategories/Rule804_13_Stores_Description_Subcategories_2026-10-19.zip'
SHA256='9f48f6690ce54a939e92115f79b7461d3afaff2e0ff0cfeab1391ccbf1b6c5eb'
FILES={'Adam Cheese.xlsx': '2854fbcbfce6c1544b3ea7a23c358f1ebc07dd43407adf204271ad9b11ce746c', 'Cool and Cool.xlsx': '6b5221807c4585b8aa2be68547513fa065b408de0ed3585371ae2262448854d7', 'Denim Leftover.xlsx': '0f895b9ea4beec4608baf8771a1c5b0c730551a36efc2c137e5bea4e53eb10d0', 'Farda Foods.xlsx': 'cbe3ae3bef3b1a1a5f87c13b1da9c5eec4117104cf121465781c0c937cae2c3e', 'Islamabad Tea.xlsx': 'f42d00e81b8d9646fd891bb6f281db6f2e6a7e6ea62cd34b61c94393675a109a', 'Miss Rose.xlsx': '6a6e8a731fdce0e3175e2eed87d457f17566347c4afccf8397a1eb19f1e7d511', 'Nisa Naturals.xlsx': 'cf687128607c1c10b7a0f8024353dcc60e610b92c177aab6ef47436313bdd421', 'Rivaj UK.xlsx': 'fb2af50fb1958609d58f1e3d8404c1e0519aa15c49b598948d3e9427d244bb9c', 'Seran.xlsx': '56fa08d101eaa6c0bec4cb780877fe496ffdd9e97de0bdb8a91ad9122a77d322', 'Shop Modest.xlsx': '8e2b9bb303864605c24214102bb05e754b09d3d387a544c9ec8fa5310bdda434', 'Skin Factor.xlsx': '0e8138834317c0093b23f934b7a8fec2454a975e8cc2c8053ed2d965f7aa57ba', 'The Hanger Pakistan.xlsx': 'c869e86f9b2636a4495470712a0ff1c0503a5ca0d4e3dca55e576f05302cdca0', 'Vince Care.xlsx': 'd685a49e53948bf77aee21d7bfc793897aa02c9f743985098bc046df2692ba8d'}
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
    print('VERIFIED: 13 description-classified Rule 804 Excel files replaced the old Drive versions. No reports or duplicate filenames.',flush=True)
    print('Drive folder: ChotuApp 19-10-2026 11-36AM',flush=True)
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--archive',type=Path);parser.add_argument('--folder',type=Path,default=Path.home()/'Desktop'/'ChotuApp 19-10-2026 11-36AM Rule804 Description Subcategories');parser.add_argument('--prepare-only',action='store_true');args=parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='rule804-download-') as temp:
        archive=args.archive or Path(temp)/'catalogs.zip'
        if args.archive is None:
            print('Downloading verified Rule 804 batch...',flush=True);urllib.request.urlretrieve(URL,archive)
        folder=prepare(archive,args.folder)
    print('13 verified Rule 804 workbooks: '+str(folder),flush=True)
    print('2034 products; 8894 variants. 447 additional subcategories inferred from supplied product text; Seran Noirelle remains ambiguous and blank. Website labels retained; inference provenance recorded separately.',flush=True)
    if not args.prepare_only:upload(folder,find_rclone())
if __name__=='__main__':main()
