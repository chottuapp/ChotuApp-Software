"""Sapphire public HTML adapter. Never request the disallowed variation API."""
import csv,hashlib,json,re,time
from pathlib import Path
from urllib.parse import urlsplit,urljoin,parse_qsl,urlencode,urlunsplit
from urllib.robotparser import RobotFileParser
from xml.etree import ElementTree as ET
from decimal import Decimal,InvalidOperation
from bs4 import BeautifulSoup
BASE='https://pk.sapphireonline.pk'
AGENT='ChotuAppCatalogRefresh'
class SourceUnavailable(RuntimeError):pass

def amount(value):
    try:value=Decimal(str(value))
    except (InvalidOperation,TypeError):raise ValueError('Sapphire price missing or invalid')
    if not value.is_finite() or value<=0:raise ValueError('Sapphire price missing or invalid')
    return str(value)

def primary_nodes(main,selector):
    """Ignore recommendation tiles and nested foreign products inside the PDP wrapper."""
    result=[]
    for node in main.select(selector):
        parent=node
        while parent is not main:
            classes=parent.get('class',[])
            if 'product-tile' in classes or ('product-detail' in classes and parent.get('data-pid') and parent.get('data-pid')!=main.get('data-pid')):break
            parent=parent.parent
        else:result.append(node)
    return result

def inspect_page(html,url):
    soup=BeautifulSoup(html,'html.parser');scopes=soup.select('.product-wrapper[data-pid]')
    if len(scopes)!=1:raise ValueError('Exact Sapphire product scope missing or ambiguous: '+url)
    main=scopes[0];master=main.get('data-master-id');pid=main.get('data-pid')
    if not master or not pid:raise ValueError('Source product identity missing')
    buttons=primary_nodes(main,'button.add-to-cart[data-gtmga4data]')
    button=buttons[0] if len(buttons)==1 else None
    if button is None:raise ValueError('Product price/currency evidence missing')
    data=json.loads(button['data-gtmga4data'])
    if data.get('item_id')!=master or button.get('data-pid')!=pid:raise ValueError('Source product identity mismatch')
    if data.get('currencyCode')!='PKR':raise ValueError('Explicit PKR required')
    price=amount(data.get('price'));price_nodes=primary_nodes(main,'.price .sales .cc-price[content]')
    visible_prices={Decimal(amount(node['content'])) for node in price_nodes}
    if visible_prices!={Decimal(price)}:raise ValueError('Visible and structured primary product prices disagree: expected '+price+'; visible '+str(sorted(str(v) for v in visible_prices)))
    compare=data.get('compare_price');compare=amount(compare) if compare not in (None,'',0) else None
    if compare and Decimal(compare)<=Decimal(price):compare=None
    canonical=soup.select_one('link[rel="canonical"]')
    if canonical is None:raise ValueError('Canonical product link missing')
    canonical=urljoin(BASE,canonical.get('href',''));cp=urlsplit(canonical)
    if cp.scheme!='https' or cp.hostname!='pk.sapphireonline.pk' or cp.path.rsplit('/',1)[-1]!=pid+'.html':raise ValueError('Canonical product identity mismatch')
    # Requested URLs may contain public size selectors but must retain the actual master/variant identity.
    requested=urlsplit(url)
    if requested.hostname!='pk.sapphireonline.pk' or requested.path.rsplit('/',1)[-1] not in (master+'.html',pid+'.html'):raise ValueError('Requested source identity mismatch')
    fixed_options={}
    for attr in {n.find_parent(attrs={'data-attr':True}).get('data-attr') for n in primary_nodes(main,'[data-attr] input.options-select')} - {'size'}:
        nodes=[n for n in primary_nodes(main,'[data-attr] input.options-select') if n.find_parent(attrs={'data-attr':True}).get('data-attr')==attr]
        if attr!='itemType' or len(nodes)!=1 or not nodes[0].has_attr('checked') or not nodes[0].get('data-attr-value') or nodes[0].get('data-pid')!=pid:raise ValueError('Additional product option requires verification: '+str(attr))
        fixed_options['dwvar_'+master+'_'+attr]=nodes[0]['data-attr-value']
    sizes=[]
    for node in primary_nodes(main,'[data-attr="size"] input.options-select'):
        item=node.find_parent(class_='size-item');label=item.find('span') if item else None
        value=node.get('data-attr-value')
        if not label or not value or node.get('data-pid')!=pid:raise ValueError('Missing size value/label or mismatched product')
        text=label.get_text(' ',strip=True)
        # These parameter names/values are observed in the page controls; only the canonical HTML path is requested.
        params=[(k,v) for k,v in parse_qsl(urlsplit(node.get('value','')).query,keep_blank_values=True) if k.startswith('dwvar_') and k.endswith('_size')]
        if len(params)!=1:raise ValueError('Public size selector parameter unavailable')
        observed=dict(parse_qsl(urlsplit(node.get('value','')).query,keep_blank_values=True))
        if any(observed.get(k)!=v for k,v in fixed_options.items()):raise ValueError('Size selector does not preserve fixed product option')
        sizes.append({'fixed_options':fixed_options,'value':value,'label':text,'parameter':params[0][0],'selected':node.has_attr('checked')})
    if len({s['value'] for s in sizes})!=len(sizes):raise ValueError('Duplicate size values')
    selected=[s for s in sizes if s['selected']]
    if len(selected)>1:raise ValueError('Ambiguous selected size')
    if selected and (pid==master or data.get('item_variant')!=pid):raise ValueError('Selected variant identity not established')
    if not selected and pid!=master:raise ValueError('Variant page has no verified selected size')
    images=[]
    for node in primary_nodes(main,'img.pdp-image'):
        image=urljoin(BASE,node.get('data-high-src') or node.get('data-src') or node.get('src',''))
        p=urlsplit(image)
        if p.scheme!='https' or p.hostname!='pk.sapphireonline.pk':continue
        if image not in images:images.append(image)
    if not images:raise ValueError('Verified product gallery missing')
    title=str(data.get('item_name') or '').strip()
    if not title:raise ValueError('Product name missing')
    description='\n\n'.join(x.get_text('\n',strip=True) for x in primary_nodes(main,'.value.content'))
    if not description:raise ValueError('Product description unavailable')
    path=[]
    for node in soup.select('.breadcrumb a[href]'):
        link=urljoin(BASE,node['href']);p=urlsplit(link);label=node.get_text(' ',strip=True)
        if label and p.hostname=='pk.sapphireonline.pk' and p.path.startswith('/collections/') and '/products/' not in p.path:path.append(label)
    return dict(fixed_options=fixed_options,master_id=master,id=pid,title=title,price=price,compare_at_price=compare,sizes=sizes,selected_size=selected[0] if selected else None,available=not button.has_attr('disabled'),images=images,description=description,category_path=path,canonical_url=canonical)

def variant_url(master_url,size):
    p=urlsplit(master_url)
    if p.scheme!='https' or p.hostname!='pk.sapphireonline.pk' or '/products/' not in p.path or not p.path.endswith('.html'):raise ValueError('Public master product URL required')
    if not re.fullmatch(r'dwvar_[A-Za-z0-9_-]+_size',size['parameter']):raise ValueError('Invalid observed size parameter')
    fixed=size.get('fixed_options',{})
    if any(not re.fullmatch(r'dwvar_[A-Za-z0-9_-]+_itemType',key) for key in fixed):raise ValueError('Invalid fixed option parameter')
    return urlunsplit((p.scheme,p.netloc,p.path,urlencode({**fixed,size['parameter']:size['value']}),''))

def normalize_product(page,url,read):
    master=inspect_page(page,url)
    if master['selected_size']:raise ValueError('Catalog discovery must use an unselected master product')
    variants=[];labels=[]
    if master['sizes']:
        for size in master['sizes']:
            selected_url=variant_url(url,size);variant=inspect_page(read(selected_url).text,selected_url)
            if variant['master_id']!=master['master_id'] or not variant['selected_size'] or variant['selected_size']['value']!=size['value']:raise ValueError('Public size selection did not select the requested variant')
            if variant['fixed_options']!=master['fixed_options']:raise ValueError('Selected variant fixed option changed')
            if variant['selected_size']['label']!=size['label']:raise ValueError('Variant size label changed')
            if variant['id'] in {v['id'] for v in variants}:raise ValueError('Repeated variant identity')
            variants.append({'id':variant['id'],'sku':variant['id'],'price':variant['price'],'compare_at_price':variant['compare_at_price'],'available':variant['available'],'option1':size['label'],'featured_image':{'src':variant['images'][0]}});labels.append(size['label'])
    else:
        variants=[{'id':master['id'],'sku':master['id'],'price':master['price'],'compare_at_price':master['compare_at_price'],'available':master['available']}]
    # Website-reported availability only; never derive quantity from quantity widgets or low-stock text.
    from website_category_support import fact
    category=fact(master['category_path'],url,'verified_product_breadcrumb')
    images=[{'src':u,'position':i+1} for i,u in enumerate(master['images'])]
    return {'id':master['master_id'],'handle':master['master_id'],'title':master['title'],'body_html':master['description'],'vendor':'Sapphire','product_type':master['category_path'][-1] if master['category_path'] else '', 'status':'active','options':[{'name':'Size','values':labels}] if labels else [],'variants':variants,'images':images,'image':images[0],'_source_url':url,'_website_category_evidence':category or {},'_popularity_page_note':'Sapphire source review: partial public-page catalog coverage; exact selected variant pages used. Full catalog completeness, website listing order, checkout availability and popularity are not independently verified.'}

class PublicCatalog:
    def __init__(self,g,log):
        self.g=g;self.log=log;self.robot=None;self.last=0;self.cache=None
        tls=g.get('_chotu_tls');path=getattr(tls,'saved_api_path',None)
        if path:
            from laam_source_support import ParsedProductCache
            self.cache=ParsedProductCache(Path(path).with_name('sapphire-parsed.sqlite3'),hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    def close(self):
        if self.cache:self.cache.close()
    def read(self,url,fresh=False):
        p=urlsplit(url)
        if p.scheme!='https' or p.hostname!='pk.sapphireonline.pk' or p.username or p.password or p.port not in (None,443):raise SourceUnavailable('Pakistan public source changed host')
        if 'demandware.store' in p.path or (self.robot and not self.robot.can_fetch(AGENT,url)):raise SourceUnavailable('Public source path disallowed; no request made')
        if any(k in ('start','sz','cgid','srsltid','selectedUrl') or k.startswith(('prefn','prefv','pmin','pmax','srule')) for k,v in parse_qsl(p.query)):raise SourceUnavailable('Public pagination/refinement path disallowed; no request made')
        self.g['_chotu_wait']()
        cache=getattr(self.g.get('_chotu_tls'),'saved_response_cache',None)
        response=cache.get(url) if cache and not fresh else None;cached=response is not None
        self.g['_chotu_debug_request'](url,1)
        if response is None:
            self.g['_chotu_backoff'](max(0,self.last+1.5-time.monotonic()),'Sapphire public page pacing');self.last=time.monotonic()
            session=self.g['S'];get=getattr(session,'get_fresh',session.get) if fresh else session.get
            response=get(url,timeout=35)
        if urlsplit(response.url).hostname!='pk.sapphireonline.pk':raise SourceUnavailable('Pakistan source redirected to a foreign host')
        self.g['_chotu_debug_response'](response.status_code,len(response.content),cached=cached)
        if response.status_code in (429,500,502,503,504):raise RuntimeError('SOURCE PAUSED: Sapphire public server response '+str(response.status_code)+'; retry saved store after at least 60s. Checkpoint retained')
        if response.status_code!=200:raise SourceUnavailable('Public page unavailable HTTP '+str(response.status_code))
        if len(response.content)>20*1024**2:raise ValueError('Public response exceeds validated size bound')
        return response
    def catalog(self):
        robots=self.read(BASE+'/robots.txt',fresh=True);self.robot=RobotFileParser();self.robot.parse(robots.text.splitlines())
        maps=re.findall(r'(?im)^Sitemap:\s*(https://\S+)',robots.text);queue=list(dict.fromkeys(maps));seen=set();products={};collections=[]
        if not queue:raise SourceUnavailable('Public sitemap declaration missing')
        while queue:
            url=queue.pop(0)
            if url in seen:continue
            if len(seen)>=100:raise ValueError('Sitemap coverage bound reached')
            seen.add(url);tree=ET.fromstring(self.read(url).content);local=lambda tag:tag.rsplit('}',1)[-1]
            if local(tree.tag)=='sitemapindex':queue.extend(n.text.strip() for n in tree.iter() if local(n.tag)=='loc' and n.text);continue
            if local(tree.tag)!='urlset':raise ValueError('Unknown public sitemap format')
            for node in tree:
                for child in node:
                    if local(child.tag)!='loc' or not child.text:continue
                    link=child.text.strip();p=urlsplit(link)
                    if p.hostname!='pk.sapphireonline.pk':continue
                    if '/products/' in p.path and p.path.endswith('.html'):products.setdefault(p.path.rsplit('/',1)[-1],link)
                    elif p.path.startswith('/collections/') and not p.query and link not in collections:collections.append(link)
        # Declared sitemap contains category pages on the observed storefront. Inspect only their allowed default pages.
        for index,url in enumerate(collections,1):
            if not self.robot.can_fetch(AGENT,url):continue
            soup=BeautifulSoup(self.read(url).text,'html.parser')
            for node in soup.select('.product-tile a[href], .pdp-link a[href]'):
                link=urljoin(BASE,node['href']);p=urlsplit(link)
                if p.hostname=='pk.sapphireonline.pk' and '/products/' in p.path and p.path.endswith('.html'):
                    # Drop merchandising tracking from the normal canonical product address.
                    link=urlunsplit((p.scheme,p.netloc,p.path,'',''));products.setdefault(p.path.rsplit('/',1)[-1],link)
            if index==1 or index%20==0:self.log(f'SAPPHIRE PUBLIC COLLECTIONS: {index}/{len(collections)} inspected; {len(products)} product URLs discovered')
        if not products:raise SourceUnavailable('No permitted public product URLs discovered')
        result=[]
        for index,url in enumerate(products.values(),1):
            self.g['_chotu_wait']();product=self.cache.get(url) if self.cache else None
            if product is None:
                product=normalize_product(self.read(url).text,url,self.read)
                if self.cache:self.cache.put(url,product)
            result.append(product)
            if index==1 or index%25==0:self.log(f'SAPPHIRE PUBLIC PRODUCTS: {index}/{len(products)} verified; exact selected variant pages; stock quantities unknown')
        # Default pages cannot establish full catalog coverage when start/sz pagination is disallowed.
        self.log('REVIEW REQUIRED: Sapphire public-page export only; pagination/full catalog coverage and independent checkout validation unverified. No forbidden variant API used.')
        return result,False

def enable_sapphire_source(g):
    if g.get('_chotu_sapphire_source'):return
    original=g['_chotuapp_run_site_original']
    def run(base,name,template,log):
        if (urlsplit(base).hostname or '').lower().removeprefix('www.') not in ('sapphireonline.pk','pk.sapphireonline.pk'):return original(base,name,template,log)
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
        except SourceUnavailable as exc:raise RuntimeError('SOURCE BLOCKED: Sapphire '+str(exc)) from exc
        except (ValueError,TypeError,KeyError) as exc:raise RuntimeError('ADAPTER ERROR: Sapphire '+str(exc)+'. Saved work retained; no price/stock guessed.') from exc
        finally:source.close();g.update(old)
    g['_chotuapp_run_site_original']=run;g['_chotu_sapphire_source']=True
