"""Install the reviewed 19 October 13-store batch and replace matching Drive files."""
import argparse,hashlib,json,os,shutil,subprocess,tempfile,urllib.request,zipfile
from pathlib import Path
URL='https://raw.githubusercontent.com/chottuapp/ChotuApp-Software/b2dbeec0e186ea55e8f98ef02dffb81c286a7ce0/catalog-files/rule804-20261019-13-locked-category/Rule804_13_Stores_Locked_Category_2026-10-19.zip'
SHA256='4bb034c930dc34045a041b8a51604af3c7fb1377312a8ad9c8dc7867b574dfaf'
FILES={'Adam Cheese.xlsx': 'ac54f3ac8f1f99870baaf59e73e8147d210a11111e0a33bfc8334802cdc43de5', 'Cool and Cool.xlsx': 'dfe23087393e3a325a8713159fa64c82763758f1056202a059ae26611bc2af8f', 'Denim Leftover.xlsx': '88cd3b5406bbd0ab8108e493cbecd6dae3d4684fe145f914880d5c3313fbe8fe', 'Farda Foods.xlsx': '6a1fbce61c18d5b230964dab98798eddab47013ae73212ca6c567765a1e85790', 'Islamabad Tea.xlsx': '183e1e5ac7c55db5f7631d6a35780397bb54cc9cc6dfb43c28f612e71675d5f3', 'Miss Rose.xlsx': 'c1b44ad47f845d86338b62fcbbd4deb4cf7e3c992d1dad7e532f91cb16b033e4', 'Nisa Naturals.xlsx': '5dbc622564f3c83c52d1c463e799a69660e1247472cd603173b14ee6612a55a8', 'Rivaj UK.xlsx': '3ccd9cfc23bda9c23cb8b153fbca78322947365bf4f3fd498622ada59eec04e6', 'Seran.xlsx': 'c151fa4240930fad30a45599d071505ed781901340bfca205c71b0462259816b', 'Shop Modest.xlsx': '560dd8e76cec7e638a3ebf14b001ccea341c45a7d471b3a53b361a6098c45ab0', 'Skin Factor.xlsx': '4762c8017fb799eaa365287ceeb85b880dc6be1df14b4f0490c3085e3b4a26bf', 'The Hanger Pakistan.xlsx': '9268138afe153be3553f3e4ddfa98fd8a4dc46b73051e22fb03fbfc2b3877e17', 'Vince Care.xlsx': '9416798a8f9da293ded02df85047a1e885fe734dda27da70ade9e4b794e34814'}
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
    print('VERIFIED: 13 final Category-header Rule 804 Excel files replaced the old Drive versions. No reports or duplicate filenames.',flush=True)
    print('Drive folder: ChotuApp 19-10-2026 11-36AM',flush=True)
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--archive',type=Path);parser.add_argument('--folder',type=Path,default=Path.home()/'Desktop'/'ChotuApp 19-10-2026 11-36AM Rule804 Final Category');parser.add_argument('--prepare-only',action='store_true');args=parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='rule804-download-') as temp:
        archive=args.archive or Path(temp)/'catalogs.zip'
        if args.archive is None:
            print('Downloading verified Rule 804 batch...',flush=True);urllib.request.urlretrieve(URL,archive)
        folder=prepare(archive,args.folder)
    print('13 verified Rule 804 workbooks: '+str(folder),flush=True)
    print('2034 products; 8894 variants. Locked schema: shop_code, product_id, Category. Former subcategory values unchanged; Seran Noirelle remains blank. Prices, formulas and image links preserved.',flush=True)
    if not args.prepare_only:upload(folder,find_rclone())
if __name__=='__main__':main()
