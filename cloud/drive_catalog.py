"""Read Drive IDs and historical checksum verification times. Never writes to Drive."""
import base64,configparser,datetime,json,os,re,subprocess,tempfile
from pathlib import Path
from source_research import publish
from drive_sync import config_text,gh,REPO

def enrich(state,folders,files,histories):
 folder=state['folder'];matches=[row for row in folders if row.get('IsDir') and row.get('Name')==folder]
 if len(matches)!=1 or not matches[0].get('ID'):raise ValueError('Unique Drive destination folder not found')
 folder_id=matches[0]['ID'];state['folder_id']=folder_id;state['folder_url']='https://drive.google.com/drive/folders/'+folder_id
 by_name={}
 for row in files:
  if not row.get('IsDir'):by_name.setdefault(row.get('Name'),[]).append(row)
 for group in ('uploaded','original_uploads'):
  for store,record in state.get(group,{}).items():
   if record.get('folder')!=folder:continue
   matching=by_name.get(store+'.xlsx',[])
   record['folder_id']=folder_id;record['folder_url']=state['folder_url']
   if len(matching)==1 and matching[0].get('ID'):
    row=matching[0];record.update(file_id=row['ID'],file_url='https://drive.google.com/file/d/'+row['ID']+'/view',drive_modified_utc=row.get('ModTime'))
   else:
    record.pop('file_id',None);record.pop('file_url',None)
   # ModTime may be copied from the source workbook: never call it upload time.
   if not record.get('verified_utc'):
    dates=[]
    for old in histories:
     previous=old.get(group,{}).get(store,{})
     if previous.get('sha256')==record.get('sha256') and previous.get('folder')==folder:
      timestamp=previous.get('verified_utc') or old.get('verified_utc')
      try:dates.append(datetime.datetime.fromisoformat(timestamp))
      except (TypeError,ValueError):pass
    if dates:record.update(verified_utc=min(dates).isoformat(),timestamp_source='Historical checksum verification report')
   if store in state.get('daily_uploads',{}).get(folder,{}):state['daily_uploads'][folder][store]=dict(record)
 return state

def main():
 secret=os.environ.get('CHOTU_DRIVE_RCLONE_CONFIG','');config_text(secret)
 response=json.loads(gh('api','repos/'+REPO+'/contents/latest.json?ref=drive-sync-reports'));state=json.loads(base64.b64decode(response['content']))
 folder=state['folder']
 if '/' in folder or '\\' in folder or ':' in folder:raise ValueError('Unexpected folder path')
 with tempfile.TemporaryDirectory() as tmp:
  cfg=Path(tmp)/'rclone.conf';cfg.write_text(secret);cfg.chmod(0o600)
  def listing(remote,*args):
   r=subprocess.run(['rclone','--config',str(cfg),'lsjson',remote,*args],capture_output=True,text=True,timeout=180)
   if r.returncode:raise RuntimeError('Read-only Drive listing unavailable')
   return json.loads(r.stdout)
  folders=listing('chotudrive:','--dirs-only','--max-depth','1');files=listing('chotudrive:'+folder,'--files-only','--max-depth','1')
 def git(*args):return subprocess.check_output(['git',*args],stderr=subprocess.DEVNULL,text=True)
 git('fetch','--depth=1','origin','refs/heads/drive-sync-reports')
 histories=[]
 for name in git('ls-tree','-r','--name-only','FETCH_HEAD','runs/').splitlines():
  if not re.fullmatch(r'runs/\d+\.json',name):continue
  try:histories.append(json.loads(git('show','FETCH_HEAD:'+name)))
  except (ValueError,subprocess.CalledProcessError):pass
 enrich(state,folders,files,histories);state['run_id']=os.environ['GITHUB_RUN_ID'];state['catalog_checked_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat();publish(state,branch='drive-sync-reports')
 print('Read-only Drive catalog refreshed:',len(state.get('uploaded',{})),'store records. No files uploaded, moved or deleted.')
if __name__=='__main__':main()
