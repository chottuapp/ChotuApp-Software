"""Verify Sapphire's permitted public-size route on the actual cloud runner."""
import json,sys
from pathlib import Path
from urllib.robotparser import RobotFileParser
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import requests
from sapphire_source_support import PublicCatalog,normalize_product,BASE,AGENT

def main():
    session=requests.Session();session.headers['User-Agent']=AGENT
    def debug_response(status,size,**kwargs):print('HTTP',status,'bytes',size,flush=True)
    g={'S':session,'_chotu_wait':lambda:None,'_chotu_backoff':lambda delay,*args:__import__('time').sleep(delay),'_chotu_debug_request':lambda url,attempt:print('PUBLIC GET',url,flush=True),'_chotu_debug_response':debug_response}
    source=PublicCatalog(g,print);report={'full_catalog_verified':False,'products':[]}
    try:
        robots=source.read(BASE+'/robots.txt',fresh=True);source.robot=RobotFileParser();source.robot.parse(robots.text.splitlines())
        for path in ['/collections/western-wear/products/WDNMV0726002.html','/collections/kurtas/products/00MSTKR26V52.html','/collections/kurtas/products/MSTEKR26V610.html','/collections/unstitched/products/U1SDDS26V91T.html','/collections/ready-to-wear/products/2PCSTCASV996_999.html','/collections/unstitched/products/U3PELXS26V91.html']:
            url=BASE+path;product=normalize_product(source.read(url).text,url,source.read)
            report['products'].append({'name':product['title'],'source_url':url,'variants':[{k:v.get(k) for k in ('id','option1','price','compare_at_price','available')} for v in product['variants']],'image_count':len(product['images'])})
        report['sample_verified']=True
        print('SAMPLE VERIFIED: public selected sizes, explicit PKR and website-reported availability. Full catalog coverage remains unverified.',flush=True)
    except Exception as exc:
        from diagnostics import redact
        report.update(sample_verified=False,error=redact(str(exc)));print('SOURCE CHECK FAILED:',report['error'],flush=True)
    finally:
        source.close();session.close();out=Path('source-diagnostics');out.mkdir(exist_ok=True);(out/'sapphire-public-route.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2),flush=True)
    return 0 if report.get('sample_verified') else 2
if __name__=='__main__':sys.exit(main())
