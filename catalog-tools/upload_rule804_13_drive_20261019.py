"""Install the reviewed 19 October 13-store batch and replace matching Drive files."""
import argparse,hashlib,json,os,shutil,subprocess,tempfile,urllib.request,zipfile
from pathlib import Path
URL='https://raw.githubusercontent.com/chottuapp/ChotuApp-Software/5f3c27ca5954d7a7394a7deb4a03e4c29e552e6c/catalog-files/rule804-20261019-13/Rule804_13_Stores_2026-10-19.zip'
SHA256='3fa9ee641e7cefcd9581ba759ead5307929c3c0231f7f60bcf66791dde28c129'
FILES={'Adam Cheese.xlsx': '697ea0ac04ae4078fe24db60c15188ac9feb9099ee5c102e81f1999e59d72db4', 'Cool and Cool.xlsx': '34f224cbc7762b1d7e23d7a3253fd6692d4ad9da209c61db03d5d10ebf29444e', 'Denim Leftover.xlsx': 'cc2b9c92e2a3005801457e769cc83b5dcab5c42ce444247f80c97a6ae0d68804', 'Farda Foods.xlsx': '70900df2c6f9891be374050cd92406f2c9db21c74993818f0d7541610df7529c', 'Islamabad Tea.xlsx': 'd6f0b255655beb34765fed72cd634e73f396542b1c260549b86e5530d05e40a4', 'Miss Rose.xlsx': 'e89255e7a59f679331047d1e1eebf97019859750f25ea61c95cf307cb3e823d2', 'Nisa Naturals.xlsx': 'e053276726105dd8dca8878ead0ec2fe111d7fd164c396a1df31ef5af9a85969', 'Rivaj UK.xlsx': '676d8d0f0d70bdcb09f202c51bbc1a10addeeb03e61c4c3949713576c7837f4d', 'Seran.xlsx': '1220daaad41dc1cf03d50349758b6cad9aa31a3aef28bd6ffddb7b0402651537', 'Shop Modest.xlsx': '7decfe66a2592cb6be6f4d3920529296e3ef98021adf5c6273e6b3141b22a2de', 'Skin Factor.xlsx': '8defad801fd71addebacb3a676ad78841dfdf23170d3441df73f94d104cee803', 'The Hanger Pakistan.xlsx': 'fd0406ea3e79d43cdf538416a06c41dce0edeaef4734661d0ab7f7ad6cdfcbed', 'Vince Care.xlsx': '5447f360b801f5d337a52c364090ededdfd81f422f86b48e7e51b65351ec4599'}
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
    print('VERIFIED: 13 Rule 804 Excel files replaced the old Drive versions. No reports or duplicate filenames.',flush=True)
    print('Drive folder: ChotuApp 19-10-2026 11-36AM',flush=True)
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--archive',type=Path);parser.add_argument('--folder',type=Path,default=Path.home()/'Desktop'/'ChotuApp 19-10-2026 11-36AM Rule804');parser.add_argument('--prepare-only',action='store_true');args=parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='rule804-download-') as temp:
        archive=args.archive or Path(temp)/'catalogs.zip'
        if args.archive is None:
            print('Downloading verified Rule 804 batch...',flush=True);urllib.request.urlretrieve(URL,archive)
        folder=prepare(archive,args.folder)
    print('13 verified Rule 804 workbooks: '+str(folder),flush=True)
    print('2034 products; 8894 variants. Shop codes and observed website categories/order preserved.',flush=True)
    if not args.prepare_only:upload(folder,find_rclone())
if __name__=='__main__':main()
