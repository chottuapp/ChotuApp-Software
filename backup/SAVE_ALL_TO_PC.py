"""Read-only ChotuApp recovery download. Saves into one Desktop folder; never deletes originals."""
import datetime,hashlib,json,os,shutil,subprocess,sys,tempfile,urllib.request,zipfile
from pathlib import Path
REPO='https://github.com/chottuapp/ChotuApp-Software.git'
SNAPSHOT='backup-complete-2026-10-22'
ROOT=Path.home()/'Desktop'/'ChotuApp_FULL_BACKUP_2026-10-22'
ROOT.mkdir(parents=True,exist_ok=True)
report={'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'saved':[],'missing':[],'errors':[]}
LOG=ROOT/'BACKUP-RESULT.json'
def save_report():LOG.write_text(json.dumps(report,indent=2),encoding='utf-8')
def note(message):print(message,flush=True)
def download(url,path):
 path.parent.mkdir(parents=True,exist_ok=True)
 if path.exists() and path.stat().st_size:note('Already downloaded: '+path.name);return
 part=path.with_suffix(path.suffix+'.part')
 request=urllib.request.Request(url,headers={'User-Agent':'ChotuAppOwnerBackup/1.0'})
 with urllib.request.urlopen(request,timeout=180) as response,part.open('wb') as target:
  count=0;next_notice=25*1024*1024
  while True:
   chunk=response.read(1024*1024)
   if not chunk:break
   target.write(chunk);count+=len(chunk)
   if count>=next_notice:note('Downloaded '+str(count//(1024*1024))+' MB: '+path.name);next_notice+=25*1024*1024
 part.replace(path)
 with path.open('rb') as stream:digest=hashlib.file_digest(stream,'sha256').hexdigest()
 path.with_suffix(path.suffix+'.sha256').write_text(digest+'  '+path.name+'\n')
def command(args):subprocess.run([str(a) for a in args],check=True)
def step(name,action):
 note('\n'+name)
 try:action();report['saved'].append(name)
 except Exception as error:report['errors'].append({'step':name,'type':type(error).__name__,'detail':str(error)});note('NOT COMPLETED: '+name+' ('+type(error).__name__+')')
 save_report()
def extract():
 archive=ROOT/'ChotuApp-Complete-Source-and-Rules.zip';download('https://codeload.github.com/chottuapp/ChotuApp-Software/zip/refs/heads/'+SNAPSHOT,archive)
 target=ROOT/'Latest-Software-and-Rules';target.mkdir(exist_ok=True)
 with zipfile.ZipFile(archive) as z:
  for entry in z.infolist():
   parts=Path(entry.filename).parts[1:]
   if not parts:continue
   if any(p in ('..','') for p in parts):raise ValueError('Unsafe archive path')
   out=target.joinpath(*parts)
   if entry.is_dir():out.mkdir(parents=True,exist_ok=True);continue
   out.parent.mkdir(parents=True,exist_ok=True)
   with z.open(entry) as src,out.open('wb') as dest:shutil.copyfileobj(src,dest)
 # Integrity check for backup-specific files (including APK and owner rules).
 base=target/'backup'
 for line in (base/'SHA256SUMS.txt').read_text().splitlines():
  digest,name=line.split('  ',1);p=base/name
  with p.open('rb') as stream:actual=hashlib.file_digest(stream,'sha256').hexdigest()
  if actual!=digest:raise ValueError('Backup integrity mismatch: '+name)
 note('Source, rules, reports and signed APK extracted and verified.')
step('Latest software, signed APK, rules and report snapshots',extract)
git=shutil.which('git')
if not git:
 for candidate in [Path(os.environ.get('ProgramFiles','C:/Program Files'))/'Git/cmd/git.exe',Path(os.environ.get('LOCALAPPDATA',''))/'Programs/Git/cmd/git.exe']:
  if candidate.is_file():git=str(candidate);break
if git:
 def mirror():
  target=ROOT/'ALL_GITHUB_HISTORY.git'
  if target.exists():command([git,'-C',target,'remote','update','--prune'])
  else:command([git,'clone','--mirror',REPO,target])
  command([git,'-C',target,'fsck','--full'])
  with (ROOT/'ALL_GITHUB_REFS.txt').open('w',encoding='utf-8') as output:subprocess.run([git,'-C',str(target),'show-ref'],stdout=output,check=True)
  command([git,'-C',target,'bundle','create',ROOT/'ALL_GITHUB_HISTORY.bundle','--all'])
  command([git,'-C',target,'bundle','verify',ROOT/'ALL_GITHUB_HISTORY.bundle'])
 step('All old and latest committed GitHub history, every branch, workbook and report',mirror)
else:
 report['missing'].append('Git not installed: full historical commit mirror/bundle unavailable. Current snapshots downloaded; install Git and rerun this script for every historical version.')
 def branches():
  refs=ROOT/'Latest-Software-and-Rules/backup/repository-refs.json'
  for name,sha in json.loads(refs.read_text()).items():download('https://codeload.github.com/chottuapp/ChotuApp-Software/zip/'+sha,ROOT/'All-Branch-Snapshots'/(name+'.zip'))
 step('Every recorded branch snapshot (fallback without Git)',branches)
def local():
 desktop=Path.home()/'Desktop';found=[]
 # Only known project folders/scripts, never browser profiles, unrelated files or credentials.
 for name in ('ANAS_DATA_FETCH','ChotuApp','ChotuApp-Software','ChotuApp_Mobile','ChotuApp-Studio'):
  src=desktop/name
  if src.is_dir():note('Copying local '+name);shutil.copytree(src,ROOT/'PC-Saved-Work'/name,dirs_exist_ok=True);found.append(name)
 patterns=('watch_all_runners.py','status_original_three.py','*khaadi*.py','*sapphire*.py','*laam*.py','*chotuapp*.py')
 for pattern in patterns:
  for src in desktop.glob(pattern):
   if src.is_file():dest=ROOT/'PC-Saved-Work'/'Desktop-Scripts'/src.name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dest)
 if not found:report['missing'].append('No known Desktop ChotuApp data folders found. Other locations and phone-private data require separate export.')
step('Existing PC saved fetch data and project scripts (copies only)',local)
rclone=shutil.which('rclone')
if rclone:
 try:remotes=subprocess.check_output([rclone,'listremotes'],text=True,timeout=30).splitlines()
 except Exception:remotes=[]
 if 'chotudrive:' in remotes:
  step('Read-only copy of final Google Drive folder',lambda:command([rclone,'copy','chotudrive:ChotuApp 19-10-2026 11-36AM',ROOT/'Google-Drive-Files','--progress']))
 else:report['missing'].append('Local rclone chotudrive connection unavailable; external Drive files not downloaded.')
else:report['missing'].append('rclone unavailable locally; external Google Drive files not downloaded. Download the destination folder separately into Google-Drive-Files.')
report['missing'] += ['GitHub Actions secret values and Google/AWS passwords or tokens are not exportable from the repository.','Private APK signing key is NOT in public GitHub; keep owner encrypted key backup separately.','Phone-private fetching cache/data and full ChatGPT transcript are not in this backup unless separately exported.','Actions-only checkpoints not committed to Git may expire; Git mirror does not contain those artifact bytes.']
report['finished_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat();save_report()
(ROOT/'READ-ME-FIRST.txt').write_text('Your backup is in this one folder. Read Latest-Software-and-Rules/backup/START-HERE.md and HANDOVER.md.\nALL_GITHUB_HISTORY.bundle plus mirror contain every reachable committed old/latest version, all branches and preserved data. Do not delete your original PC files.\nRead BACKUP-RESULT.json for exact completed steps, errors and missing external data. This is not a complete account/device disk image.\n',encoding='utf-8')
note('\nBACKUP FOLDER: '+str(ROOT));note('Completed steps: '+str(len(report['saved']))+'; failed steps: '+str(len(report['errors'])));note('Read BACKUP-RESULT.json for missing external/private items.')
if os.name=='nt':os.startfile(str(ROOT))
if report['errors']:sys.exit(1)
