"""Send only the authorized Drive remote to an encrypted Actions secret; never print it."""
import configparser,os,shutil,subprocess,sys
from pathlib import Path
REPO='chottuapp/ChotuApp-Software'
def main():
 gh=shutil.which('gh') or str(Path(os.environ['ProgramFiles'])/'GitHub CLI/gh.exe');rc=shutil.which('rclone')
 if not rc:
  choices=list((Path(os.environ['LOCALAPPDATA'])/'Microsoft/WinGet/Packages').glob('Rclone.Rclone_*/rclone-*-windows-amd64/rclone.exe'))
  if not choices:raise RuntimeError('Rclone not found')
  rc=str(sorted(choices)[-1])
 r=subprocess.run([rc,'config','show','chotudrive'],capture_output=True,text=True,timeout=60)
 if r.returncode:raise RuntimeError('Drive remote could not be read; credentials were not uploaded')
 text=r.stdout;cfg=configparser.ConfigParser(interpolation=None);cfg.read_string(text)
 if cfg.sections()!=['chotudrive'] or cfg['chotudrive'].get('type')!='drive' or not cfg['chotudrive'].get('token'):raise RuntimeError('Expected only the chotudrive Google Drive remote')
 print('Saving only chotudrive credentials as encrypted GitHub Actions secret. Credentials are not printed or committed.',flush=True)
 r=subprocess.run([gh,'secret','set','CHOTU_DRIVE_RCLONE_CONFIG','--repo',REPO],input=text,capture_output=True,text=True,timeout=180)
 if r.returncode:raise RuntimeError('Encrypted secret setup failed; check GitHub account repository permissions')
 subprocess.run([gh,'workflow','run','cloud-drive-sync.yml','--repo',REPO,'--ref','main'],check=True,timeout=120)
 print('CLOUD DRIVE SYNC ENABLED. You may close the local Drive uploader after the first cloud upload succeeds. Local Khaadi still requires this PC.',flush=True)
if __name__=='__main__':main()
