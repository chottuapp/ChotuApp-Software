"""Download verified reviewed catalogs and copy Excel files to the user's rclone Drive."""
import argparse,hashlib,os,shutil,subprocess,tempfile,urllib.request,zipfile
from pathlib import Path
URL='https://raw.githubusercontent.com/chottuapp/ChotuApp-Software/ae184d96ed7ad41375cecf2ca95129a348cc77a7/catalog-files/rule804-20261018-fresh12/Rule804_12_Stores_2026-10-18.zip'
SHA256='1703783b3b509e2288c6d2ce217195eec915e6bb25aa44baed1780ce1e3698e7'
DESTINATION='chotudrive:ChotuApp 18-10-2026'
EXPECTED={n+'_Rule804.xlsx' for n in ('Adam_Cheese','Cool_and_Cool','Denim_Leftover','Farda_Foods','Islamabad_Tea','Miss_Rose','Nisa_Naturals','Rivaj_UK','Seran','Shop_Modest','Skin_Factor','The_Hanger_Pakistan')}
def prepare(archive,folder):
    if hashlib.sha256(archive.read_bytes()).hexdigest()!=SHA256:raise ValueError('Download checksum mismatch; nothing uploaded')
    with zipfile.ZipFile(archive) as z:
        if set(z.namelist())!=EXPECTED or len(z.infolist())!=12 or z.testzip() is not None:raise ValueError('Unexpected archive contents')
        folder.mkdir(parents=True,exist_ok=True)
        for name in sorted(EXPECTED):
            payload=z.read(name);target=folder/name
            if target.exists() and target.read_bytes()!=payload:raise ValueError('Existing local file differs: '+str(target)+'; preserve it in another folder first')
        for name in sorted(EXPECTED):
            target=folder/name
            if not target.exists():
                temp=folder/(name+'.downloading');temp.write_bytes(z.read(name));temp.replace(target)
    return folder

def find_rclone():
    found=shutil.which('rclone')
    if found:return found
    local=os.environ.get('LOCALAPPDATA')
    if local:
        candidates=sorted((Path(local)/'Microsoft/WinGet/Packages').glob('Rclone.Rclone_*/rclone-*-windows-amd64/rclone.exe'))
        if candidates:return str(candidates[-1])
    raise FileNotFoundError('rclone not found; open a new CMD after installing rclone')
def upload(folder,executable):
    remotes=subprocess.run([executable,'listremotes'],capture_output=True,text=True,check=True,timeout=60)
    if 'chotudrive:' not in remotes.stdout.splitlines():raise ValueError('Configured chotudrive remote not found; no upload attempted')
    subprocess.run([executable,'copy',str(folder),DESTINATION,'--include','*.xlsx','--checksum','--progress'],check=True)
    subprocess.run([executable,'check',str(folder),DESTINATION,'--include','*.xlsx','--one-way'],check=True)
    print('VERIFIED: 12 Excel files in Google Drive / ChotuApp 18-10-2026',flush=True)
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--archive',type=Path);parser.add_argument('--folder',type=Path,default=Path.home()/'Desktop'/'ChotuApp 18-10-2026');parser.add_argument('--prepare-only',action='store_true');args=parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='chotu804-') as temp:
        archive=args.archive or Path(temp)/'catalogs.zip'
        if not args.archive:
            print('Downloading 12 reviewed workbooks...',flush=True)
            urllib.request.urlretrieve(URL,archive)
        folder=prepare(archive,args.folder)
    # Upload from an isolated directory: unrelated local .xlsx files never enter the batch.
    print('Verified Excel files saved:',folder,flush=True)
    if args.prepare_only:return
    with tempfile.TemporaryDirectory(prefix='chotu804-upload-') as temp:
        source=Path(temp)
        for name in EXPECTED:shutil.copy2(folder/name,source/name)
        upload(source,find_rclone())
if __name__=='__main__':main()
