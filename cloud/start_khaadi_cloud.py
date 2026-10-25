"""Start the owner-requested fresh Khaadi lane only after live Pakistan size verification."""
import json,subprocess,re
from pathlib import Path
REPO='chottuapp/ChotuApp-Software'
def gh(*args):return subprocess.check_output(['gh',*args],text=True,timeout=180)
def main():
 release=json.loads(Path('cloud/audit804-release.json').read_text())
 if release.get('khaadi_fresh_enabled') is False or 'Khaadi' in release.get('excluded_stores',[]):print('Khaadi excluded by owner request; no fetching dispatched');return
 report=json.loads(Path('source-diagnostics/khaadi-public-route.json').read_text())
 if report.get('sample_verified') is not True:raise ValueError('Khaadi Pakistan public size source not verified; cloud fetch withheld')
 release=json.loads(Path('cloud/audit804-release.json').read_text());campaign=release['campaign_id']
 if not re.fullmatch(r'fresh804-[0-9]{8}-[a-f0-9]{8}',campaign):raise ValueError('Approved campaign required')
 group='audit804-'+campaign+'-khaadi-cloud'
 runs=json.loads(gh('run','list','--repo',REPO,'--workflow','cloud-fetch.yml','--limit','100','--json','databaseId,displayTitle,status'))
 if any(r['displayTitle']=='Cloud group '+group for r in runs):print('Khaadi cloud lane already submitted; no duplicate or zero reset');return
 print(gh('workflow','run','cloud-fetch.yml','--repo',REPO,'--ref','main','-f','stores=Khaadi | https://pk.khaadi.com','-f','runner_group='+group,'-f','minutes=90','-f','save_checkpoint=true','-f','auto_continue_limit=48','-f','auto_continue_once=false'))
if __name__=='__main__':main()
