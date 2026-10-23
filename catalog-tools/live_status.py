"""Read-only live health tool for the assistant. No tokens, shell uploads or PC/phone prompts."""
import concurrent.futures,datetime,json,re
import requests
from bs4 import BeautifulSoup
REPO='chottuapp/ChotuApp-Software';RAW='https://raw.githubusercontent.com/'+REPO+'/'
def fetch(url):
 r=requests.get(url,params={'health_check':datetime.datetime.now(datetime.timezone.utc).timestamp()},timeout=20);r.raise_for_status();return r

def read_json(path):
 try:return fetch(RAW+path).json()
 except (requests.RequestException,ValueError):return {'unavailable':True}

def phone_state(phone,now):
 if phone.get('unavailable'):return {'status':'not_connected_or_no_report','status_confirmed':False,'message':'No published Android report; cloud cannot inspect an unconnected phone.'}
 try:age=(now-datetime.datetime.fromisoformat(phone['observed_utc'])).total_seconds()
 except (KeyError,ValueError,TypeError):return {'status':'invalid_report','status_confirmed':False}
 report=dict(phone);report['report_age_seconds']=max(0,round(age));report['status_confirmed']=0<=age<=180
 if not report['status_confirmed']:report['last_reported_status']=report.get('status');report['status']='unknown_stale_heartbeat'
 return report

def run_state(item):
 rid=str(item['databaseId']);result={'run_id':rid,'title':item.get('displayTitle',''),'reported_stores':item.get('stores',{})}
 try:
  text=BeautifulSoup(fetch('https://github.com/'+REPO+'/actions/runs/'+rid).text,'html.parser').get_text(' ',strip=True)
  match=re.search(r'\bStatus (In progress|Queued|Waiting|Success|Failure|Cancelled|Timed out|Skipped)\b',text)
  if not match:raise ValueError('Public run state missing')
  value=match[1];result.update(status='in_progress' if value=='In progress' else value.lower().replace(' ','_'),live_verified=True,checked_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
 except (requests.RequestException,ValueError):result.update(status='unknown',live_verified=False)
 result['snapshot']=item.get('snapshot','');result['snapshot_utc']=item.get('snapshot_utc')
 return result

def main():
 now=datetime.datetime.now(datetime.timezone.utc)
 paths=['runner-status-reports/latest.json','drive-sync-reports/latest.json','local-run-status/local/khaadi-android.json','source-research/latest.json']
 with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:runners,drive,phone,khaadi_probe=list(pool.map(read_json,paths))
 known={str(r['databaseId']):r for r in runners.get('runs',[])};recent=[]
 try:
  page=BeautifulSoup(fetch('https://github.com/'+REPO+'/actions/workflows/cloud-fetch.yml').text,'html.parser')
  for a in page.select('a[href*="/actions/runs/"]'):
   match=re.search(r'/actions/runs/(\d+)',a.get('href',''))
   if match and match[1] not in recent:
    recent.append(match[1]);known.setdefault(match[1],{'databaseId':match[1],'displayTitle':a.get_text(' ',strip=True)})
   if len(recent)>=12:break
 except requests.RequestException:pass
 ids=recent or list(known)[:12]
 with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:live=list(pool.map(run_state,[known[r] for r in ids]))
 audits=drive.get('audit804_results',{});campaign=drive.get('audit804_campaign')
 result={'checked_utc':now.isoformat(),'runner_report_utc':runners.get('checked_utc'),'runs':live,'active_verified':sum(r['status']=='in_progress' for r in live),'queued_verified':sum(r['status'] in ('queued','waiting') for r in live),'phone':phone_state(phone,now),'drive':{'sync_status':drive.get('sync_status'),'sync_error':drive.get('sync_error'),'checked_utc':drive.get('audit804_checked_utc'),'fresh_verified_uploads':[{k:v.get(k) for k in ('file_name','shop_code','verified_utc','file_url')}|{'store':name} for name,v in drive.get('uploaded',{}).items() if v.get('campaign_id')==campaign],'audit_pass':[n for n,a in audits.items() if a.get('status')=='pass'],'audit_hold':[{k:a.get(k) for k in ('store','findings_count','error','checked_utc')} for a in audits.values() if a.get('status')=='hold']},'limits':'Live run state is checked directly; source task counts retain their original snapshot timestamps. Missing/stale heartbeat is unknown, never proof of a running phone.'}
 result['khaadi_cloud']={'status':'source_verified' if khaadi_probe.get('sample_verified') is True else 'source_blocked' if khaadi_probe.get('execution')=='GitHub hosted runner' and khaadi_probe.get('error') else 'unknown','probe_run_id':khaadi_probe.get('run_id'),'probe_checked_utc':khaadi_probe.get('checked_utc'),'error':khaadi_probe.get('error'),'route_observations':khaadi_probe.get('public_route_observations',[]),'phone_required':False}
 for run in live:
  if 'khaadi-cloud' in run.get('title','') and run.get('live_verified') and run['status'] in ('in_progress','queued'):
   result['khaadi_cloud'].update(status=run['status'],run_id=run['run_id'])
 print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
