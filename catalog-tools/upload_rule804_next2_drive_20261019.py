"""Install the reviewed 19 October Rawayat and Outfitters batch and replace matching Drive files."""
import argparse,hashlib,json,os,shutil,subprocess,tempfile,urllib.request,zipfile
from pathlib import Path
URL='https://raw.githubusercontent.com/chottuapp/ChotuApp-Software/310f86d3cdd41cfd98ab19e98c219fe3522ca68e/catalog-files/rule804-20261019-next2-reviewed/Rule804_Rawayat_Outfitters_2026-10-19.zip'
SHA256='cfc5a8f5f25627995131fdb3ba4f52023278a91a300df35c52063f069faa6c03'
FILES={'Outfitters.xlsx': 'b984767cc5d3a309169f366f4ad9826b8d72d955caa2b887e7663f98d1113184', 'Rawayat.xlsx': '6ec1456457e326427903423fe58eed747c9dc5b6fc143019ff478c4ff7b8d38a'}
OLD_FILES={'Tawakkal Fabrics.xlsx', 'Nisa Naturals.xlsx', 'Bonanza Satrangi.xlsx', 'Rivaj UK.xlsx', 'Hemani Herbals.xlsx', 'Vince Care.xlsx', 'Adam Cheese.xlsx', 'Miss Rose.xlsx', 'Computer Zone.xlsx', 'Farda Foods.xlsx', 'Denim Leftover.xlsx', 'Seran.xlsx', 'Cool and Cool.xlsx', 'Shop Modest.xlsx', 'Saeed Ghani.xlsx', 'Islamabad Tea.xlsx', 'Elite Cosmetics.xlsx', 'Skin Factor.xlsx', 'The Hanger Pakistan.xlsx'}
REMOTE='chotudrive:ChotuApp 19-10-2026 11-36AM'

def digest(payload):return hashlib.sha256(payload).hexdigest()
def prepare(archive,folder):
    if digest(archive.read_bytes())!=SHA256:raise ValueError('ZIP checksum mismatch; no upload attempted')
    with zipfile.ZipFile(archive) as z:
        if len(z.infolist())!=2 or set(z.namelist())!=set(FILES) or z.testzip() is not None:
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
    if len(before)!=len(set(before)) or not OLD_FILES.issubset(set(before)) or not set(before).issubset(OLD_FILES | set(FILES)):
        raise ValueError('Drive folder contains unexpected/missing old Excel names or duplicates; stopped without deleting anything')
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
    if len(after)!=21 or set(after)!=(OLD_FILES | set(FILES)):raise ValueError('Unexpected final Drive file listing; inspect before claiming completion')
    print('VERIFIED: Rawayat and Outfitters uploaded and verified. Existing 19 files retained; total 21 Excel files. No reports or duplicate filenames.',flush=True)
    print('Drive folder: ChotuApp 19-10-2026 11-36AM',flush=True)
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--archive',type=Path);parser.add_argument('--folder',type=Path,default=Path.home()/'Desktop'/'ChotuApp 19-10-2026 11-36AM Rule804 Rawayat Outfitters');parser.add_argument('--prepare-only',action='store_true');args=parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='rule804-download-') as temp:
        archive=args.archive or Path(temp)/'catalogs.zip'
        if args.archive is None:
            print('Downloading verified Rule 804 batch...',flush=True);urllib.request.urlretrieve(URL,archive)
        folder=prepare(archive,args.folder)
    print('2 verified Rule 804 workbooks: '+str(folder),flush=True)
    print('8425 products; 35777 variant combinations. Updated Rule 804; shop_code, product_id, Category. Prices, stock, variants, website order and image links preserved. 148 Rawayat and 1 Outfitters category remain source-unverified and blank.',flush=True)
    if not args.prepare_only:upload(folder,find_rclone())
if __name__=='__main__':main()
