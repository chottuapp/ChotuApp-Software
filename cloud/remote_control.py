"""Observe an explicitly dispatched stop workflow without exposing credentials."""
import json,os,subprocess,time
from pathlib import Path


def check_stop_request(data):
    run=os.environ.get('GITHUB_RUN_ID','');repo=os.environ.get('GITHUB_REPOSITORY','')
    if not run.isdigit() or not repo or not os.environ.get('GH_TOKEN'):return False
    data=Path(data);marker=data/'stop-request'
    if marker.exists():return True
    try:
        result=subprocess.run(['gh','run','list','--repo',repo,'--workflow','cloud-stop.yml','--limit','30','--json','displayTitle,status,conclusion'],capture_output=True,text=True,timeout=12,check=True)
        requested=any(item.get('displayTitle')=='Save and stop '+run and item.get('conclusion')=='success' for item in json.loads(result.stdout))
    except (OSError,ValueError,subprocess.SubprocessError):return False
    if requested:
        marker.touch();print('SAVE AND STOP requested: extractor will close and upload its checkpoint. Wait for artifact upload before resuming.',flush=True)
    return requested
