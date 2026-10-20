"""Read-only USB backup of the installed debug preview. Never uninstall or clear data."""
import argparse,datetime,hashlib,json,os,shutil,subprocess,tarfile,tempfile
from pathlib import Path
PACKAGE='com.chotuapp.mobile'

def stream_archive(adb,serial,destination=None):
 digest=hashlib.sha256();size=0
 with tempfile.TemporaryFile() as errors:
  process=subprocess.Popen([str(adb),'-s',serial,'exec-out','run-as',PACKAGE,'tar','-cf','-','files'],stdout=subprocess.PIPE,stderr=errors)
  try:
   while True:
    chunk=process.stdout.read(1024*1024)
    if not chunk:break
    digest.update(chunk);size+=len(chunk)
    if destination:destination.write(chunk)
   code=process.wait(timeout=30)
  except BaseException:process.kill();process.wait();raise
 if code:raise RuntimeError('Phone backup read failed. Original app and files were not modified.')
 if size<1024:raise ValueError('No usable app data received')
 return digest.hexdigest(),size

def validate_archive(path):
 count=0;total=0;records=[]
 with tarfile.open(path,'r:') as archive:
  for member in archive:
   parts=Path(member.name).parts
   if not parts or parts[0]!='files' or '..' in parts or member.name.startswith('/') or not (member.isdir() or member.isfile()):raise ValueError('Unsafe or unexpected archive member')
   if not member.isfile():continue
   digest=hashlib.sha256();stream=archive.extractfile(member)
   for chunk in iter(lambda:stream.read(1024*1024),b''):digest.update(chunk)
   records.append({'path':member.name,'bytes':member.size,'sha256':digest.hexdigest()});count+=1;total+=member.size
 if not count:raise ValueError('Empty app backup')
 return records,total

def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--adb');parser.add_argument('--out');args=parser.parse_args()
 adb=args.adb or shutil.which('adb') or shutil.which('adb.exe')
 if not adb:raise SystemExit('Android Platform Tools required: https://developer.android.com/tools/releases/platform-tools — extract it and run this helper with --adb PATH_TO_ADB_EXE')
 devices=subprocess.run([str(adb),'devices'],capture_output=True,text=True,check=True).stdout.splitlines()
 ready=[line.split()[0] for line in devices if len(line.split())==2 and line.split()[1]=='device']
 if len(ready)!=1:raise SystemExit('Connect exactly one Android phone with USB debugging authorized. Nothing was changed.')
 serial=ready[0];result=subprocess.run([str(adb),'-s',serial,'exec-out','run-as',PACKAGE,'cat','files/khaadi/local-status.json'],capture_output=True,text=True)
 if result.returncode:raise SystemExit('App saved state unavailable. Nothing was changed.')
 state=json.loads(result.stdout)
 if state.get('status')=='running':raise SystemExit('Pause Khaadi inside the app first and wait for paused. Fetching has not been stopped by this helper.')
 stamp=datetime.datetime.now().strftime('%Y-%m-%d_%H%M%S');default=Path('D:/Anas_PC_Backup') if os.name=='nt' and Path('D:/').exists() else Path.home()/'Desktop/ANAS_DATA_FETCH/Android_Backups'
 folder=Path(args.out) if args.out else default/('ChotuApp_Mobile_'+stamp)
 folder.mkdir(parents=True,exist_ok=True);pending=folder/'Phone_Data.pending.tar';archive=folder/'Phone_Data.tar'
 if archive.exists() or pending.exists():raise SystemExit('Backup destination already contains an archive. Choose a new folder.')
 print('Reading phone app data. Original files are untouched.',flush=True)
 with pending.open('xb') as stream:first,size=stream_archive(adb,serial,stream)
 print('Checking the phone data a second time for an exact, stable copy...',flush=True)
 second,second_size=stream_archive(adb,serial)
 if first!=second or size!=second_size:raise RuntimeError('Phone data changed during backup. No backup marked verified; original app remains installed.')
 records,total=validate_archive(pending);pending.replace(archive)
 report={'package':PACKAGE,'verified_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'archive_sha256':first,'archive_bytes':size,'file_bytes':total,'files':records,'source_status':state.get('status'),'verification':'Two independent USB archive reads matched byte-for-byte; all archived files hashed','credentials':'Android Keystore and token preferences are not exported; reconnect GitHub after a future migration','app_modified':False}
 (folder/'Backup_Manifest.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
 print('VERIFIED BACKUP:',archive);print('FILES:',len(records),'SIZE GB:',round(total/1024**3,2));print('App remains installed. No uninstall, install, reset or data deletion was performed.')
if __name__=='__main__':main()
