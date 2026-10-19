"""Bounded verification of the exact upstream failure; no catalog crawl."""
import json,os,time
from types import SimpleNamespace
from urllib.robotparser import RobotFileParser
import requests
import czone_source_support as c
from source_research import publish

def main():
    url=c.BASE+'/ugreen-nexode-pro-65w-gan-fast-charger'
    report={'source_commit':os.environ['GITHUB_SHA'],'run_id':os.environ['GITHUB_RUN_ID'],'url':url,'software_tests':'passed','live_result':'not_checked'}
    with requests.Session() as session:
        session.headers['User-Agent']='ChotuAppCatalogRefresh/1.0'
        robots=session.get(c.BASE+'/robots.txt',timeout=25)
        if robots.status_code!=200:report['live_result']='robots_unavailable'
        else:
            parser=RobotFileParser();parser.parse(robots.text.splitlines())
            if not parser.can_fetch('ChotuAppCatalogRefresh',url):report['live_result']='robots_disallowed'
            else:
                g={'S':session,'_chotu_tls':SimpleNamespace(),'_chotu_wait':lambda:None,'_chotu_backoff':lambda seconds,reason:time.sleep(seconds)}
                time.sleep(2)
                try:
                    response=c.fetch_page(g,session,url);report['live_result']='source_recovered' if response.status_code==200 else 'unexpected_response'
                    report['http_status']=response.status_code
                    if response.status_code==200:
                        try:
                            product=c.parse_product(response.text,url);report['product_id']=product.get('id');report['product_availability']=product.get('available')
                        except (ValueError,KeyError,TypeError) as exc:
                            report['live_result']='product_schema_requires_review';report['schema_error']=str(exc)[:200]
                except c.TemporaryPageError:report['live_result']='upstream_still_unavailable_after_bounded_retries'
                except Exception as exc:report['live_result']='source_requires_cooldown_or_review';report['exception_type']=type(exc).__name__
    publish(report,branch='category-reports');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
