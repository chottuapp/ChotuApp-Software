"""Embedded Android worker. No Termux, subprocess, desktop UI or shell required."""
import base64,hashlib,importlib.util,json,sys,time
from pathlib import Path
import requests
REPO='chottuapp/ChotuApp-Software'
class Paused(KeyboardInterrupt):pass

def load(name,path):
 spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec);sys.modules[name]=module;spec.loader.exec_module(module);return module

def run(root,data,token,bridge=None):
 if bridge is None:
  from java import jclass
  bridge=jclass("com.chotuapp.mobile.FetchService")
 root=Path(root);data=Path(data);sys.path.insert(0,str(root))
 def check():
  if bridge.isPaused():raise Paused()
 class PublicSession:
  def __init__(self):self.session=requests.Session();self.session.headers['User-Agent']='Mozilla/5.0 ChotuApp-PublicCatalog/1.0'
  def get(self,url,**kwargs):
   check();response=self.session.get(url,timeout=(15,45));check();return response
 state=data/'local-status.json'
 try:previous=json.loads(state.read_text())
 except (OSError,ValueError):previous={}
 if previous.get('status')!='exported_review_required':
  worker=load('android_approved_worker',root/'approved_worker.py')
  code=worker.fetch(root,data,PublicSession())
  if code:return json.dumps({'status':'paused' if code==130 else 'attention','message':'Saved work retained. See activity for the source error.'})
 check()
 if not token:return json.dumps({'status':'ready_to_upload','message':'Excel saved on this phone. Connect GitHub to queue Rule 804 and Drive upload.'})
 sha=upload(data,token,check)
 return json.dumps({'status':'cloud_queued','source_sha256':sha,'message':'Workbook queued for Rule 804 and Drive verification. Drive completion is shown separately.'})

def upload(data,token,check=lambda:None):
 state=json.loads((data/'local-status.json').read_text());files=[Path(p) for p in state.get('files',[])]
 if state.get('status')!='exported_review_required' or not files:raise ValueError('No completed workbook')
 file=max(files,key=lambda p:p.stat().st_mtime)
 if not file.resolve().is_relative_to((data/'files').resolve()) or file.suffix!='.xlsx':raise ValueError('Unexpected output path')
 content=file.read_bytes()
 if len(content)>32*1024*1024:raise ValueError('File exceeds safe repository upload limit; retained on phone')
 sha=hashlib.sha256(content).hexdigest();path='catalog-inputs/khaadi-mobile/'+sha[:16]+'/Khaadi.xlsx'
 session=requests.Session();session.headers.update(Authorization='Bearer '+token,Accept='application/vnd.github+json')
 def put(path,body):
  check();url='https://api.github.com/repos/'+REPO+'/contents/'+path
  response=session.get(url,params={'ref':'main'},timeout=45)
  if response.status_code not in (200,404):raise RuntimeError('GitHub access unavailable ('+str(response.status_code)+'). File retained on phone.')
  old=response.json() if response.status_code==200 else {}
  blob=hashlib.sha1(b'blob '+str(len(body)).encode()+b'\0'+body).hexdigest()
  if old.get('sha')==blob:return
  payload={'message':'Supply mobile Khaadi workbook for checked Rule 804 delivery','branch':'main','content':base64.b64encode(body).decode()}
  if old.get('sha'):payload['sha']=old['sha']
  check();response=session.put(url,json=payload,timeout=180)
  if response.status_code not in (200,201):raise RuntimeError('GitHub upload failed ('+str(response.status_code)+'). File retained on phone.')
 put(path,content)
 marker=json.dumps({'store':'Khaadi','input_path':path,'sha256':sha,'coverage':'Public default-page discovery; full catalog coverage unverified'},indent=2).encode()
 put('catalog-inputs/khaadi-mobile/latest.json',marker)
 return sha

def dashboard():
 result={}
 for key,branch in (('runners','runner-status-reports'),('drive','drive-sync-reports')):
  try:
   response=requests.get('https://raw.githubusercontent.com/'+REPO+'/'+branch+'/latest.json',params={'check':time.time_ns()},timeout=25);response.raise_for_status();result[key]=response.json()
  except requests.RequestException:result[key]={'unavailable':True}
 return json.dumps(result)

def verify_token(token):
 response=requests.get('https://api.github.com/repos/'+REPO,headers={'Authorization':'Bearer '+token,'Accept':'application/vnd.github+json'},timeout=30)
 if response.status_code!=200:raise ValueError('GitHub connection failed. Check token access to ChotuApp-Software.')
 if not response.json().get('permissions',{}).get('push'):raise ValueError('This GitHub account needs write access to ChotuApp-Software.')
 return 'Connected'

def self_test(root,data):
 """On-device fixture export: embedded Python, SQLite, XLSX and headless source."""
 root=Path(root);sys.path.insert(0,str(root))
 import khaadi_source_support as source
 from bs4 import BeautifulSoup
 from openpyxl import load_workbook
 fixture=root/'test-fixtures';soup=BeautifulSoup((fixture/'master.html').read_text(),'html.parser')
 for node in soup.select('.set-item')[0].select('[data-attr="size"] input'):
  if node['data-attr-value']=='00S':node.parent.decompose()
 from types import SimpleNamespace
 product=source.normalize_product(str(soup),source.BASE+'/black-cambric-kurta/1-26-320-A-C1-VG_MULTI.html',lambda url:SimpleNamespace(text=(fixture/('xs.html' if '=0XS' in url else 'l.html')).read_text()))
 original=source.PublicCatalog.catalog
 try:
  source.PublicCatalog.catalog=lambda reader:([product],False)
  helper=load('android_fixture_worker',root/'approved_worker.py')
  if helper.fetch(root,Path(data),object())!=0:raise ValueError('On-device fixture export failed')
 finally:source.PublicCatalog.catalog=original
 state=json.loads((Path(data)/'local-status.json').read_text());book=load_workbook(state['files'][0])
 try:
  if [c.value for c in next(book['Products'].iter_rows())][:3]!=['shop_code','product_id','Category']:raise ValueError('Template schema changed')
  if book['Variant Combinations'].max_row!=3:raise ValueError('Selected fixture variants missing')
 finally:book.close()
 return 'Embedded export verified'
