"""Check the Khaadi adapter through Windows curl's verified TLS stack."""
import hashlib,importlib.util,json,subprocess,sys,tempfile,time,urllib.request
from pathlib import Path
from types import SimpleNamespace
from urllib.robotparser import RobotFileParser
REVISION='38efa09'
FILES={'khaadi_source_support.py': '1cbc55fb2ec2b86b0945c916937072f1c0a95b8caebe688a8a44c970a2ff4ed0', 'website_category_support.py': '65dfda24fc281d3f986293421977ee9f3d758d375099fc005242677cac268cfc'}

def run_check(source,session,output):
    def debug_response(status,size,**kwargs):print('HTTP',status,'bytes',size,flush=True)
    g={'S':session,'_chotu_wait':lambda:None,'_chotu_backoff':lambda delay,*args:time.sleep(delay),'_chotu_debug_request':lambda url,attempt:print('PUBLIC GET',url,flush=True),'_chotu_debug_response':debug_response}
    reader=source.PublicCatalog(g,print);report={'full_catalog_verified':False,'sample_verified':False,'execution':'Windows local curl','products':[]}
    try:
        robots=reader.read(source.BASE+'/robots.txt',fresh=True);reader.robot=RobotFileParser();reader.robot.parse(robots.text.splitlines())
        url=source.BASE+'/black-cambric-kurta/1-26-320-A-C1-VG_MULTI.html'
        product=source.normalize_product(reader.read(url).text,url,reader.read)
        report['products'].append({'name':product['title'],'source_url':url,'variants':[{k:v.get(k) for k in ('id','option1','price','available')} for v in product['variants']],'image_count':len(product['images'])});report['sample_verified']=True
        print('LOCAL SAMPLE VERIFIED: exact public size prices and stock. Cloud fetching was not started.',flush=True)
    except Exception as exc:
        report['error']=str(exc);print('LOCAL CHECK FAILED:',str(exc),flush=True)
    finally:
        reader.close();output.write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report,indent=2),flush=True);print('Report:',output,flush=True)
    return 0 if report['sample_verified'] else 2

class CurlSession:
    def get(self,url,timeout=35):
        with tempfile.TemporaryDirectory() as tmp:
            body=Path(tmp)/'body.html'
            result=subprocess.run(['curl.exe','--silent','--show-error','--location','--proto','=https','--proto-redir','=https','--max-time',str(timeout),'--output',str(body),'--write-out','%{http_code}\n%{url_effective}','--user-agent','ChotuAppCatalogRefresh',url],capture_output=True,text=True,timeout=timeout+10)
            if result.returncode:raise RuntimeError('curl failed: '+result.stderr.strip())
            lines=result.stdout.strip().splitlines()
            if len(lines)!=2:raise RuntimeError('Unexpected curl status output')
            content=body.read_bytes()
            return SimpleNamespace(status_code=int(lines[0]),url=lines[1],content=content,text=content.decode('utf-8',errors='replace'))
    get_fresh=get

def main():
    try:import bs4
    except ImportError:subprocess.run([sys.executable,'-m','pip','install','beautifulsoup4'],check=True)
    desktop=Path.home()/'Desktop';out=desktop/'Khaadi_Local_Adapter_Check.json'
    with tempfile.TemporaryDirectory(prefix='khaadi-adapter-check-') as tmp:
        root=Path(tmp)
        for name,expected in FILES.items():
            data=urllib.request.urlopen('https://raw.githubusercontent.com/chottuapp/ChotuApp-Software/'+REVISION+'/'+name,timeout=60).read()
            if hashlib.sha256(data).hexdigest()!=expected:raise RuntimeError('Source checksum mismatch: '+name)
            (root/name).write_bytes(data)
        sys.path.insert(0,str(root))
        spec=importlib.util.spec_from_file_location('khaadi_local_checked',root/'khaadi_source_support.py');source=importlib.util.module_from_spec(spec);spec.loader.exec_module(source)
        return run_check(source,CurlSession(),out)
if __name__=='__main__':sys.exit(main())
