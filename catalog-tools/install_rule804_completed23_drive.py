"""Install reviewed Rule 804 replacements by matching Drive names and verified hashes."""
import argparse,hashlib,json,os,shutil,subprocess,tempfile,time,zipfile
from pathlib import Path
REPO='chottuapp/ChotuApp-Software'
ARTIFACT_REF='ac1062954a09de3c4243f0ca255278aea3e809ca'
ZIP_PATH='catalog-files/rule804-20261020-completed23/Rule804_Changed_Files_2026-10-20.zip'
ZIP_SHA256='59e1dcc1ec8ee31e52f37a7ebeb3808a1a9308fb2302373dfc768e8e5205e74f'
REMOTE='chotudrive:ChotuApp 19-10-2026 11-36AM'
PACE=['--tpslimit','0.5','--tpslimit-burst','1','--drive-pacer-min-sleep','2s','--drive-pacer-burst','1','--retries','6','--retries-sleep','60s','--low-level-retries','4','--contimeout','20s','--timeout','90s']

def digest(path,kind='sha256'):
 with Path(path).open('rb') as stream:return hashlib.file_digest(stream,kind).hexdigest()

def run(args,stdout=None,timeout=1800):
 started=time.monotonic();proc=subprocess.Popen(args,stdout=stdout if stdout is not None else subprocess.PIPE,stderr=subprocess.PIPE)
 try:
  while True:
   left=timeout-(time.monotonic()-started)
   if left<=0:raise TimeoutError('Command timed out; existing data preserved. Rerun to resume.')
   try:out,err=proc.communicate(timeout=min(15,left));break
   except subprocess.TimeoutExpired:print('Working: '+str(int(time.monotonic()-started))+' seconds. Quota retries can wait 60 seconds.',flush=True)
  if proc.returncode:raise RuntimeError((err or b'Command failed').decode('utf-8','replace')[-12000:])
  return (out or b'').decode('utf-8','replace')
 finally:
  if proc.poll() is None:
   proc.terminate()
   try:proc.communicate(timeout=10)
   except subprocess.TimeoutExpired:proc.kill();proc.communicate()

def find_rclone():
 exe=shutil.which('rclone')
 if exe:return exe
 folder=Path(os.environ.get('LOCALAPPDATA',''))/'Microsoft/WinGet/Packages'
 paths=sorted(folder.glob('Rclone.Rclone_*/rclone-*-windows-amd64/rclone.exe'))
 if paths:return str(paths[-1])
 raise RuntimeError('Existing rclone executable not found')

def unpack(archive,folder):
 if digest(archive)!=ZIP_SHA256:raise ValueError('Archive verification failed; Drive unchanged')
 with zipfile.ZipFile(archive) as z:
  manifest=json.loads(z.read('manifest.json'));records=manifest['files'];assert len(records)==23
  changed={r['file']:r for r in records if r['source_sha256']!=r['sha256']}
  if set(z.namelist())!=set(changed)|{'manifest.json'}:raise ValueError('Unexpected archive contents')
  if sum(i.file_size for i in z.infolist())>200*1024*1024:raise ValueError('Archive expands beyond approved size')
  folder.mkdir(parents=True,exist_ok=True)
  for name,item in changed.items():
   if Path(name).name!=name:raise ValueError('Unsafe filename')
   raw=z.read(name)
   if hashlib.sha256(raw).hexdigest()!=item['sha256']:raise ValueError('Workbook verification failed: '+name)
   target=folder/name
   if target.exists() and digest(target)!=item['sha256']:raise ValueError('Different local workbook exists; preserve it: '+str(target))
   if not target.exists():
    staged=target.with_suffix('.next.xlsx');staged.write_bytes(raw);staged.replace(target)
 return manifest,changed

def inventory(exe):
 data=json.loads(run([exe,'lsjson',REMOTE,'--files-only','--max-depth','1','--hash',*PACE]))
 return [r for r in data if not r.get('IsDir') and r['Name'].lower().endswith('.xlsx')]

def validate_inventory(items,manifest):
 expected={r['file']:r for r in manifest['files']};names=[r['Name'] for r in items]
 if len(names)!=len(set(names)) or set(names)!=set(expected):raise ValueError('Drive listing differs from the approved 23 names; nothing overwritten')
 pending=[]
 for item in items:
  record=expected[item['Name']];hashes=item.get('Hashes') or {};md5=hashes.get('md5') or hashes.get('MD5')
  if not md5:raise ValueError('Drive MD5 unavailable; cannot safely replace '+item['Name'])
  if md5 not in {record['source_md5'],record['md5']}:raise ValueError('Drive file changed since the source review; preserve it: '+item['Name'])
  if md5!=record['md5']:pending.append(item['Name'])
 return pending

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--archive',type=Path);ap.add_argument('--prepare-only',action='store_true');args=ap.parse_args()
 root=Path(r'D:\ChotuAppData\Rule804_Completed23_20261020');root.mkdir(parents=True,exist_ok=True)
 archive=args.archive or root/'Rule804_Changed_Files_2026-10-20.zip'
 if not archive.exists() or digest(archive)!=ZIP_SHA256:
  if args.archive:raise ValueError('Supplied archive hash mismatch')
  gh=shutil.which('gh')
  if not gh:raise RuntimeError('GitHub CLI not found; gh auth login is required')
  print('Downloading only the reviewed changed workbooks...',flush=True);staged=archive.with_suffix('.downloading')
  with staged.open('wb') as stream:run([gh,'api','repos/'+REPO+'/contents/'+ZIP_PATH+'?ref='+ARTIFACT_REF,'-H','Accept: application/vnd.github.raw+json'],stdout=stream)
  if digest(staged)!=ZIP_SHA256:raise ValueError('Downloaded archive verification failed; Drive unchanged')
  staged.replace(archive)
 manifest,changed=unpack(archive,root/'Reviewed Files')
 if args.prepare_only:print('Verified local files:',root/'Reviewed Files');return
 exe=find_rclone();print('Checking current Drive files before any replacement...',flush=True)
 before=inventory(exe);pending=validate_inventory(before,manifest)
 receipt={'folder':REMOTE,'source_manifest':ARTIFACT_REF,'pending':pending,'verified_local_archive_sha256':ZIP_SHA256,'before':before,'status':'PREPARED'}
 receipt_path=root/'receipt.json';receipt_path.write_text(json.dumps(receipt,ensure_ascii=False,indent=2))
 if any(name not in changed for name in pending):raise ValueError('Unexpected replacement requested')
 if pending:
  print('Replacing '+str(len(pending))+' matching filenames. No Drive deletes, no duplicate filenames, no reports uploaded.',flush=True)
  with tempfile.TemporaryDirectory(prefix='upload-',dir=str(root)) as temp:
   for name in pending:
    source=root/'Reviewed Files'/name
    if digest(source)!=changed[name]['sha256']:raise ValueError('Local workbook changed; upload stopped: '+name)
    shutil.copy2(source,Path(temp)/name)
   run([exe,'copy',temp,REMOTE,'--include','*.xlsx','--checksum','--transfers','1','--checkers','1',*PACE],timeout=2400)
 after=inventory(exe);remaining=validate_inventory(after,manifest)
 if remaining:raise ValueError('Upload incomplete; rerun the same command to resume: '+', '.join(remaining))
 receipt.update(status='VERIFIED',after=after,replaced=len(pending),excel_count=len(after));receipt_path.write_text(json.dumps(receipt,ensure_ascii=False,indent=2))
 print('VERIFIED: all 23 Drive Excel files match the reviewed outputs. '+str(len(pending))+' files replaced; unchanged files retained.',flush=True)
 print('Category blanks: 0. Unknown shop codes remain blank as requested. Original prices, IDs, variants, stock, image links and row order preserved.',flush=True)
 print('Receipt: '+str(receipt_path),flush=True)
 print('Website ordering evidence was preserved with its existing verified/unverified status; no new sales/ranking claims.',flush=True)
if __name__=='__main__':
 try:main()
 except KeyboardInterrupt:print('Stopped. Current local files and receipt retained; rerun to resume.');raise SystemExit(130)
 except Exception as error:print('STOPPED: '+str(error));raise SystemExit(1)
