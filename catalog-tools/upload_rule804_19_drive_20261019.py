"""Install the reviewed 19 October 19-store batch and replace matching Drive files."""
import argparse,hashlib,json,os,shutil,subprocess,tempfile,urllib.request,zipfile
from pathlib import Path
URL='https://raw.githubusercontent.com/chottuapp/ChotuApp-Software/f6aff18b90f579ad7194e8cf4374d2075857d1d4/catalog-files/rule804-20261019-19-reviewed/Rule804_19_Stores_2026-10-19.zip'
SHA256='e33a44a1114185b5085e8fceb310bd7523b79e8a07510f8c5a640c1253875eff'
FILES={'Adam Cheese.xlsx': 'f4b0395c03efbf3eb1856009139d4fc039dc92bb1422b82284bb9e00f1c9dccc', 'Bonanza Satrangi.xlsx': '635bb23de6e3dc54324bfcf4efa3d189ff250a040e93f918f94601287390cb3d', 'Computer Zone.xlsx': 'bf2449d3613f4005dabcf9b2571b73a6e45fd35c977ee70def68fd0c650e662f', 'Cool and Cool.xlsx': '306a0a6c6deb63e5088a27a2749d6a2a1e0da87cd314d6d0e58914f0684918aa', 'Denim Leftover.xlsx': '9fb2db02a03f43d2b8d396244449d6435dbd7d7341f36553f7c9948ad2323fa2', 'Elite Cosmetics.xlsx': 'd001b0c519acedf2bb00c01789b4674bdcec0b16ac0879f9ba9f9435ab6fadd2', 'Farda Foods.xlsx': '0c749dc7fa6eb1dc11aba5681f302ed8aa6be95cc199edcc75cfa5a4f23ffa32', 'Hemani Herbals.xlsx': 'a1b09ea887529ab9bbc276d530a123e8a70f904c308e7a34d50e835b362e7cfb', 'Islamabad Tea.xlsx': '4472280409208d17218c77830f9f8f531cca5dd1f87c443793d09314bd732c84', 'Miss Rose.xlsx': 'ed13829880c6d5ea49134c51f823dc1dd7e1d3d53def0599b6c2e41a3aeaa58f', 'Nisa Naturals.xlsx': '03c63726365dc74af781731db6069c156ff8102c8559433c3db89d2787888ee1', 'Rivaj UK.xlsx': 'e333e279587242812481fac34d8377c6cdcefe41e052c375c45c102468b96a1a', 'Saeed Ghani.xlsx': '3e6540536f38d3e51b1d1a7ba786687ccc6ae9706083633ee8d3caf4b121dece', 'Seran.xlsx': '7c6ad612078221c44959d832dc972b81a5a1eb6e3bcc90471f944fdb9cb4029c', 'Shop Modest.xlsx': '0167f06f23eb33e0ca4b0be0d97fe79ac99d375bff10fae561ad9382fb12bef2', 'Skin Factor.xlsx': '55071bbab72088e1ebfde21df3e08e35956e8bac894feda644d6dbc3191977e3', 'Tawakkal Fabrics.xlsx': '2f0908de30a687dcd1ca382839925b7e47bce1493d2a29203fc339ea43820819', 'The Hanger Pakistan.xlsx': 'dc0e45edc819427999c2374036e2484135d81ec5b291e113ee875fc03a1df527', 'Vince Care.xlsx': '9bc338b7519c153399c1d579c911ddf5c2ea988bb4b8a539d3fa00d3a25331d9'}
OLD_FILES={'Vince Care.xlsx', 'Denim Leftover.xlsx', 'Seran.xlsx', 'Skin Factor.xlsx', 'Nisa Naturals.xlsx', 'Miss Rose.xlsx', 'Rivaj UK.xlsx', 'Islamabad Tea.xlsx', 'Shop Modest.xlsx', 'Adam Cheese.xlsx', 'Cool and Cool.xlsx', 'The Hanger Pakistan.xlsx', 'Farda Foods.xlsx'}
REMOTE='chotudrive:ChotuApp 19-10-2026 11-36AM'

def digest(payload):return hashlib.sha256(payload).hexdigest()
def prepare(archive,folder):
    if digest(archive.read_bytes())!=SHA256:raise ValueError('ZIP checksum mismatch; no upload attempted')
    with zipfile.ZipFile(archive) as z:
        if len(z.infolist())!=19 or set(z.namelist())!=set(FILES) or z.testzip() is not None:
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
    if len(before)!=len(set(before)) or not OLD_FILES.issubset(set(before)) or not set(before).issubset(set(FILES)):
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
    if len(after)!=19 or set(after)!=set(FILES):raise ValueError('Unexpected final Drive file listing; inspect before claiming completion')
    print('VERIFIED: 19 Rule 804 Excel files verified in Drive. Old 13 versions replaced; 6 additional stores saved. No reports or duplicate filenames.',flush=True)
    print('Drive folder: ChotuApp 19-10-2026 11-36AM',flush=True)
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--archive',type=Path);parser.add_argument('--folder',type=Path,default=Path.home()/'Desktop'/'ChotuApp 19-10-2026 11-36AM Rule804 Updated 19 Stores');parser.add_argument('--prepare-only',action='store_true');args=parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='rule804-download-') as temp:
        archive=args.archive or Path(temp)/'catalogs.zip'
        if args.archive is None:
            print('Downloading verified Rule 804 batch...',flush=True);urllib.request.urlretrieve(URL,archive)
        folder=prepare(archive,args.folder)
    print('19 verified Rule 804 workbooks: '+str(folder),flush=True)
    print('8445 products; 20017 variant combinations. Updated Rule 804; shop_code first, one Category column. Prices, stock, variants, website order and image links preserved. Seran Noirelle and Bonanza Two of a Kind Deal have insufficient category evidence and remain blank.',flush=True)
    if not args.prepare_only:upload(folder,find_rclone())
if __name__=='__main__':main()
