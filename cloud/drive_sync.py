"""Upload only checksum-validated Rule 804 fresh-batch artifacts; never raw exports."""
import base64,configparser,datetime,hashlib,importlib.util,json,os,subprocess,sys,tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from source_research import publish
ROOT=Path(__file__).resolve().parents[1];REPO='chottuapp/ChotuApp-Software'
spec=importlib.util.spec_from_file_location('drive_checked',ROOT/'catalog-tools/start_fresh26_rule804_drive_windows.py');checked=importlib.util.module_from_spec(spec);spec.loader.exec_module(checked)
def gh(*args):
 r=subprocess.run(['gh',*args],capture_output=True,text=True,timeout=600)
 if r.returncode:raise RuntimeError('GitHub operation failed: '+args[0]+'; saved Drive files retained')
 return r.stdout

def config_text(value):
 cfg=configparser.ConfigParser(interpolation=None);cfg.read_string(value)
 if cfg.sections()!=['chotudrive'] or cfg['chotudrive'].get('type')!='drive' or not cfg['chotudrive'].get('token'):raise ValueError('Only the existing chotudrive Google Drive remote may be configured')
 return value

def main():
 secret=os.environ.get('CHOTU_DRIVE_RCLONE_CONFIG','')
 if not secret:raise RuntimeError('CHOTU_DRIVE_RCLONE_CONFIG secret not configured; no Drive upload attempted')
 config_text(secret)
 config=json.loads((ROOT/'cloud/drive-sync-release.json').read_text());root=config['dispatcher'];folder=config.get('destination_folder') or checked.daily_folder()
 if '/' in folder or '\\' in folder or ':' in folder or folder in ('.','..',''):raise ValueError('Invalid destination folder')
 try:
  old=json.loads(gh('api','repos/'+REPO+'/contents/latest.json?ref=drive-sync-reports'))
  state=json.loads(base64.b64decode(old['content']))
 except RuntimeError:state={}
 if state.get('dispatcher')!=root:state={'dispatcher':root,'processed_artifacts':{},'uploaded':{},'daily_uploads':{}}
 state['folder']=folder;state.setdefault('daily_uploads',{}).setdefault(folder,{})
 state['run_id']=os.environ['GITHUB_RUN_ID'];state['sync_status']='scanning';state['last_scan_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat();globals()['LAST_STATE']=state
 state.pop('sync_error',None);publish(state,branch='drive-sync-reports')
 runs=json.loads(gh('run','list','--repo',REPO,'--workflow','cloud-fetch.yml','--limit','100','--json','databaseId,displayTitle,status,conclusion'))
 groups={r['displayTitle'].removeprefix('Cloud group ') for r in runs if r['displayTitle'].startswith('Cloud group fresh26-'+root+'-')}
 runs=checked.related(runs,groups)
 if not runs and not (ROOT/'catalog-inputs/khaadi-mobile/latest.json').exists():raise RuntimeError('No matching authorized fresh-batch runs found')
 with tempfile.TemporaryDirectory() as tmp:
  cfg=Path(tmp)/'rclone.conf';cfg.write_text(secret,encoding='utf-8');cfg.chmod(0o600)
  def rc(*args):
   result=subprocess.run(['rclone','--config',str(cfg),*args],capture_output=True,text=True,timeout=900)
   if result.returncode:raise RuntimeError('Drive '+args[0]+' failed; upload not marked verified')
  from mobile_khaadi_ingest import upload as upload_mobile
  if upload_mobile(state,folder,rc):
   state['verified_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat();publish(state,branch='drive-sync-reports')
   print('VERIFIED: mobile Khaadi processed with Rule 804 and checksum-checked in',folder,flush=True)
  for run in reversed(runs):
   rid=str(run['databaseId']);artifacts=json.loads(gh('api','repos/'+REPO+'/actions/runs/'+rid+'/artifacts?per_page=100'))['artifacts']
   matches=[a for a in artifacts if a['name']=='chotuapp-rule804-files' and not a.get('expired')]
   if not matches:continue
   artifact=max(matches,key=lambda a:a['id'])
   if state['processed_artifacts'].get(rid)==artifact['id']:continue
   with tempfile.TemporaryDirectory(dir=tmp) as stage:
    gh('run','download',rid,'--repo',REPO,'--name','chotuapp-rule804-files','--dir',stage)
    manifests=list(Path(stage).rglob('manifest.json'))
    if len(manifests)!=1:raise ValueError('Unique Rule 804 manifest required')
    manifest=json.loads(manifests[0].read_text());files=checked.checked_files(Path(stage),manifest)
    files=[(item,file) for item,file in files if state['uploaded'].get(item['store'],{}).get('sha256')!=item['sha256']]
    approved=set(config['stores']);upload=Path(stage)/'verified';upload.mkdir()
    for item,file in files:
     if item['store'] not in approved:raise ValueError('Store outside authorized Drive scope')
     import shutil
     shutil.copy2(file,upload/file.name)
    if files:
     remote='chotudrive:'+folder
     rc('copy',str(upload),remote,'--include','*.xlsx','--checksum')
     rc('check',str(upload),remote,'--include','*.xlsx','--one-way')
     for item,file in files:
      record={'sha256':item['sha256'],'rule804':item['rule804'],'warnings':item.get('warnings',[]),'source_run':rid,'folder':folder,'verified_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
      state['uploaded'][item['store']]=record;state['daily_uploads'][folder][item['store']]=record
    state.setdefault('held',{})[rid]=manifest.get('held',[])
    state['processed_artifacts'][rid]=artifact['id'];state['verified_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat();state['run_id']=os.environ['GITHUB_RUN_ID']
    publish(state,branch='drive-sync-reports')
    print('VERIFIED:',len(files),'Rule 804 workbooks in',folder,'| total verified:',len(state['uploaded']),'/26',flush=True)
 state['sync_status']='finished';state['run_id']=os.environ['GITHUB_RUN_ID'];publish(state,branch='drive-sync-reports')
 print('Drive sync finished. Existing files retained. No raw workbooks or reports uploaded.')
if __name__=='__main__':
 try:main()
 except Exception as exc:
  state=globals().get('LAST_STATE')
  if state is not None:
   state['sync_status']='failed';state['sync_error']=str(exc);publish(state,branch='drive-sync-reports')
  raise
