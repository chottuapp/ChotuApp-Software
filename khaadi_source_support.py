"""Khaadi public HTML adapter. Never request the disallowed variation API."""
import csv,hashlib,json,re,time
from pathlib import Path
from urllib.parse import urlsplit,urljoin,parse_qsl,urlencode,urlunsplit
from urllib.robotparser import RobotFileParser
from xml.etree import ElementTree as ET
from decimal import Decimal,InvalidOperation
from bs4 import BeautifulSoup
BASE='https://pk.khaadi.com'
AGENT='ChotuAppCatalogRefresh'
class SourceUnavailable(RuntimeError):pass

def amount(value):
    try:value=Decimal(str(value))
    except (InvalidOperation,TypeError):raise ValueError('Khaadi price missing or invalid')
    if not value.is_finite() or value<=0:raise ValueError('Khaadi price missing or invalid')
    return str(value)

def inspect_page(html,url):
    soup=BeautifulSoup(html,'html.parser');outer=soup.select_one('.product-set-detail[data-pid]')
    if outer is None:raise ValueError('Primary Khaadi product scope missing')
    main=outer.select_one('.set-item[data-pid]');pid=outer['data-pid']
    if main is None or main['data-pid']!=pid:raise ValueError('Primary product and bundle item identity disagree')
    records=[]
    for node in soup.select('script[type="application/ld+json"]'):
        data=json.loads(node.get_text())
        if isinstance(data,dict) and data.get('@type')=='Product' and str(data.get('sku'))==pid:records.append(data)
    if len(records)!=1:raise ValueError('Unique primary structured product missing')
    data=records[0];offer=data.get('offers',{})
    if offer.get('priceCurrency')!='PKR':raise ValueError('Explicit PKR required')
    price=amount(offer.get('price'));prices={Decimal(amount(n['content'])) for n in main.select('.price .sales [content]')}
    if prices!={Decimal(price)}:raise ValueError('Primary visible and structured prices disagree')
    lists={Decimal(amount(n['content'])) for n in main.select('.price .list [content]')}
    if len(lists)>1:raise ValueError('Ambiguous primary regular price')
    compare=str(next(iter(lists))) if lists and next(iter(lists))>Decimal(price) else None
    canonical=soup.select_one('link[rel="canonical"]');canonical=urljoin(BASE,canonical.get('href','')) if canonical else ''
    if urlsplit(canonical).hostname!='pk.khaadi.com' or urlsplit(canonical).path.rsplit('/',1)[-1]!=pid+'.html' or urljoin(BASE,offer.get('url',''))!=canonical:raise ValueError('Canonical product identity mismatch')
    page=soup.select_one('.page[data-querystring]');echo=dict(parse_qsl(page['data-querystring'])) if page else {}
    requested=dict(parse_qsl(urlsplit(url).query));selection={k:v for k,v in requested.items() if k.startswith('dwvar_') and k.endswith('_size')}
    if selection and any(echo.get(k)!=v for k,v in selection.items()):raise ValueError('Public page did not acknowledge requested size')
    sizes=[]
    for node in main.select('[data-attr="size"] input.options-select'):
        label=node.find_next_sibling('span');value=node.get('data-attr-value');params=[(k,v) for k,v in parse_qsl(urlsplit(node.get('value','')).query) if k.startswith('dwvar_') and k.endswith('_size')]
        if label is None or not value or len(params)!=1 or node.get('data-pid')!=pid:raise ValueError('Primary size control incomplete')
        sizes.append({'value':value,'label':label.get_text(' ',strip=True),'parameter':params[0][0]})
    if not sizes or len({v['value'] for v in sizes})!=len(sizes):raise ValueError('Unique observed sizes required')
    selected=[v for v in sizes if v['value'] in selection.values()]
    if selection and len(selected)!=1:raise ValueError('Selected size unavailable')
    availability=main.select_one('.product-availability[data-available][data-ready-to-order]')
    available=None
    if selection:
        if availability is None or availability['data-available'] not in ('true','false') or availability['data-ready-to-order']!='true':raise ValueError('Selected variant stock unverified')
        available=availability['data-available']=='true'
        if offer.get('availability','').rsplit('/',1)[-1]!=('InStock' if available else 'OutOfStock'):raise ValueError('Selected stock sources disagree')
    images=list(dict.fromkeys(urljoin(BASE,u) for u in data.get('image',[]) if isinstance(u,str)))
    if not images or any(urlsplit(u).hostname!='pk.khaadi.com' or urlsplit(u).scheme!='https' for u in images):raise ValueError('Verified primary images missing')
    description=soup.select_one('.description-and-detail')
    title=str(data.get('name') or '').strip()
    if not title:raise ValueError('Product name missing')
    return dict(id=pid,title=title,price=price,compare_at_price=compare,available=available,sizes=sizes,selected=selected[0] if selected else None,images=images,description=description.get_text('\n',strip=True) if description else str(data.get('description') or ''),canonical=canonical)

def variant_url(url,size):
    p=urlsplit(url)
    if p.hostname!='pk.khaadi.com' or p.scheme!='https' or not p.path.endswith('.html') or not re.fullmatch(r'dwvar_[A-Za-z0-9_-]+_size',size['parameter']):raise ValueError('Invalid public size route')
    return urlunsplit((p.scheme,p.netloc,p.path,urlencode({size['parameter']:size['value']}),''))

def normalize_product(html,url,read):
    master=inspect_page(html,url);variants=[]
    if master['selected']:raise ValueError('Catalog must start from master page')
    for size in master['sizes']:
        selected_url=variant_url(url,size);page=inspect_page(read(selected_url).text,selected_url)
        if not page['selected'] or page['selected']['value']!=size['value'] or page['title']!=master['title'] or page['id']==master['id'] or page['images']!=master['images']:raise ValueError('Selected variant family/identity mismatch')
        if page['id'] in {v['id'] for v in variants}:raise ValueError('Repeated selected variant identity')
        variants.append({'id':page['id'],'sku':page['id'],'option1':size['label'],'price':page['price'],'compare_at_price':page['compare_at_price'],'available':page['available'],'featured_image':{'src':page['images'][0]}})
    images=[{'src':u,'position':i+1} for i,u in enumerate(master['images'])]
    from website_category_support import fact
    soup=BeautifulSoup(html,'html.parser');labels=[]
    for node in soup.select('.breadcrumb a[href]'):
        link=urlsplit(urljoin(BASE,node['href']));label=node.get_text(' ',strip=True)
        if link.hostname=='pk.khaadi.com' and link.path!='/' and not link.path.endswith('.html') and label:labels.append(label)
    category=fact(labels,url,'verified_product_breadcrumb') or {}
    return dict(id=master['id'],handle=master['id'],title=master['title'],body_html=master['description'],vendor='Khaadi',product_type='',status='active',options=[{'name':'Size','values':[s['label'] for s in master['sizes']]}],variants=variants,images=images,image=images[0],_source_url=url,_website_category_evidence=category,_popularity_page_note='Khaadi source review: exact public selected size pages; partial coverage, website order and checkout availability unverified; stock quantities unknown.')

class PublicCatalog:
    def __init__(self,g,log):
        self.g=g;self.log=log;self.robot=None;self.last=0;self.cache=None
        tls=g.get('_chotu_tls');path=getattr(tls,'saved_api_path',None)
        if path:
            from laam_source_support import ParsedProductCache
            self.cache=ParsedProductCache(Path(path).with_name('khaadi-parsed.sqlite3'),hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    def close(self):
        if self.cache:self.cache.close()
    def read(self,url,fresh=False,allow_missing=False):
        p=urlsplit(url)
        if p.scheme!='https' or p.hostname!='pk.khaadi.com' or p.username or p.password or p.port not in (None,443):raise SourceUnavailable('Pakistan public source changed host')
        if 'demandware.store' in p.path or (self.robot and not self.robot.can_fetch(AGENT,url)):raise SourceUnavailable('Public source path disallowed; no request made')
        if any(k in ('start','sz','cgid','srsltid','selectedUrl') or k.startswith(('prefn','prefv','pmin','pmax','srule')) for k,v in parse_qsl(p.query)):raise SourceUnavailable('Public pagination/refinement path disallowed; no request made')
        self.g['_chotu_wait']()
        cache=getattr(self.g.get('_chotu_tls'),'saved_response_cache',None)
        response=cache.get(url) if cache and not fresh else None;cached=response is not None
        self.g['_chotu_debug_request'](url,1)
        if response is None:
            self.g['_chotu_backoff'](max(0,self.last+1.5-time.monotonic()),'Khaadi public page pacing');self.last=time.monotonic()
            session=self.g['S'];get=getattr(session,'get_fresh',session.get) if fresh else session.get
            response=get(url,timeout=35)
        if urlsplit(response.url).hostname!='pk.khaadi.com':raise SourceUnavailable('Pakistan source redirected to a foreign host')
        self.g['_chotu_debug_response'](response.status_code,len(response.content),cached=cached)
        if response.status_code in (429,500,502,503,504):raise RuntimeError('SOURCE PAUSED: Khaadi public server response '+str(response.status_code)+'; retry saved store after at least 60s. Checkpoint retained')
        if allow_missing and response.status_code in (404,410):return response
        if response.status_code!=200:raise SourceUnavailable('Public page unavailable HTTP '+str(response.status_code))
        if len(response.content)>20*1024**2:raise ValueError('Public response exceeds validated size bound')
        return response
    def catalog(self):
        robots=self.read(BASE+'/robots.txt',fresh=True);self.robot=RobotFileParser();self.robot.parse(robots.text.splitlines())
        queue=list(dict.fromkeys(re.findall(r'(?im)^Sitemap:\s*(https://\S+)',robots.text)));seen=set();urls={};categories=[]
        if not queue:raise SourceUnavailable('Declared public sitemap missing')
        while queue:
            url=queue.pop(0)
            if url in seen:continue
            if len(seen)>=100:raise ValueError('Sitemap coverage bound reached')
            seen.add(url);tree=ET.fromstring(self.read(url).content);local=lambda tag:tag.rsplit('}',1)[-1]
            if local(tree.tag)=='sitemapindex':queue.extend(n.text.strip() for n in tree.iter() if local(n.tag)=='loc' and n.text);continue
            if local(tree.tag)!='urlset':raise ValueError('Unknown sitemap format')
            for row in tree:
                for n in row:
                    if local(n.tag)!='loc' or not n.text:continue
                    p=urlsplit(n.text.strip())
                    if p.path.strip('/').split('/')[0].lower() in ('blogs','blog','pages','account','customer-service','stores','store-locator'):continue
                    if p.hostname=='pk.khaadi.com' and not p.query and not p.path.endswith('.html') and p.path.endswith('/') and n.text.strip() not in categories:categories.append(n.text.strip())
                    if p.hostname=='pk.khaadi.com' and re.fullmatch(r'/[^/]+/[A-Za-z0-9_-]*[0-9][A-Za-z0-9_-]*\.html',p.path) and not p.query:urls.setdefault(p.path.rsplit('/',1)[-1],n.text.strip())
        self.log('KHAADI DISCOVERY: '+str(len(categories))+' public category pages; '+str(len(urls))+' direct product links from sitemap')
        for index,url in enumerate(categories,1):
            if not self.robot.can_fetch(AGENT,url):
                self.log('KHAADI CATEGORY SKIPPED: robots disallow '+url);continue
            self.log(f'KHAADI CATEGORY: {index}/{len(categories)} '+url)
            response=self.read(url,allow_missing=True)
            if response.status_code in (404,410):
                self.log('KHAADI CATEGORY REMOVED: HTTP '+str(response.status_code)+' '+url);continue
            soup=BeautifulSoup(response.text,'html.parser')
            for node in soup.select('a[href]'):
                link=urljoin(BASE,node['href']);p=urlsplit(link)
                if p.hostname!='pk.khaadi.com' or p.scheme!='https' or p.username or p.password:continue
                if p.path.strip('/').split('/')[0].lower() in ('blogs','blog','pages','account','customer-service','stores','store-locator'):continue
                if not re.fullmatch(r'/[^/]+/[A-Za-z0-9_-]*[0-9][A-Za-z0-9_-]*\.html',p.path):continue
                canonical=urlunsplit((p.scheme,p.netloc,p.path,'',''))
                if self.robot.can_fetch(AGENT,canonical):urls.setdefault(p.path.rsplit('/',1)[-1],canonical)
            self.log(f'KHAADI LISTING PROGRESS: {index}/{len(categories)} categories; {len(urls)} distinct product URLs')
        if not urls:raise SourceUnavailable('No public product links found in permitted category listings')
        result=[]
        for index,url in enumerate(urls.values(),1):
            self.g['_chotu_wait']();product=self.cache.get(url) if self.cache else None
            if product is None:
                html=self.read(url).text;soup=BeautifulSoup(html,'html.parser')
                if soup.select_one('.product-set-detail[data-pid]') is None:
                    page=soup.select_one('[data-action]');action=page.get('data-action') if page else None
                    has_product=False
                    for node in soup.select('script[type="application/ld+json"]'):
                        try:
                            data=json.loads(node.get_text())
                            has_product=has_product or (isinstance(data,dict) and data.get('@type')=='Product')
                        except (ValueError,TypeError):pass
                    if action in ('Page-Show','Search-Show','Content-Show','Home-Show','Blog-Show') and not has_product:
                        self.log('KHAADI NON-PRODUCT SKIPPED: '+str(action)+' '+url);continue
                product=normalize_product(html,url,self.read)
                if self.cache:self.cache.put(url,product)
            result.append(product)
            if index==1 or index%25==0:self.log(f'KHAADI PUBLIC PRODUCTS: {index}/{len(urls)} verified')
        if not result:raise SourceUnavailable('No verified public products found; source page classification requires review')
        self.log('REVIEW REQUIRED: Khaadi public selected-size export; catalog completeness and website listing order unverified')
        return result,False

def enable_khaadi_source(g):
    if g.get('_chotu_khaadi_source'):return
    original=g['_chotuapp_run_site_original']
    def run(base,name,template,log):
        if (urlsplit(base).hostname or '').lower().removeprefix('www.') not in ('khaadi.com','pk.khaadi.com'):return original(base,name,template,log)
        source=PublicCatalog(g,log);keys=('discover','collections','refresh_variant_prices','storefront_cover','verified_top20','audit_fractional_prices','storefront_price_audit');old={k:g[k] for k in keys}
        def cover(base,p,pictures,log):
            g['_chotu_tls'].image_audit.append([p['_source_url'],'REVIEW',pictures[0]['src'] if pictures else '', 'Public product gallery retained; visual hero ordering unverified']);return None
        def audit(*args):
            # Writer signatures differ between the two existing audit hooks.
            for arg in args:
                if isinstance(arg,Path) and arg.suffix=='.csv':
                    with arg.open('w',encoding='utf-8-sig',newline='') as stream:
                        writer=csv.writer(stream);writer.writerow(['status','source','detail']);writer.writerow(['REVIEW',BASE,'Exact selected public variant pages used; full catalog and independent checkout verification unavailable'])
            log('PRICE AUDIT: REVIEW REQUIRED — source-page verification only');return set()
        def ranking(*args):g['_chotu_tls'].ranking_evidence={};return []
        g.update(discover=lambda base,log:source.catalog(),collections=lambda *args:{},refresh_variant_prices=lambda base,p,log:p['variants'],storefront_cover=cover,verified_top20=ranking,audit_fractional_prices=audit,storefront_price_audit=audit)
        try:return original(BASE,name,template,log)
        except SourceUnavailable as exc:raise RuntimeError('SOURCE BLOCKED: Khaadi '+str(exc)) from exc
        except (ValueError,TypeError,KeyError) as exc:raise RuntimeError('ADAPTER ERROR: Khaadi '+str(exc)+'. Saved work retained; no price/stock guessed.') from exc
        finally:source.close();g.update(old)
    g['_chotuapp_run_site_original']=run;g['_chotu_khaadi_source']=True
