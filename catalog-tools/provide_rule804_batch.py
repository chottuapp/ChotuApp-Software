"""Transfer exported catalog workbooks from an Actions artifact for Rule 804 review."""
import argparse,base64,hashlib,json,os,shutil,subprocess,tempfile,zipfile
from pathlib import Path
REPO='chottuapp/ChotuApp-Software'
def main():
 p=argparse.ArgumentParser();p.add_argument('--run',required=True);a=p.parse_args()
 if not a.run.isdigit():p.error('Run ID must contain digits only')
 gh=shutil.which('gh') or str(Path(os.environ.get('ProgramFiles','C:/Program Files'))/'GitHub CLI'/'gh.exe')
 def call(*args,check=True):return subprocess.run([gh,*args],capture_output=True,text=True,check=check,timeout=600)
 with tempfile.TemporaryDirectory(prefix='rule804-transfer-') as tmp:
  root=Path(tmp);source=root/'exports';source.mkdir()
  result=call('run','download',a.run,'--repo',REPO,'--name','chotuapp-excel-files','--dir',str(source),check=False)
  if result.returncode:raise SystemExit('Download failed; run may not have a snapshot yet. Retry later.\n'+result.stderr)
  files=sorted(f for f in source.rglob('*.xlsx') if f.is_file() and not f.is_symlink() and not f.name.startswith('~$'))
  if not files:raise SystemExit('No exported Excel workbooks found; nothing uploaded.')
  desktop=Path.home()/'Desktop';out=desktop/('Rule804_Input_'+a.run+'.zip')
  # Atomic replacement of the transfer archive only; original workbooks remain untouched.
  archive=root/'batch.zip'
  with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
   for f in files:z.write(f,f.relative_to(source).as_posix())
   summary=source/'run-summary.json'
   if summary.is_file():z.write(summary,'run-summary.json')
   z.writestr('transfer-manifest.json',json.dumps({'source_run':a.run,'files':[{'name':f.relative_to(source).as_posix(),'sha256':hashlib.sha256(f.read_bytes()).hexdigest()} for f in files]},indent=2))
  shutil.copy2(archive,out)
  print('Downloaded workbooks:',len(files),flush=True);print('Backup ZIP:',out,flush=True)
  if archive.stat().st_size>60*1024**2:raise SystemExit('Archive exceeds upload limit. Attach the Desktop ZIP in chat instead.')
  endpoint='repos/'+REPO+'/contents/catalog-inputs/run'+a.run+'/Rule804_Input.zip'
  existing=call('api',endpoint,check=False);payload={'message':'Provide exported batch '+a.run+' for Rule 804','branch':'main','content':base64.b64encode(archive.read_bytes()).decode('ascii')}
  if existing.returncode==0:payload['sha']=json.loads(existing.stdout)['sha']
  elif '404' not in existing.stderr:raise SystemExit('Cannot inspect destination; upload cancelled.\n'+existing.stderr)
  request=root/'upload.json';request.write_text(json.dumps(payload),encoding='utf-8')
  response=call('api',endpoint,'--method','PUT','--input',str(request),'--jq','.content.path')
  print('Uploaded:',response.stdout.strip(),flush=True)
  print('Files supplied for review; Rule 804 has NOT been applied yet.',flush=True)
if __name__=='__main__':main()
