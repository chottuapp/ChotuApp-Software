"""Collect permitted public Khaadi pages with Windows curl TLS validation."""
import json,subprocess,tempfile,zipfile
from pathlib import Path
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser
BASE='https://pk.khaadi.com'
PATHS={'sitemap_index.xml':'/sitemap_index.xml','product_black_kurta.html':'/black-cambric-kurta/1-26-320-A-C1-VG_MULTI.html','product_purple_kurta.html':'/purple-cambric-kurta/1-26-320-A-F2-VG_MULTI.html'}
def fetch(url,path):
 r=subprocess.run(['curl.exe','--fail','--location','--silent','--show-error','--max-time','60','--max-redirs','5','--output',str(path),'--write-out','%{http_code}\n%{url_effective}',url],capture_output=True,text=True,timeout=75)
 if r.returncode:raise RuntimeError('Public download failed: '+url+'\n'+r.stderr)
 status,final=r.stdout.strip().split('\n',1)
 parsed=urlsplit(final)
 if status!='200' or parsed.scheme!='https' or parsed.hostname!='pk.khaadi.com':raise RuntimeError('Pakistan source not verified: '+status+' '+final)
 if path.stat().st_size>20*1024**2:raise RuntimeError('Unexpectedly large public response')
 return {'requested_url':url,'final_url':final,'http_status':int(status)}
def main():
 with tempfile.TemporaryDirectory(prefix='khaadi-public-') as tmp:
  root=Path(tmp);print('Checking public robots rules...',flush=True)
  records=[fetch(BASE+'/robots.txt',root/'robots.txt')];robot=RobotFileParser();robot.parse((root/'robots.txt').read_text(encoding='utf-8',errors='replace').splitlines())
  for name,path in PATHS.items():
   url=BASE+path
   if not robot.can_fetch('ChotuAppCatalogRefresh',url):raise RuntimeError('Robots disallows this public path; no request made: '+url)
   print('Downloading:',name,flush=True);records.append(fetch(url,root/name))
  (root/'public-source-manifest.json').write_text(json.dumps(records,indent=2),encoding='utf-8')
  out=Path.home()/'Desktop'/'Khaadi_Product_Evidence.zip'
  with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as archive:
   for p in sorted(root.iterdir()):archive.write(p,p.name)
  print('Attach this ZIP:',out,flush=True)
  print('Public pages only; no browser cookies collected. No Excel files or cloud fetching modified.',flush=True)
if __name__=='__main__':main()
