"""Verify Khaadi's permitted public-size route on the actual cloud runner."""
import json,sys
from pathlib import Path
from urllib.robotparser import RobotFileParser
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import requests
from khaadi_source_support import PublicCatalog,normalize_product,BASE,AGENT

def main():
    session=requests.Session();session.headers['User-Agent']='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/130.0 Safari/537.36'
    session.headers['Accept-Language']='en-PK,en;q=0.9'
    def debug_response(status,size,**kwargs):print('HTTP',status,'bytes',size,flush=True)
    g={'S':session,'_chotu_wait':lambda:None,'_chotu_backoff':lambda delay,*args:__import__('time').sleep(delay),'_chotu_debug_request':lambda url,attempt:print('PUBLIC GET',url,flush=True),'_chotu_debug_response':debug_response}
    source=PublicCatalog(g,print);report={'full_catalog_verified':False,'products':[],'execution':'GitHub hosted runner','request':'Owner requested phone-independent fresh Khaadi cloud start on 23 October 2026'}
    try:
        robots=source.read(BASE+'/robots.txt',fresh=True);source.robot=RobotFileParser();source.robot.parse(robots.text.splitlines())
        for path in ['/floral-tailored-3-piece/T-CHD09B-R-VG_MULTI.html','/black-cambric-kurta/1-26-320-A-C1-VG_MULTI.html']:
            url=BASE+path;product=normalize_product(source.read(url).text,url,source.read)
            report['products'].append({'name':product['title'],'source_url':url,'variants':[{k:v.get(k) for k in ('id','option1','price','compare_at_price','available')} for v in product['variants']],'image_count':len(product['images'])})
        report['sample_verified']=True
        print('SAMPLE VERIFIED: public selected sizes, explicit PKR and website-reported availability. Full catalog coverage remains unverified.',flush=True)
    except Exception as exc:
        from diagnostics import redact
        report.update(sample_verified=False,error=redact(str(exc)));print('SOURCE CHECK FAILED:',report['error'],flush=True)
    finally:
        source.close();session.close();out=Path('source-diagnostics');out.mkdir(exist_ok=True);(out/'khaadi-public-route.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2),flush=True)
        import os
        if os.environ.get('GITHUB_RUN_ID'):
            from source_research import publish
            publish(dict(report,run_id=os.environ['GITHUB_RUN_ID']),branch='source-research')
    return 0 if report.get('sample_verified') else 2
if __name__=='__main__':sys.exit(main())
