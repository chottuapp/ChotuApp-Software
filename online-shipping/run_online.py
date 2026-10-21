"""Run the audit and publish bounded live snapshots to its own GitHub branch."""
import json,os,subprocess,sys,time
from datetime import datetime,timezone
from pathlib import Path
FILES=('activity.log','progress.json','summary.json','errors.json','evidence.json','Products_Delivery_Audit.csv','Products_Delivery_Audit.xlsx','run-summary.md')

def git(*args):return subprocess.run(['git',*args],check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)

def snapshot(folder,final=False):
 names=[str(folder/name) for name in FILES if (folder/name).is_file() and (final or name in ('activity.log','progress.json'))]
 if not names:return
 git('add','--sparse',*names)
 if subprocess.run(['git','diff','--cached','--quiet']).returncode==0:return
 git('commit','-m','Shipping audit '+('final results' if final else 'live progress'))
 git('push','origin','HEAD')

def main():
 root=Path('shipping-output');root.mkdir(exist_ok=True)
 branch='shipping-results-'+os.environ['GITHUB_RUN_ID']+'-'+os.environ.get('GITHUB_RUN_ATTEMPT','1')
 git('config','user.name','github-actions');git('config','user.email','github-actions@github.com');git('switch','-c',branch)
 progress={'updated_at_utc':datetime.now(timezone.utc).isoformat(),'products':0,'errors':0,'message':'Runner started. Checking website access.'}
 (root/'progress.json').write_text(json.dumps(progress),encoding='utf-8');snapshot(root)
 command=[sys.executable,'-u','online-shipping/audit.py','--links',os.environ['AUDIT_LINKS'],'--cities',os.environ['AUDIT_CITIES'],'--max-pages',os.environ['AUDIT_PAGES']]
 proc=subprocess.Popen(command)
 try:
  while proc.poll() is None:
   time.sleep(5)
   if time.monotonic()-main.last>=30:
    try:snapshot(root)
    except subprocess.CalledProcessError:print('Live snapshot publish failed; fetch continues. Final upload will retry.',flush=True)
    main.last=time.monotonic()
  code=proc.wait()
  if code and not (root/'summary.json').exists():
   progress.update(updated_at_utc=datetime.now(timezone.utc).isoformat(),message='Audit failed before final export. Open runner for details.',errors=1)
   (root/'progress.json').write_text(json.dumps(progress),encoding='utf-8')
  published=False
  for attempt in range(3):
   try:
    snapshot(root,final=True)
    # A previous push may have failed after the commit; always retry the branch push.
    git('push','origin','HEAD');published=True;break
   except subprocess.CalledProcessError:
    print('Final result publish retry '+str(attempt+1),flush=True);time.sleep(5)
  if not published:raise RuntimeError('Results remain in runner Artifacts; branch publish failed')
  return code
 finally:
  if proc.poll() is None:proc.terminate();proc.wait(timeout=30)
main.last=0
if __name__=='__main__':raise SystemExit(main())
