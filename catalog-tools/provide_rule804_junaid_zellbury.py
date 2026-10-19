"""Provide two completed source catalogs for reviewed Rule 804 processing."""
import base64,hashlib,json,os,shutil,subprocess,tempfile,zipfile
from pathlib import Path
REPO='chottuapp/ChotuApp-Software'
SOURCES={'Junaid Jamshed.xlsx':'39280218526','Zellbury.xlsx':'39302500744'}
def main():
 gh=shutil.which('gh') or str(Path(os.environ.get('ProgramFiles','C:/Program Files'))/'GitHub CLI'/'gh.exe')
 def call(*args):
  r=subprocess.run([gh,*args],capture_output=True,text=True,timeout=600)
  if r.returncode:raise RuntimeError(r.stderr or r.stdout)
  return r.stdout
 with tempfile.TemporaryDirectory(prefix='rule804-two-') as tmp:
  root=Path(tmp);files=[];manifest=[]
  for name,run in SOURCES.items():
   target=root/run;target.mkdir()
   call('run','download',run,'--repo',REPO,'--name','chotuapp-excel-files','--dir',str(target))
   matches=list(target.rglob(name))
   if len(matches)!=1:raise RuntimeError('Expected exactly one '+name+'; nothing uploaded')
   f=matches[0]
   with zipfile.ZipFile(f) as book:
    if book.testzip() is not None:raise RuntimeError('Workbook archive is corrupt: '+name)
   files.append(f);manifest.append({'name':name,'source_run':run,'sha256':hashlib.sha256(f.read_bytes()).hexdigest()})
   print('Downloaded:',name,'from',run,flush=True)
  archive=root/'Input.zip'
  with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
   for f in files:z.write(f,f.name)
   z.writestr('transfer-manifest.json',json.dumps(manifest,indent=2))
  backup=Path.home()/'Desktop'/'Rule804_Junaid_Zellbury_Input.zip';shutil.copy2(archive,backup);print('Backup:',backup,flush=True)
  if archive.stat().st_size>60*1024**2:raise RuntimeError('Attach the backup ZIP in chat; too large for transfer')
  endpoint='repos/'+REPO+'/contents/catalog-inputs/rule804-20261020-junaid-zellbury/Input.zip'
  existing=subprocess.run([gh,'api',endpoint],capture_output=True,text=True,timeout=180)
  payload={'message':'Provide completed Junaid and Zellbury catalogs for Rule 804 review','branch':'main','content':base64.b64encode(archive.read_bytes()).decode('ascii')}
  if existing.returncode==0:payload['sha']=json.loads(existing.stdout)['sha']
  elif '404' not in existing.stderr:raise RuntimeError(existing.stderr)
  request=root/'request.json';request.write_text(json.dumps(payload),encoding='utf-8')
  print(call('api',endpoint,'--method','PUT','--input',str(request),'--jq','.content.path'),flush=True)
  print('UPLOAD SUCCESS: 2 source workbooks supplied. Rule 804 review and Drive upload still pending.')
if __name__=='__main__':main()
