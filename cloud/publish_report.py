"""Publish only a credential-free diagnostic JSON to an independent Git branch."""
import json,os,re,subprocess,tempfile
from pathlib import Path
TOP={'schema_version','generated_utc','run_id','attempt','source_commit','status','checkpoint_saved','python','elapsed_seconds','stores'}
STORE={'name','status','review_required','issue_codes','software_revision','products','variants','http_statuses','network_seconds','max_response_seconds','cache_events'}


def validate_report(data):
    if not isinstance(data,dict) or set(data)-TOP or data.get('schema_version')!=1:raise ValueError('Unexpected report format; nothing published')
    if not re.fullmatch(r'\d{1,30}',str(data.get('run_id',''))) or not re.fullmatch(r'\d{1,6}',str(data.get('attempt',''))):raise ValueError('Invalid run identity')
    if not isinstance(data.get('stores'),list) or len(data['stores'])>30:raise ValueError('Invalid store report')
    for store in data['stores']:
        if not isinstance(store,dict) or set(store)-STORE:raise ValueError('Report contains unapproved fields')
    payload=json.dumps(data,indent=2,ensure_ascii=True).encode()
    if len(payload)>150000:raise ValueError('Report exceeds publication size limit')
    return payload


def publish(path,repo='.'):
    data=json.loads(Path(path).read_text(encoding='utf-8'));payload=validate_report(data)
    with tempfile.TemporaryDirectory(prefix='chotu-report-index-') as folder:
        env=dict(os.environ,GIT_INDEX_FILE=str(Path(folder)/'index'))
        def git(*args,input=None):
            result=subprocess.run(['git',*args],cwd=repo,env=env,input=input,stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True)
            return result.stdout.decode().strip()
        ref='refs/heads/cloud-reports';existing=git('ls-remote','--heads','origin',ref);parent=None
        if existing:
            git('fetch','--depth=1','origin',ref);parent=git('rev-parse','FETCH_HEAD');git('read-tree',parent)
        else:git('read-tree','--empty')
        def put(name,content):
            blob=git('hash-object','-w','--stdin',input=content)
            git('update-index','--add','--cacheinfo','100644,'+blob+','+name)
        put('runs/'+data['run_id']+'-'+data['attempt']+'.json',payload);put('latest.json',payload)
        put('README.md',b'# ChotuApp cloud diagnostics\n\nAutomatic structured reports only; application code remains on main.\nReports include store names, outcomes, product counts, HTTP/timing/cache metrics and source revision. No raw logs, response bodies, credentials, cookies, Excel files or response databases are committed here.\n\nThe assistant does not receive background notifications. Ask it to check this branch when diagnosing a run. Full redacted logs remain in the short-lived diagnostics artifact.\n')
        tree=git('write-tree');args=['-c','user.name=github-actions[bot]','-c','user.email=41898282+github-actions[bot]@users.noreply.github.com','commit-tree',tree]
        if parent:args+=['-p',parent]
        commit=git(*args,input=('Cloud diagnostic '+data['run_id']+' attempt '+data['attempt']+'\n').encode())
        # No force pushes and no working-tree/index replacement; app branch is untouched.
        git('push','origin',commit+':'+ref)
    print('Diagnostic report published on cloud-reports; application source unchanged.')

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('report',type=Path);parser.add_argument('--repo',default='.');args=parser.parse_args();publish(args.report,args.repo)
