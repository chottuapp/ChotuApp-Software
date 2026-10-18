"""Bounded public category checks; reports labels and provenance, never private data."""
import json,os,time
from pathlib import Path
from types import SimpleNamespace
from urllib.robotparser import RobotFileParser
import requests
from openpyxl import load_workbook
from website_order_support import Capture,navigation,public_link
from website_category_support import navigation_membership,breadcrumb
from source_research import publish

def main():
    results=[]
    stores=[('Miss Rose','https://missrose.com.pk'),('Shop Modest','https://www.shopmodest.pk'),('Skin Factor','https://www.skinfactor.pk'),('Rivaj UK','https://rivaj-uk.com'),('Cool and Cool','https://www.coolandcool.pk'),('Nisa Naturals','https://nisanaturals.pk')]
    for name,base in stores:
        record={'store':name,'url':base,'verified_memberships':0};results.append(record)
        with requests.Session() as session:
            session.headers['User-Agent']='ChotuAppCatalogRefresh/1.0'
            tls=SimpleNamespace();logs=[];g={'S':session,'_chotu_tls':tls,'_chotu_wait':lambda:None,'_chotu_backoff':lambda seconds,reason:time.sleep(seconds)};capture=Capture(g,base,logs.append,max_requests=8)
            try:
                robot=RobotFileParser();robot.parse(capture.page(base+'/robots.txt').get_text().splitlines());capture.robot=robot
                home=capture.page(base+'/');nav=navigation(home,base);record['navigation_labels']=[item.get('category_path') for item in nav]
                tls.website_category_navigation=nav;tls.website_category_robot=robot
                def get_json(url):
                    if capture.requests>=7 or not robot.can_fetch('ChotuAppCatalogRefresh',url):raise ValueError('Bound or robots restriction')
                    time.sleep(1.5);capture.requests+=1;response=session.get(url,timeout=25)
                    response.raise_for_status()
                    if not public_link(base,response.url) or len(response.content)>5*1024**2:raise ValueError('Response outside source boundaries')
                    return response.json()
                navigation_membership(tls,base,get_json,lambda:None,logs.append,max_requests=3)
                facts=tls.website_category_evidence;record['verified_memberships']=len(facts);record['samples']=[{'handle':key,**value} for key,value in list(facts.items())[:3]]
                file=Path('catalog-files/rule804-20261018-fresh12')/(name.replace(' ','_')+'_Rule804.xlsx')
                if file.exists():
                    w=load_workbook(file,read_only=True);it=w['Products'].values;h=next(it);row=next(it);url=row[h.index('source_url')];w.close()
                    record['product_breadcrumb']=breadcrumb(capture.page(url),url)
            except Exception as exc:record['limitation']=type(exc).__name__+': '+str(exc)[:160]
            record['logs']=logs[-3:]
    verified=sum(bool(r.get('verified_memberships') or r.get('product_breadcrumb')) for r in results)
    report={'run_id':os.environ['GITHUB_RUN_ID'],'source_commit':os.environ['GITHUB_SHA'],'verified_sources':verified,'coverage':'bounded public sample, not a full-store guarantee','sources':results}
    publish(report,branch='category-reports');print(json.dumps(report,indent=2))
    if verified<3:raise SystemExit('Need at least three verified public category samples before restart')
if __name__=='__main__':main()
