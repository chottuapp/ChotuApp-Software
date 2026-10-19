"""Install the reviewed 19 October 13-store batch and replace matching Drive files."""
import argparse,hashlib,json,os,shutil,subprocess,tempfile,urllib.request,zipfile
from pathlib import Path
URL='https://raw.githubusercontent.com/chottuapp/ChotuApp-Software/52a819f5332e7de973e373333a0b86bac24cf0a3/catalog-files/rule804-20261019-13-product-types/Rule804_13_Stores_Product_Categories_2026-10-19.zip'
SHA256='935925320f01ef55600d37cef5e7346ca295bb911b566b22bf7f554e4a204184'
FILES={'Islamabad Tea.xlsx': '0ef73ad4fe7f59ee0498abec75c46b7add61ec98d653dd33c9261ed3a4d844c7', 'Rivaj UK.xlsx': 'a5c32769fb643a9fb71ea0fe986124eb52a9bfe3551a62941ec4b942ba02b356', 'Farda Foods.xlsx': 'b23995ab2e45af30c0574e7fc0dbc27750ab834413c4ff62fefcc9e1dcfe2dc3', 'Miss Rose.xlsx': '6d43200fc77fa4526904d86fbf4bf4a8d4a55703e80646d8e1875194573ce704', 'Seran.xlsx': 'a9bb9f311d2d679ee69daa6ff690768aac19e466c65bee650db4405bd2734e53', 'Adam Cheese.xlsx': 'd4c58e57476c19f3a29bcaed460438eaac6632e9fd04292be32d00f1c4d7f4c8', 'Shop Modest.xlsx': '6a4d313f3504909cd9d30c1715cf84bb4ea4112d211811c6d61005189609e276', 'Nisa Naturals.xlsx': '54a71f9f1744d48e389c2984ed43e33377da6cee27589f0da12f43e3f2f44d1c', 'The Hanger Pakistan.xlsx': '93c4e6d47a7b6e489b57f0c2e30badd38e0f210491256a419b0a8206045abcb0', 'Skin Factor.xlsx': '0b9ccfc5243ca3152948f01f2608000d728194bf9892844bc0c66fdbdc21d7de', 'Vince Care.xlsx': '7b55bfadaa8a4cd4fa6309350b71653188bc42d02f06f93f1d4a9cda39c73963', 'Cool and Cool.xlsx': '440d8e918319c9f606c8e478437ddc656253e53674a06f1df333e0bf6ae43717', 'Denim Leftover.xlsx': '47e740aace622dbfb44e6446092f2c21b78463a5604f65056de990898fa93c8c'}
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
    print('VERIFIED: 13 product-type Category Rule 804 Excel files replaced the old Drive versions. No reports or duplicate filenames.',flush=True)
    print('Drive folder: ChotuApp 19-10-2026 11-36AM',flush=True)
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--archive',type=Path);parser.add_argument('--folder',type=Path,default=Path.home()/'Desktop'/'ChotuApp 19-10-2026 11-36AM Rule804 Product Categories');parser.add_argument('--prepare-only',action='store_true');args=parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='rule804-download-') as temp:
        archive=args.archive or Path(temp)/'catalogs.zip'
        if args.archive is None:
            print('Downloading verified Rule 804 batch...',flush=True);urllib.request.urlretrieve(URL,archive)
        folder=prepare(archive,args.folder)
    print('13 verified Rule 804 workbooks: '+str(folder),flush=True)
    print('2034 products; 8894 variants. 1326 Category labels refined by supported product type/purpose. Website taxonomy and order, shop codes, descriptions, prices, formulas and links preserved. Seran Noirelle remains unresolved.',flush=True)
    if not args.prepare_only:upload(folder,find_rclone())
if __name__=='__main__':main()
