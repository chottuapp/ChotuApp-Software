"""Bounded fetch telemetry and credential-free reports for the cloud workflow."""
import collections,datetime,json,os,platform,re,sqlite3,sys,tempfile,time
from pathlib import Path
from urllib.parse import urlsplit


def redact(line):
    if re.search(r'(?i)\b(authorization|password|secret|access[_-]?token|refresh[_-]?token|gh_token|api[_-]?key|cookie|set-cookie)\s*[:=]',line):return '[credential-bearing log line removed]'
    line=re.sub(r'\bgh[opusr]_[A-Za-z0-9_]+','[token removed]',line)
    def clean(match):
        try:
            url=urlsplit(match[0]);return url.scheme+'://'+(url.hostname or '')+url.path+('?redacted' if url.query else '')
        except ValueError:return '[URL removed]'
    return re.sub(r'https?://[^\s<>"\']+',clean,line)


def issue_codes(text):
    issues=[]
    for code in (403,404,429,503):
        if re.search(r'(?:status=|HTTP\s+|\()'+str(code)+r'\b',text,re.I):issues.append('HTTP_'+str(code))
    for needle,code in [('SOURCE BLOCKED:','SOURCE_BLOCKED'),('SOURCE PAUSED:','RATE_LIMIT'),('TOP 20: UNVERIFIED','RANKING_UNVERIFIED'),('schema','SCHEMA_CHECK'),('CHECKPOINT NOT SAVED','CHECKPOINT_NOT_SAVED')]:
        if needle.lower() in text.lower():issues.append(code)
    if 'mismatch' in text.lower() and (re.search(r'FAILED:|EXCEPTION:|\bERROR\b',text) or re.search(r'\b[1-9][0-9]* (?:review/)?mismatch',text)):issues.append('DATA_MISMATCH')
    return issues


def atomic_json(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True);fd,name=tempfile.mkstemp(prefix='.telemetry-',dir=path.parent)
    try:
        with os.fdopen(fd,'w',encoding='utf-8') as stream:json.dump(value,stream,ensure_ascii=True)
        os.replace(name,path)
    finally:Path(name).unlink(missing_ok=True)


class Collector:
    def __init__(self,path):self.path=Path(path);self.started=time.time();self.updated=0;self.stores={}
    def observe(self,text):
        match=re.match(r'^\[([^\]]{1,100})\]\s',text)
        if not match:return
        name=match[1]
        if name not in self.stores and len(self.stores)>=30:return
        item=self.stores.setdefault(name,{'http_statuses':{},'network_seconds':0,'max_response_seconds':0,'cache_events':0,'issues':[]})
        status=re.search(r'HTTP END status=(\d{3})',text)
        if status:
            key=status[1];item['http_statuses'][key]=item['http_statuses'].get(key,0)+1
            elapsed=re.search(r'elapsed=([0-9.]+)s',text)
            if elapsed:
                seconds=float(elapsed[1]);item['network_seconds']=round(item['network_seconds']+seconds,3);item['max_response_seconds']=max(item['max_response_seconds'],seconds)
        if 'CACHE HIT:' in text or 'SAVED RESPONSE:' in text:item['cache_events']+=1
        item['issues']=sorted(set(item['issues'])|set(issue_codes(text)))
        if time.monotonic()-self.updated>=10:self.flush()
    def flush(self):
        atomic_json(self.path,{'started_epoch':self.started,'elapsed_seconds':round(time.time()-self.started,1),'stores':self.stores});self.updated=time.monotonic()


def safe_text(value,limit=100):
    return ''.join(c for c in str(value or '') if c.isprintable())[:limit]


def build_report(data,output):
    data=Path(data);output=Path(output);summary={};telemetry={}
    for path,target in [(data/'ANAS_DATA_FETCH'/'run-summary.json',summary),(data/'telemetry.json',telemetry)]:
        try:
            loaded=json.loads(path.read_text(encoding='utf-8'))
            if isinstance(loaded,dict):target.update(loaded)
        except (ValueError,OSError):pass
    if not summary:
        database=data/'saved_runs'/'run_state.sqlite3'
        if database.is_file():
            try:
                with sqlite3.connect(database.as_uri()+'?mode=ro',uri=True) as db:row=db.execute('SELECT payload FROM state WHERE id=1').fetchone()
                summary=json.loads(row[0]) if row else {}
            except (ValueError,sqlite3.Error):pass
    stores=[]
    for site in summary.get('stores',summary.get('sites',[]))[:30]:
        if not isinstance(site,dict):continue
        name=safe_text(site.get('name'));stats=telemetry.get('stores',{}).get(name,{})
        status=safe_text(site.get('status'),24)
        issues=set(stats.get('issues',[]))|set(issue_codes(str(site.get('detail',''))))
        if status in ('failed','blocked') and not issues:issues.add('STORE_FAILED')
        # Explicit allowlist: never copy free-text exception details, URLs, response bodies or settings.
        item={'name':name,'status':status,'review_required':bool(site.get('reviewed')),'issue_codes':sorted(x for x in issues if re.fullmatch(r'[A-Z0-9_]{1,50}',x))}
        revision=str(site.get('software_revision',''))
        if re.fullmatch(r'[0-9a-f]{16}',revision):item['software_revision']=revision
        for key in ('products','variants'):
            if isinstance(site.get(key),int) and site[key]>=0:item[key]=site[key]
        item['http_statuses']={k:int(v) for k,v in stats.get('http_statuses',{}).items() if re.fullmatch(r'\d{3}',str(k)) and isinstance(v,int) and v>=0}
        for key in ('network_seconds','max_response_seconds','cache_events'):
            value=stats.get(key,0)
            if isinstance(value,(int,float)) and 0<=value<10**12:item[key]=value
        stores.append(item)
    run=os.environ.get('GITHUB_RUN_ID','');attempt=os.environ.get('GITHUB_RUN_ATTEMPT','1');sha=os.environ.get('GITHUB_SHA','')
    report={'schema_version':1,'generated_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'run_id':run if run.isdigit() else '', 'attempt':attempt if attempt.isdigit() else '1','source_commit':sha if re.fullmatch(r'[0-9a-f]{40}',sha) else '', 'status':safe_text(summary.get('status','no_saved_state'),30),'checkpoint_saved':summary.get('checkpoint')=='saved','python':platform.python_version(),'elapsed_seconds':telemetry.get('elapsed_seconds',0),'stores':stores}
    atomic_json(output/'report.json',report)
    logs=[]
    for name in ('fetch.log.2','fetch.log.1','fetch.log'):
        try:logs.extend((data/name).read_text(encoding='utf-8',errors='replace').splitlines())
        except OSError:pass
    (output/'redacted-log.txt').write_text('\n'.join(redact(x) for x in logs[-2000:]),encoding='utf-8')
    return report

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--data',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args();build_report(args.data.resolve(),args.output)
