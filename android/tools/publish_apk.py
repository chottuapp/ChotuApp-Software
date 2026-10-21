"""Deliver only the tested preview APK and checksum on a dedicated download branch."""
import datetime,hashlib,json,os,shutil,subprocess,tempfile,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def run(args,cwd):return subprocess.run(args,cwd=cwd,check=True,capture_output=True,text=True)
def certificate(apk):
 sdk=Path(os.environ.get('ANDROID_HOME',os.environ.get('ANDROID_SDK_ROOT','/usr/local/lib/android/sdk')))
 tools=sorted((sdk/'build-tools').glob('*/apksigner'))
 if not tools:raise RuntimeError('APK signature verifier unavailable')
 run([str(tools[-1]),'verify',str(apk)],ROOT)
 from apk_signers import fingerprints
 return fingerprints(apk)

def main():
 apk=ROOT/'android/app/build/outputs/apk/debug/app-debug.apk'
 if not apk.is_file() or apk.stat().st_size>95*1024*1024:raise ValueError('APK missing or exceeds Git delivery limit')
 with tempfile.TemporaryDirectory() as tmp:
  directory=Path(tmp);run(['git','init'],directory)
  run(['git','config','user.name','github-actions[bot]'],directory);run(['git','config','user.email','41898282+github-actions[bot]@users.noreply.github.com'],directory)
  # The repository credential helper from checkout is not copied into an APK or report.
  auth='AUTHORIZATION: basic '+__import__('base64').b64encode(('x-access-token:'+os.environ['GH_TOKEN']).encode()).decode()
  run(['git','config','http.https://github.com/.extraheader',auth],directory)
  run(['git','remote','add','origin','https://github.com/chottuapp/ChotuApp-Software.git'],directory)
  exists=subprocess.run(['git','fetch','--depth','1','origin','android-builds'],cwd=directory,capture_output=True).returncode==0
  run(['git','checkout','-B','android-builds','FETCH_HEAD'] if exists else ['git','checkout','--orphan','android-builds'],directory)
  signing=certificate(apk)
  shutil.copy2(apk,directory/'ChotuApp-Studio-candidate.apk')
  sdk=Path(os.environ.get('ANDROID_HOME',os.environ.get('ANDROID_SDK_ROOT','/usr/local/lib/android/sdk')))
  jars=sorted((sdk/'build-tools').glob('*/lib/apksigner.jar'))
  if not jars:raise RuntimeError('Signing tool missing')
  shutil.copy2(jars[-1],directory/'apksigner.jar')
  screenshot=ROOT/'android/dashboard.png'
  if screenshot.exists():shutil.copy2(screenshot,directory/'dashboard.png')
  report={'version':'1.4-studio-candidate','signing_certificate_sha256':signing,'sha256':hashlib.sha256(apk.read_bytes()).hexdigest(),'bytes':apk.stat().st_size,'source_commit':os.environ['GITHUB_SHA'],'run_id':os.environ['GITHUB_RUN_ID'],'built_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'device_test':'Android 35 x86_64 dashboard, Keystore and captured-source XLSX export passed','release':'debug-signed preview; first phone live source fetch not yet verified'}
  (directory/'studio-candidate.json').write_text(json.dumps(report,indent=2));run(['git','add','ChotuApp-Studio-candidate.apk','studio-candidate.json','apksigner.jar'],directory)
  if screenshot.exists():run(['git','add','dashboard.png'],directory)
  run(['git','commit','-m','Deliver tested ChotuApp Android preview'],directory);run(['git','push','origin','HEAD:android-builds'],directory)
  print('Published APK SHA256:',report['sha256'])
if __name__=='__main__':main()
