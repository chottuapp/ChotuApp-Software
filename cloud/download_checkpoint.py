"""Download a checkpoint transactionally with bounded retries for storage throttling."""
import argparse,os,re,shutil,subprocess,tempfile,time
from pathlib import Path
RETRY=re.compile(r'HTTP\s+(429|502|503|504)|egress is over|error connecting|connection reset|TLS handshake timeout|i/o timeout|timed out',re.I)
def download(run,repo,output,attempts=6,deadline_seconds=900):
    if not str(run).isdigit() or not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+',repo):raise ValueError('Numeric run ID and repository required')
    output=Path(output);output.parent.mkdir(parents=True,exist_ok=True)
    if output.exists() and (not output.is_dir() or any(output.iterdir())):raise ValueError('Restore destination is not empty; existing data preserved')
    deadline=time.monotonic()+deadline_seconds
    for attempt in range(1,attempts+1):
        remaining=deadline-time.monotonic()
        if remaining<=0:break
        with tempfile.TemporaryDirectory(prefix='checkpoint-download-',dir=output.parent) as tmp:
            try:
                result=subprocess.run(['gh','run','download',str(run),'--repo',repo,'--name','chotuapp-checkpoint','--dir',tmp],capture_output=True,text=True,timeout=min(600,remaining))
                retry=bool(RETRY.search(result.stderr+'\n'+result.stdout))
            except subprocess.TimeoutExpired:
                result=None;retry=True
            if result is not None and result.returncode==0:
                if not any(p.is_file() for p in Path(tmp).rglob('*')):raise RuntimeError('Checkpoint artifact was empty; nothing restored')
                shutil.copytree(tmp,output,dirs_exist_ok=True);print('Checkpoint downloaded; archive verification will run before fetching.',flush=True);return
        if not retry:raise RuntimeError('Checkpoint download failed without a retryable storage response; no fetching started. Check artifact availability and account access.')
        delay=min(30*2**(attempt-1),300,max(0,deadline-time.monotonic()))
        if attempt==attempts or delay<=0:break
        print('CHECKPOINT STORAGE COOLDOWN: temporary network/storage throttle; attempt '+str(attempt)+'/'+str(attempts)+'; retry in '+str(int(delay))+'s. Saved parent unchanged.',flush=True)
        end=time.monotonic()+delay
        while time.monotonic()<end:time.sleep(min(15,end-time.monotonic()))
    raise RuntimeError('Checkpoint storage remained unavailable within the retry budget. Parent checkpoint retained; no fresh fallback or partial restore performed.')
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--run',required=True);parser.add_argument('--repo',required=True);parser.add_argument('--output',required=True,type=Path);args=parser.parse_args();download(args.run,args.repo,args.output)
if __name__=='__main__':main()
