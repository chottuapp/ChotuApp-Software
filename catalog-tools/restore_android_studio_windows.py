"""Restore verified Khaadi data into an empty Studio install; keep original app intact."""
import argparse,hashlib,io,json,subprocess,tarfile,tempfile,uuid
from pathlib import Path
PACKAGE='com.chotuapp.studio'
def prepare(archive,manifest,destination):
 report=json.loads(Path(manifest).read_text(encoding='utf-8'))
 digest=hashlib.sha256()
 with Path(archive).open('rb') as stream:
  for chunk in iter(lambda:stream.read(1024*1024),b''):digest.update(chunk)
 if digest.hexdigest()!=report.get('archive_sha256'):raise ValueError('Backup checksum mismatch')
 expected={entry['path']:entry for entry in report['files']};count=0
 with tarfile.open(archive,'r:') as source,tarfile.open(destination,'w:') as target:
  for item in source:
   parts=Path(item.name).parts
   if '..' in parts or item.name.startswith('/') or not (item.isfile() or item.isdir()):raise ValueError('Unsafe backup entry')
   if not item.isfile():continue
   if not item.name.startswith('files/khaadi/'):continue
   # Never import executable code, stale locks, credentials or worker preferences.
   if item.name.endswith(('.lock','.py','.pyc','.pending')):continue
   data=source.extractfile(item).read();entry=expected.get(item.name)
   if not entry or hashlib.sha256(data).hexdigest()!=entry['sha256'] or len(data)!=entry['bytes']:raise ValueError('File verification failed')
   if item.name=='files/khaadi/local-status.json':
    state=json.loads(data)
    if state.get('status')=='running':raise ValueError('Backup was not paused')
    state['files']=['/data/user/0/'+PACKAGE+'/files/khaadi/files/'+Path(path).name for path in state.get('files',[])]
    data=json.dumps(state,indent=2).encode()
   record=tarfile.TarInfo(item.name);record.size=len(data);record.mode=0o600;target.addfile(record,io.BytesIO(data));count+=1
 if not count:raise ValueError('No Khaadi saved data in backup')
 return count

def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('backup_folder');parser.add_argument('--adb',required=True);args=parser.parse_args();folder=Path(args.backup_folder)
 def adb(*parts,**kwargs):return subprocess.run([args.adb,*parts],check=True,capture_output=True,**kwargs)
 devices=adb('devices').stdout.decode().splitlines();ready=[line.split()[0] for line in devices if len(line.split())==2 and line.split()[1]=='device']
 if len(ready)!=1:raise SystemExit('Exactly one authorized USB phone required')
 serial=ready[0]
 # Refuse to overwrite even a partial fetch in Studio. The old app is never touched.
 result=adb('-s',serial,'shell','run-as',PACKAGE,'sh','-c',"'test ! -e files/khaadi/local-status.json && test ! -e files/khaadi/responses.sqlite3 && test ! -e files/khaadi/api.sqlite3'")
 with tempfile.TemporaryDirectory() as tmp:
  payload=Path(tmp)/'restore.tar';count=prepare(folder/'Phone_Data.tar',folder/'Backup_Manifest.json',payload)
  remote='/data/local/tmp/chotuapp-restore-'+uuid.uuid4().hex+'.tar'
  adb('-s',serial,'push',str(payload),remote)
  try:
   adb('-s',serial,'shell','chmod','644',remote)
   adb('-s',serial,'shell','run-as',PACKAGE,'tar','-xf',remote)
   digest=hashlib.sha256()
   with payload.open('rb') as stream:
    for chunk in iter(lambda:stream.read(1024*1024),b''):digest.update(chunk)
   # Verify every restored file against the exact payload, including rebased state.
   with tarfile.open(payload,'r:') as archive:
    for item in archive:
     data=adb('-s',serial,'exec-out','run-as',PACKAGE,'cat',item.name).stdout
     if hashlib.sha256(data).digest()!=hashlib.sha256(archive.extractfile(item).read()).digest():raise RuntimeError('Restore verification failed; do not start fetching')
  finally:adb('-s',serial,'shell','rm',remote)
 print('RESTORE VERIFIED:',count,'saved files. Original app remains intact. Open Studio, reconnect GitHub, then Start / Resume. Cached pages will be reused; listing counters may replay cached work.')
if __name__=='__main__':main()
