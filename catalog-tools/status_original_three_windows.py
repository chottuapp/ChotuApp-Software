"""Read-only report for LAAM, Sapphire and local Khaadi; never dispatch fetching."""
import concurrent.futures,json,os,shutil,subprocess,tempfile,time
from pathlib import Path
REPO='chottuapp/ChotuApp-Software';ROOTS={'LAAM':('39410937297','solo-laam'),'Sapphire':('39414516183','solo-sapphire')}
def main():
    gh=shutil.which('gh') or str(Path(os.environ.get('ProgramFiles','C:/Program Files'))/'GitHub CLI/gh.exe')
    def call(*args):
        r=subprocess.run([gh,*args],capture_output=True,text=True,timeout=120)
        if r.returncode:raise RuntimeError(r.stderr.strip() or 'GitHub request failed')
        return r.stdout
    runs=json.loads(call('run','list','--repo',REPO,'--workflow','cloud-fetch.yml','--limit','100','--json','databaseId,displayTitle,status,conclusion'))
    def report(name,root,lane):
        ids={root};ids.update(str(r['databaseId']) for r in runs if r.get('displayTitle')=='Cloud group '+lane)
        for _ in runs:
            more={str(r['databaseId']) for r in runs if r.get('displayTitle','').startswith('Automatic continuation of ') and r['displayTitle'].split()[-1] in ids}
            if more<=ids:break
            ids.update(more)
        chain=[r for r in runs if str(r['databaseId']) in ids]
        if not chain:return name+': no matching recent cloud run; current progress unconfirmed'
        run=chain[0];rid=str(run['databaseId']);lines=[name+' | run '+rid+' | '+run['status']+' / '+str(run.get('conclusion') or '')]
        try:
            with tempfile.TemporaryDirectory() as tmp:
                call('run','download',rid,'--repo',REPO,'--name','chotuapp-live-logs','--dir',tmp)
                paths=list(Path(tmp).rglob('store-status.txt'))
                if not paths:lines.append('No published store-status snapshot yet.')
                else:lines.append(paths[0].read_text(encoding='utf-8',errors='replace'))
        except Exception as exc:lines.append('Snapshot unavailable: '+str(exc))
        return '\n'.join(lines)
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        jobs=[pool.submit(report,name,*data) for name,data in ROOTS.items()]
        for job in jobs:
            try:print(job.result(),flush=True)
            except Exception as exc:print('Cloud status unavailable:',str(exc),flush=True)
    base=Path.home()/'Desktop/ANAS_DATA_FETCH/Khaadi_Local';log=base/'fetch-log.txt';status=base/'local-status.json'
    print('\nKHAADI LOCAL',flush=True)
    if status.exists():print(status.read_text(encoding='utf-8',errors='replace'),flush=True)
    if log.exists():
        age=int(max(0,time.time()-log.stat().st_mtime));print('Last log update age:',age,'seconds'+(' — stale; progress not confirmed' if age>600 else ''),flush=True)
        print('\n'.join(log.read_text(encoding='utf-8',errors='replace').splitlines()[-15:]),flush=True)
    else:print('Local log not found.',flush=True)
    ps=['powershell','-NoProfile','-Command',"Get-CimInstance Win32_Process | Where-Object {$_.Name -match '^python' -and $_.CommandLine -like '*khaadi*' -and $_.CommandLine -notlike '*status_original_three*'} | Select-Object ProcessId,CreationDate | Format-Table -AutoSize"]
    result=subprocess.run(ps,capture_output=True,text=True,timeout=30)
    print('Khaadi process check:',result.stdout.strip() or ('No matching Python process found.' if result.returncode==0 else result.stderr.strip()),flush=True)
if __name__=='__main__':main()
