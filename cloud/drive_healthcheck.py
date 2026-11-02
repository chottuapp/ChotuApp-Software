"""Verify the configured delivery remote using only our own unique tiny marker."""
import json,os,tempfile
from pathlib import Path
from drive_sync import config_text,drive_command,load_config,DriveOperationError

def main():
 run=os.environ['GITHUB_RUN_ID']
 if not run.isdigit():raise ValueError('Invalid run identity')
 folder=load_config()['destination_folder']
 if any(c in folder for c in '/\\:') or folder in ('','.','..'):raise ValueError('Invalid folder')
 remote='chotudrive:'+folder+'/_healthcheck/'+run
 result={'status':'failed','stage':'configure'}
 with tempfile.TemporaryDirectory() as tmp:
  root=Path(tmp);cfg=root/'rclone.conf';cfg.write_text(config_text(os.environ['CHOTU_DRIVE_RCLONE_CONFIG']));cfg.chmod(0o600)
  source=root/'source';source.mkdir();(source/'probe.txt').write_text('ChotuApp delivery verification '+run+'\n')
  created=[]
  try:
   result['stage']='list';drive_command(cfg,'lsjson','chotudrive:'+folder,'--files-only','--max-depth','1')
   result['stage']='upload';drive_command(cfg,'copy',str(source),remote,'--checksum');created.append(remote+'/probe.txt')
   result['stage']='uploaded_checksum';drive_command(cfg,'check',str(source),remote,'--one-way')
   result['stage']='server_copy';drive_command(cfg,'copyto',remote+'/probe.txt',remote+'/copied.txt','--checksum');created.append(remote+'/copied.txt')
   result['stage']='download';download=root/'copied.txt';drive_command(cfg,'copyto',remote+'/copied.txt',str(download))
   if download.read_bytes()!=(source/'probe.txt').read_bytes():raise ValueError('Probe checksum mismatch')
   result.update(status='pass',stage='verified')
  except DriveOperationError as exc:result.update(category=exc.category)
  finally:
   cleanup=[]
   for path in created:
    try:drive_command(cfg,'deletefile',path)
    except DriveOperationError as exc:cleanup.append(exc.category)
   if cleanup:result['cleanup_errors']=cleanup
 print(json.dumps(result,sort_keys=True))
if __name__=='__main__':main()
