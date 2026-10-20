import json,os,sys,datetime
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'cloud'))
from source_research import publish
logs={}
for name in ('build','device'):
 path=ROOT/'android'/str(name+'.log')
 if path.exists():logs[name]='\n'.join(path.read_text(errors='replace').splitlines()[-160:])
publish({'run_id':os.environ['GITHUB_RUN_ID'],'commit':os.environ['GITHUB_SHA'],'phase':os.environ.get('BUILD_PHASE'),'updated_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'logs':logs},branch='android-build-reports')
