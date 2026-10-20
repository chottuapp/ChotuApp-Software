"""Move the authorized checked batch after destination checksum verification; retain extras."""
import hashlib,json,os,subprocess,tempfile,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from drive_sync import config_text,gh
from source_research import publish
import base64,datetime
REPO='chottuapp/ChotuApp-Software'
SOURCE='ChotuApp 20-10-2026 Fresh';TARGET='ChotuApp 19-10-2026 11-36AM'
def transfer(rc,stage,state):
 approved=state.get('daily_uploads',{}).get(SOURCE,{})
 if not approved:raise RuntimeError('No verified source batch found; no files changed')
 rc('copy','chotudrive:'+SOURCE,str(stage),'--include','*.xlsx','--max-depth','1','--checksum')
 files=sorted(stage.glob('*.xlsx'))
 if not files:
  print('Source folder has no Excel files; no files deleted.');return state
 names=[]
 for file in files:
  store=file.stem;record=approved.get(store)
  if not record or hashlib.sha256(file.read_bytes()).hexdigest()!=record.get('sha256'):raise ValueError('Source file does not match verified Rule 804 report: '+file.name)
  names.append(file.name)
 before=json.loads(rc('lsjson','chotudrive:'+TARGET,'--files-only','--max-depth','1'))
 preserved={x['Name'] for x in before if x['Name'] not in names}
 rc('copy',str(stage),'chotudrive:'+TARGET,'--include','*.xlsx','--checksum')
 rc('check',str(stage),'chotudrive:'+TARGET,'--include','*.xlsx','--one-way')
 after=json.loads(rc('lsjson','chotudrive:'+TARGET,'--files-only','--max-depth','1'))
 if not preserved<={x['Name'] for x in after}:raise RuntimeError('Destination extra-file preservation failed; source not deleted')
 # Do not remove a source file if another uploader changed its bytes during copying.
 rc('check',str(stage),'chotudrive:'+SOURCE,'--include','*.xlsx','--one-way')
 state['run_id']=os.environ['GITHUB_RUN_ID']
 move={'source':SOURCE,'destination':TARGET,'verified_files':names,'destination_file_count':len(after),'preserved_other_files':len(preserved),'verified_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_removed':[]}
 for file in files:
  record=dict(approved[file.stem],folder=TARGET)
  state['uploaded'][file.stem]=record;state.setdefault('daily_uploads',{}).setdefault(TARGET,{})[file.stem]=record
 state.setdefault('moves',[]).append(move)
 publish(state,branch='drive-sync-reports')
 for name in names:
  rc('deletefile','chotudrive:'+SOURCE+'/'+name)
  move['source_removed'].append(name)
 publish(state,branch='drive-sync-reports')
 print('VERIFIED MOVE:',len(names),'Rule 804 workbooks;',len(preserved),'other destination files retained; destination files:',len(after))
 return state

def main():
 secret=config_text(os.environ.get('CHOTU_DRIVE_RCLONE_CONFIG',''))
 raw=json.loads(gh('api','repos/'+REPO+'/contents/latest.json?ref=drive-sync-reports'));state=json.loads(base64.b64decode(raw['content']))
 with tempfile.TemporaryDirectory() as tmp:
  cfg=Path(tmp)/'rclone.conf';cfg.write_text(secret);cfg.chmod(0o600);stage=Path(tmp)/'files';stage.mkdir()
  def rc(*args):
   r=subprocess.run(['rclone','--config',str(cfg),*args],capture_output=True,text=True,timeout=900)
   if r.returncode:raise RuntimeError('Drive '+args[0]+' failed; no unverified source deletion attempted')
   return r.stdout
  transfer(rc,stage,state)
if __name__=='__main__':main()
