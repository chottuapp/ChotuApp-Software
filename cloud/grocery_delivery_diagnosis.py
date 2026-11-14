"""Read completed grocery coverage receipts without refetching products."""
import csv,json,os,tempfile
from pathlib import Path
from drive_sync import gh,REPO
from source_research import publish

def main():
 rid=os.environ['GROCERY_COMPLETED_RUN']
 if not rid.isdigit():raise ValueError('Exact completed grocery run required')
 run=json.loads(gh('api','repos/'+REPO+'/actions/runs/'+rid))
 if run.get('status')!='completed' or run.get('head_branch')!='main' or run.get('path') not in ('.github/workflows/cloud-fetch.yml','.github/workflows/cloud-grocery-complete.yml') or run.get('head_repository',{}).get('full_name')!=REPO:raise ValueError('Untrusted grocery source')
 report=dict(run_id=os.environ['GITHUB_RUN_ID'],source_run=rid,coverage=[])
 with tempfile.TemporaryDirectory() as tmp:
  gh('run','download',rid,'--repo',REPO,'--name','chotuapp-excel-files','--dir',tmp)
  root=Path(tmp)
  audits=list(root.rglob('grocery-final-audit.json'))
  if len(audits)==1:report['final_audit']=json.loads(audits[0].read_text())
  proofs=list(root.rglob('grocery-completion-proof.json'))
  if len(proofs)==1:report['completion_proof']=json.loads(proofs[0].read_text())
  report['files']=[str(p.relative_to(root)) for p in root.rglob('*') if p.is_file()][:250]
  for p in root.rglob('*SCOPE COVERAGE.csv'):
   with p.open(encoding='utf-8-sig',newline='') as f:report['coverage'].extend(csv.DictReader(f))
 publish(report,branch='chotu-groceries-reports')
 print('Saved grocery coverage receipts inspected; products not refetched')
if __name__=='__main__':main()
