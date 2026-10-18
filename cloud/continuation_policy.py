"""Bounded continuation policy: checkpoints, useful progress, and no manual-stop loops."""
import hashlib,json,os,sqlite3
from pathlib import Path
MAX_CONTINUATIONS=6

def integer(value,default=0,maximum=MAX_CONTINUATIONS):
    try:
        result=int(value)
        if str(result)!=str(value).strip() or not 0<=result<=maximum:raise ValueError
        return result
    except (ValueError,TypeError):return default

def budget(summary):
    limit=integer(summary.get('auto_continue_limit',0))
    if not limit and summary.get('auto_continue_once') is True:limit=1
    return limit,integer(summary.get('continuation_index',0))

def recoverable(site):
    return site.get('status') in ('pending','running','source_paused')

def progress_token(state,root):
    data=[]
    for index,site in enumerate(state.get('sites',[])):
        counts=[]
        if site.get('status')!='done':
            for name in ('api.sqlite3','pages.sqlite3'):
                path=Path(root)/str(state.get('id',''))/str(index)/name
                if not path.is_file():counts.append(0);continue
                try:
                    with sqlite3.connect(path.resolve().as_uri()+'?mode=ro',uri=True) as db:counts.append(db.execute('SELECT COUNT(*) FROM responses').fetchone()[0])
                except sqlite3.Error:counts.append(0)
        data.append([index,site.get('status')=='done',(site.get('output') or {}).get('size',0) if site.get('status')=='done' else 0,counts])
    return hashlib.sha256(json.dumps(data,separators=(',',':')).encode()).hexdigest()

def summary_fields(state,root):
    token=progress_token(state,root);previous=os.environ.get('CLOUD_PREVIOUS_PROGRESS','')
    return {'auto_continue_limit':integer(os.environ.get('CLOUD_AUTO_CONTINUE_LIMIT','0')),'continuation_index':integer(os.environ.get('CLOUD_CONTINUATION_INDEX','0')),'progress_token':token,'stalled_runs':min(2,integer(os.environ.get('CLOUD_STALLED_RUNS','0'),maximum=2)+1) if previous==token else 0}
