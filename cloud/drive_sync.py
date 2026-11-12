"""Upload only checksum-validated Rule 804 fresh-batch artifacts; never raw exports."""
import base64,configparser,datetime,hashlib,importlib.util,json,os,subprocess,sys,tempfile,re
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from source_research import publish
from github_json import read_json
ROOT=Path(__file__).resolve().parents[1];REPO='chottuapp/ChotuApp-Software'
spec=importlib.util.spec_from_file_location('drive_checked',ROOT/'catalog-tools/start_fresh26_rule804_drive_windows.py');checked=importlib.util.module_from_spec(spec);spec.loader.exec_module(checked)
class GitHubOperationError(RuntimeError):
 def __init__(self,args,detail,*,timeout=False):
  from diagnostics import redact
  safe=redact(str(detail))[:1200]
  self.not_found=bool(re.search(r'(?i)HTTP\s+404\b',safe))
  self.transient=timeout or bool(re.search(r'(?i)HTTP\s+(?:429|50[0234])|timed?\s*out|unexpected EOF|connection reset|temporary failure|TLS handshake timeout',safe))
  super().__init__('GitHub operation failed: '+' '.join(args[:2])+'; saved Drive files retained; '+safe)

def gh(*args):
 try:r=subprocess.run(['gh',*args],capture_output=True,text=True,timeout=600)
 except subprocess.TimeoutExpired as exc:raise GitHubOperationError(args,'command timeout',timeout=True) from exc
 if r.returncode:raise GitHubOperationError(args,r.stderr)
 return r.stdout

def config_text(value):
 cfg=configparser.ConfigParser(interpolation=None);cfg.read_string(value)
 if cfg.sections()!=['chotudrive'] or cfg['chotudrive'].get('type')!='drive' or not cfg['chotudrive'].get('token'):raise ValueError('Only the existing chotudrive Google Drive remote may be configured')
 return value

class DriveOperationError(RuntimeError):
 """Expose an actionable category without logging remote paths or credentials."""
 def __init__(self,operation,detail='',*,timeout=False):
  text=str(detail).lower()
  categories=(('storage_quota',('storagequotaexceeded','storage quota','quota exceeded for quota metric \'storage')),
              ('rate_limit',('ratelimitexceeded','rate limit','too many requests','error 429')),
              ('authentication',('invalid_grant','invalid credentials','token expired','error 401')),
              ('permission',('insufficientpermissions','insufficientfilepermissions','permission denied','error 403')),
              ('not_found',('not found','error 404')),
              ('temporary_service',('error 500','error 502','error 503','error 504','connection reset','i/o timeout','temporary failure')))
  self.category='timeout' if timeout else next((name for name,needles in categories if any(n in text for n in needles)),'unclassified')
  self.transient=self.category in {'rate_limit','temporary_service','timeout'}
  super().__init__('Drive '+operation+' failed; category='+self.category+'; upload not marked verified')

def drive_command(config,*args):
 try:result=subprocess.run(['rclone','--config',str(config),*args],capture_output=True,text=True,timeout=900)
 except subprocess.TimeoutExpired as exc:raise DriveOperationError(args[0],timeout=True) from None
 if result.returncode:raise DriveOperationError(args[0],result.stderr) from None
 return getattr(result,'stdout','')

def load_config():
 config=json.loads((ROOT/'cloud/drive-sync-release.json').read_text())
 request_path=ROOT/'cloud/audit804-release.json'
 if config.get('audit804_enabled') and request_path.exists():
  request=json.loads(request_path.read_text())
  if request.get('campaign_id')==config['dispatcher'] and request.get('refresh_generation'):
   if request.get('destination_folder')!=config['destination_folder']:raise ValueError('Fresh fetch destination differs from approved Drive destination')
   from fresh804_dispatch import selected_sites
   registry=json.loads((ROOT/'cloud/fetch-update-release.json').read_text())['fresh_stores']
   names=[site['name'] for site in selected_sites(registry,request)]
   if not set(names)<=set(config['stores']):raise ValueError('Fresh fetch includes stores outside approved Drive delivery')
   config.update(refresh_generation=request['refresh_generation'],refresh_stores=names,
    refresh_requested_utc=request.get('requested_utc'),refresh_requested_date_pkt=request.get('requested_date_pkt'),
    preserve_active_run_ids=request.get('preserve_active_run_ids',[]))
 return config

def main():
 secret=os.environ.get('CHOTU_DRIVE_RCLONE_CONFIG','')
 if not secret:raise RuntimeError('CHOTU_DRIVE_RCLONE_CONFIG secret not configured; no Drive upload attempted')
 config_text(secret)
 config=load_config();root=config['dispatcher'];folder=config.get('destination_folder') or checked.daily_folder()
 if '/' in folder or '\\' in folder or ':' in folder or folder in ('.','..',''):raise ValueError('Invalid destination folder')
 try:
  state=read_json(gh,'repos/'+REPO+'/contents/latest.json?ref=drive-sync-reports')
 except GitHubOperationError as exc:
  if not exc.not_found:raise
  state={}
 if state.get('dispatcher')!=root:
  if config.get('audit804_enabled'):
   state.update(dispatcher=root,processed_artifacts={},audit804_processed={},audit804_results={},audit804_artifacts={})
  else:state={'dispatcher':root,'processed_artifacts':{},'uploaded':{},'daily_uploads':{}}
 state['folder']=folder;state.setdefault('daily_uploads',{}).setdefault(folder,{})
 state['run_id']=os.environ['GITHUB_RUN_ID'];state['sync_status']='scanning';state['last_scan_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat();globals()['LAST_STATE']=state
 state.pop('sync_error',None);publish(state,branch='drive-sync-reports')
 runs=json.loads(gh('run','list','--repo',REPO,'--workflow','cloud-fetch.yml','--limit','100','--json','databaseId,displayTitle,status,conclusion,headSha'))
 all_runs=list(runs)
 groups={r['displayTitle'].removeprefix('Cloud group ') for r in runs if r['displayTitle'].startswith('Cloud group fresh26-'+root+'-')}
 runs=checked.related(runs,groups)
 if not runs and not config.get('audit804_enabled') and not config.get('original_sources') and not (ROOT/'catalog-inputs/khaadi-mobile/latest.json').exists():raise RuntimeError('No matching authorized fresh-batch runs found')
 with tempfile.TemporaryDirectory() as tmp:
  cfg=Path(tmp)/'rclone.conf';cfg.write_text(secret,encoding='utf-8');cfg.chmod(0o600)
  def rc(*args):
   return drive_command(cfg,*args)
  if config.get('audit804_enabled'):
   from audit804_delivery import run_campaign
   held_stores=[s.strip() for s in os.environ.get('CHOTU_REPAIR_HELD_STORES','').split(',') if s.strip()] or None
   run_campaign(state,config,all_runs,gh,rc,progress=lambda current:publish(current,branch='drive-sync-reports'),held_stores=held_stores)
   publish(state,branch='drive-sync-reports');print('804 Audit campaign scan complete; only passed shop-code-identified workbooks delivered.');return
  from mobile_khaadi_ingest import upload as upload_mobile
  if upload_mobile(state,folder,rc):
   state['verified_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat();publish(state,branch='drive-sync-reports')
   print('VERIFIED: mobile Khaadi processed with Rule 804 and checksum-checked in',folder,flush=True)
  from original_store_ingest import upload as upload_originals
  original_sent=upload_originals(state,folder,rc,all_runs,gh,config.get('original_sources',[]))
  if original_sent:state['verified_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
  if original_sent or state.get('original_holds'):
   publish(state,branch='drive-sync-reports');print('Original store Rule 804 Drive verified:',', '.join(original_sent) or 'none; see holds',flush=True)
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
