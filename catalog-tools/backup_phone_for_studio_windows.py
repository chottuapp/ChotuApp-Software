"""Prepare official Android tools and make a read-only, verified phone backup."""
from pathlib import Path
import hashlib,importlib.util,io,os,sys,urllib.request,zipfile
REVISION='b297689'
def main():
 if os.name!='nt':raise SystemExit('Run this helper on your Windows PC connected to the phone.')
 root=Path.home()/'Desktop'/'ChotuApp_Phone_Migration';root.mkdir(parents=True,exist_ok=True)
 adb=root/'platform-tools'/'adb.exe'
 if not adb.exists():
  print('Downloading official Google Android Platform Tools...',flush=True)
  with urllib.request.urlopen('https://dl.google.com/android/repository/platform-tools-latest-windows.zip',timeout=120) as response:payload=response.read(30*1024*1024+1)
  if len(payload)>30*1024*1024:raise ValueError('Unexpected download size')
  with zipfile.ZipFile(io.BytesIO(payload)) as archive:
   for item in archive.infolist():
    destination=(root/item.filename).resolve()
    if not destination.is_relative_to(root.resolve()) or not item.filename.startswith('platform-tools/'):raise ValueError('Unexpected tool archive path')
   archive.extractall(root)
 helper=root/'backup_android_app_windows.py'
 with urllib.request.urlopen('https://raw.githubusercontent.com/chottuapp/ChotuApp-Software/'+REVISION+'/catalog-tools/backup_android_app_windows.py',timeout=45) as response:payload=response.read()
 expected='df3f1f08bbd9aae7d1925fdf1532224670f9228d363963d0fe5e036debfefd14'
 if hashlib.sha256(payload).hexdigest()!=expected:raise ValueError('Backup helper verification failed')
 helper.write_bytes(payload)
 sys.argv=[str(helper),'--adb',str(adb)]
 spec=importlib.util.spec_from_file_location('phone_backup',helper);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);module.main()
if __name__=='__main__':main()
