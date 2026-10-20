"""Khaadi Android/Ubuntu worker: verified curl, saved-work recovery and GitHub upload."""
import base64,datetime,hashlib,importlib.util,json,os,subprocess,sys,tempfile,time,urllib.request
from pathlib import Path
REPO='https://raw.githubusercontent.com/chottuapp/ChotuApp-Software/'
DATA=Path(os.environ.get('CHOTU_MOBILE_DATA','/chotuapp-data'))
SUPERVISOR_REV='48dca796e41d366fc3c986c30a872cb696dea79f'
SUPERVISOR_SHA='9c5c5e3899374e32f0b0d7d2e4bbfb734ba8722be106ce9de268fc2059aeb2d7'
def load(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def download(url,limit=2*1024*1024):
 request=urllib.request.Request(url,headers={'Cache-Control':'no-cache'})
 with urllib.request.urlopen(request,timeout=60) as response:payload=response.read(limit+1)
 if len(payload)>limit:raise RuntimeError('Download exceeds expected size')
 return payload

class CurlSession:
 def get(self,url,**kwargs):
  from types import SimpleNamespace
  with tempfile.TemporaryDirectory() as tmp:
   body=Path(tmp)/'page'
   result=subprocess.run(['curl','--silent','--show-error','--location','--max-time','45','--user-agent','Mozilla/5.0','--output',str(body),'--write-out','%{http_code}\n%{url_effective}',url],capture_output=True,text=True,timeout=60)
   if result.returncode:raise RuntimeError('SOURCE PAUSED: mobile curl transport exit '+str(result.returncode))
   code,final=result.stdout.strip().split('\n')[-2:];content=body.read_bytes()
   if len(content)>20*1024*1024:raise ValueError('Public response too large')
   return SimpleNamespace(status_code=int(code),url=final,content=content,text=content.decode('utf-8',errors='replace'),encoding='utf-8',headers={'Content-Type':'text/html; charset=utf-8'})

def worker_once(path):
 helper=load('approved_khaadi_worker',path);root=DATA/'software';root.mkdir(parents=True,exist_ok=True)
 for name,expected in helper.FILES.items():
  target=root/name
  if target.is_file() and hashlib.sha256(target.read_bytes()).hexdigest()==expected:continue
  payload=download(REPO+helper.REVISION+'/'+name)
  if hashlib.sha256(payload).hexdigest()!=expected:raise ValueError('Source checksum mismatch: '+name)
  target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(payload)
 return helper.fetch(root,DATA,CurlSession())

def api(endpoint,method=None,payload=None,check=True):
 args=['gh','api','repos/chottuapp/ChotuApp-Software/'+endpoint]
 if method:args+=['--method',method]
 if payload is not None:args+=['--input','-']
 result=subprocess.run(args,input=json.dumps(payload) if payload is not None else None,capture_output=True,text=True,timeout=600)
 if result.returncode:
  if not check:return None
  raise RuntimeError('GitHub upload unavailable; completed workbook retained on phone')
 return json.loads(result.stdout) if result.stdout.strip() else {}

def upload_completed():
 state=json.loads((DATA/'local-status.json').read_text());files=[Path(p) for p in state.get('files',[])]
 if state.get('status')!='exported_review_required' or not files:raise ValueError('No completed reviewed-source workbook')
 file=max(files,key=lambda p:p.stat().st_mtime)
 if not file.resolve().is_relative_to((DATA/'files').resolve()) or file.suffix!='.xlsx':raise ValueError('Unexpected output path')
 content=file.read_bytes();sha=hashlib.sha256(content).hexdigest()
 if len(content)>32*1024*1024:raise ValueError('Workbook too large for verified repository upload; kept locally')
 path='catalog-inputs/khaadi-mobile/'+sha[:16]+'/Khaadi.xlsx'
 def put(endpoint,body,message):
  existing=api('contents/'+endpoint,check=False)
  blob=hashlib.sha1(b'blob '+str(len(body)).encode()+b'\0'+body).hexdigest()
  if existing and existing.get('sha')==blob:return
  payload={'message':message,'branch':'main','content':base64.b64encode(body).decode()}
  if existing:payload['sha']=existing['sha']
  api('contents/'+endpoint,'PUT',payload)
 put(path,content,'Supply completed mobile Khaadi workbook for Rule 804')
 marker=json.dumps({'store':'Khaadi','input_path':path,'sha256':sha,'coverage':'Public default-page discovery; full catalog coverage unverified'},indent=2).encode()
 put('catalog-inputs/khaadi-mobile/latest.json',marker,'Queue mobile Khaadi Rule 804 and verified Drive upload')
 print('MOBILE FETCH COMPLETE. Rule 804 and Drive upload queued in cloud. Workbook retained on phone.',flush=True)


def main():
 DATA.mkdir(parents=True,exist_ok=True)
 if len(sys.argv)>2 and sys.argv[1]=='--once':return worker_once(Path(sys.argv[2]))
 supervisor_path=DATA/'mobile-reporting.py';payload=download(REPO+SUPERVISOR_REV+'/catalog-tools/watch_khaadi_recovery_windows.py')
 if hashlib.sha256(payload).hexdigest()!=SUPERVISOR_SHA:raise ValueError('Reporting helper checksum mismatch')
 supervisor_path.write_bytes(payload)
 reporter=load('mobile_recovery_reporting',supervisor_path);original=reporter.local_report
 reporter.local_report=lambda data:dict(original(data),execution='Android Ubuntu local')
 attempted=None;last_code=None;attempt=0
 with reporter.lease(DATA/'recovery-supervisor.lock'),reporter.local_reporting(DATA):
  while True:
   state=reporter.read_json(DATA/'local-status.json')
   if state.get('status')=='exported_review_required':
    try:upload_completed();return 0
    except (RuntimeError,OSError,ValueError):print('Upload retry in 60 seconds; completed file safe on phone.',flush=True);time.sleep(60);continue
   if reporter.occupied(DATA/'active.lock'):time.sleep(30);continue
   try:
    release=reporter.release_spec(json.loads(download(REPO+'main/cloud/recovery-release.json?check='+str(time.time_ns()))))
    revision=release['commit'];decision='new_release' if attempted is None else reporter.action(last_code,state,revision,attempted)
    if decision=='manual_stop':return 130
    if decision=='wait_for_fix':print('Waiting for a tested published adapter update; no data guessed.',flush=True);time.sleep(60);continue
    if decision=='retry':time.sleep(min(900,60*2**min(attempt,4)))
    worker=DATA/('approved-worker-'+revision+'.py');payload=download(REPO+revision+'/catalog-tools/start_khaadi_local_fetch_windows.py')
    if hashlib.sha256(payload).hexdigest()!=release['sha256']:raise ValueError('Approved worker checksum mismatch')
    worker.write_bytes(payload);attempted=revision;attempt+=1
    print('MOBILE KHAADI: starting saved work; release',revision,flush=True)
    last_code=subprocess.run([sys.executable,str(Path(__file__).resolve()),'--once',str(worker)]).returncode
   except (OSError,RuntimeError,ValueError,subprocess.SubprocessError):print('Setup/network wait; retrying safely in 60 seconds.',flush=True);time.sleep(60)
 return 2
if __name__=='__main__':
 try:sys.exit(main())
 except KeyboardInterrupt:print('Mobile supervision stopped; saved work retained.');sys.exit(130)
