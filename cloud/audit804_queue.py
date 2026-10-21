"""Durable catalog-only held inputs on a separate Git branch; never runtime caches or credentials."""
import hashlib,json,os,re,subprocess,tempfile
from pathlib import Path
BRANCH='audit804-held-inputs';CHUNK=40*1024*1024

def slug(value):return re.sub('[^a-z0-9]+','-',value.lower()).strip('-')
def save(source,store,campaign,source_run):
 source=Path(source);sha=hashlib.sha256(source.read_bytes()).hexdigest()
 if source.suffix.lower()!='.xlsx' or source.stat().st_size>512*1024*1024:raise ValueError('Held input exceeds catalog queue bounds')
 prefix='inputs/'+campaign+'/'+slug(store)+'/'+sha[:16]
 with tempfile.TemporaryDirectory() as tmp:
  env=dict(os.environ,GIT_INDEX_FILE=str(Path(tmp)/'index'))
  def git(*args,input=None):return subprocess.run(['git',*args],input=input,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True).stdout.decode().strip()
  parent=None
  if git('ls-remote','--heads','origin','refs/heads/'+BRANCH):
   git('fetch','--depth=1','origin',BRANCH);parent=git('rev-parse','FETCH_HEAD');git('read-tree',parent)
  else:git('read-tree','--empty')
  parts=[]
  with source.open('rb') as stream:
   while True:
    data=stream.read(CHUNK)
    if not data:break
    name=prefix+'/source.xlsx.part-'+str(len(parts)).zfill(3);blob=git('hash-object','-w','--stdin',input=data)
    git('update-index','--add','--cacheinfo','100644,'+blob+','+name);parts.append({'path':name,'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data)})
  record={'store':store,'campaign_id':campaign,'source_run':source_run,'sha256':sha,'parts':parts}
  marker=prefix+'/manifest.json';blob=git('hash-object','-w','--stdin',input=json.dumps(record).encode());git('update-index','--add','--cacheinfo','100644,'+blob+','+marker)
  args=['-c','user.name=github-actions[bot]','-c','user.email=41898282+github-actions[bot]@users.noreply.github.com','commit-tree',git('write-tree')]
  if parent:args+=['-p',parent]
  commit=git(*args,input=b'Save catalog-only 804 Audit held input\n');git('push','origin',commit+':refs/heads/'+BRANCH)
  return marker

def restore(marker,out,store,campaign):
 prefix='inputs/'+campaign+'/'+slug(store)+'/'
 if not marker.startswith(prefix) or not re.fullmatch(r'[a-zA-Z0-9_./-]+',marker) or '..' in marker:raise ValueError('Invalid held-input identity')
 subprocess.run(['git','fetch','--depth=1','origin',BRANCH],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
 def blob(path):return subprocess.check_output(['git','show','FETCH_HEAD:'+path])
 record=json.loads(blob(marker))
 if record.get('store')!=store or record.get('campaign_id')!=campaign or not 1<=len(record.get('parts',[]))<=13:raise ValueError('Held queue identity mismatch')
 digest=hashlib.sha256();out=Path(out)
 with out.open('wb') as stream:
  for part in record['parts']:
   if not part['path'].startswith(marker.rsplit('/',1)[0]+'/source.xlsx.part-'):raise ValueError('Unexpected held input part')
   data=blob(part['path'])
   if len(data)!=part['bytes'] or hashlib.sha256(data).hexdigest()!=part['sha256']:raise ValueError('Held input part changed')
   stream.write(data);digest.update(data)
 if digest.hexdigest()!=record['sha256']:raise ValueError('Held workbook changed')
 return out
