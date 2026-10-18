"""Order exports by observed default storefront navigation and product grids."""
from urllib.parse import urlsplit,urljoin,urlunsplit,parse_qsl,urlencode
from urllib.robotparser import RobotFileParser
from datetime import datetime,timezone
import re,time
from bs4 import BeautifulSoup
FIELDS=('website_category_order','website_subcategory_order','website_product_order','website_order_source_url','website_order_checked_at','website_order_status')
GRID='#product-grid, [data-product-grid], .product-grid, .collection-products, .products-grid, .grid--view-items, .product-list'
SKIP=re.compile(r'/account|/cart|/checkout|/search|/policies|/pages/|/blogs/|/products/',re.I)

def public_link(base,value):
    p=urlsplit(urljoin(base,str(value)))
    if p.scheme!='https' or p.username or p.password or p.port not in (None,443):return ''
    host=(p.hostname or '').lower().removeprefix('www.');expected=(urlsplit(base).hostname or '').lower().removeprefix('www.')
    if host!=expected:return ''
    query=[(k,v) for k,v in parse_qsl(p.query) if k in ('page','sort_by','start','sz','cgid','srule') or k.startswith('filter.')]
    return urlunsplit((p.scheme,p.netloc,p.path,urlencode(query),''))

def product_key(value):
    p=urlsplit(str(value));match=re.search(r'/products/([^/]+)',p.path)
    return match[1] if match else p.path.rstrip('/')

def navigation(soup,base):
    """Only observed header navigation/collection links, never the API's collection order."""
    roots=soup.select('header nav, header [role=navigation], [role=banner] nav, #shopify-section-header nav')
    if not roots:roots=soup.select('header, [role=banner]')
    if not roots:roots=[node for node in soup.select('nav') if node.find_parent('footer') is None]
    result=[];seen=set();groups={}
    for root in roots:
        for anchor in root.select('a[href]'):
            url=public_link(base,anchor['href']);path=urlsplit(url).path if url else ''
            label=anchor.get_text(' ',strip=True)
            if not url or not label or SKIP.search(path) or not re.search(r'/collections/[^/]+/?$|/(women|woman|men|man|kids|new-in)/?$',path):continue
            if path.rstrip('/') in ('/collections/all','/collections/frontpage') or url in seen:continue
            seen.add(url);parent_label=''
            for node in anchor.parents:
                if node is root:break
                if node.name not in ('li','details'):continue
                parent=node.find('a',recursive=False) or node.find('summary',recursive=False)
                if parent is not None and parent is not anchor and parent.get_text(' ',strip=True):
                    text=parent.get_text(' ',strip=True)
                    if text.casefold() not in ('shop','shop now','menu','all products'):parent_label=text
            category=parent_label or label;subcategory=label if parent_label and parent_label!=label else ''
            groups.setdefault(category,len(groups)+1)
            result.append({'url':url,'category':category,'subcategory':subcategory,'category_order':groups[category],'subcategory_order':len(result)+1})
    return result

def grid_products(soup,base):
    main=soup.select_one('main, [role=main]') or soup
    grids=main.select(GRID)
    cards=main.select('[data-testid=product-card], .product_card') if not grids else []
    if not grids and not cards:return []
    result=[];seen=set()
    candidates=[anchor for grid in grids for anchor in grid.select('a[href]')]
    candidates.extend(card.find_parent('a',href=True) or card.select_one('a[href]') for card in cards)
    for anchor in candidates:
        if anchor is None:continue
        url=public_link(base,anchor['href'])
        if not url or '/products/' not in urlsplit(url).path:continue
        if anchor.find_parent(class_=re.compile('recommend|recently|related',re.I)):continue
        key=product_key(url)
        if key not in seen:seen.add(key);result.append(key)
    return result

def next_page(soup,base):
    for node in soup.select('a[rel=next][href], link[rel=next][href], .pagination a.pagination__next[href], .pagination a[aria-label*="Next"][href], .pagination a[aria-label*="next"][href]'):
        url=public_link(base,node.get('href'))
        if url:return url
    return ''

class Capture:
    def __init__(self,g,base,log,max_requests=80,max_pages=5):
        self.g=g;self.base=base.rstrip('/');self.log=log;self.limit=max_requests;self.max_pages=max_pages;self.requests=0;self.robot=None;self.evidence={};self.complete=True;self.last=0
    def page(self,url):
        url=public_link(self.base,url)
        if not url or self.requests>=self.limit:raise ValueError('Storefront order request limit reached')
        if self.robot is not None and not self.robot.can_fetch('ChotuAppCatalogRefresh',url):raise ValueError('Storefront order path disallowed by source robots')
        self.g['_chotu_wait']();cache=getattr(self.g.get('_chotu_tls'),'saved_response_cache',None);response=cache.get(url) if cache else None
        cached=response is not None
        self.g.get('_chotu_debug_request',lambda *args:None)(url,1)
        if response is None:
            self.g['_chotu_backoff'](max(0,self.last+1.5-time.monotonic()),'Website order pacing');self.last=time.monotonic();response=self.g['S'].get(url,timeout=25)
        self.g.get('_chotu_debug_response',lambda *args,**kwargs:None)(response.status_code,len(response.content),cached=cached)
        self.requests+=1
        if response.status_code!=200 or not public_link(self.base,response.url):raise ValueError('Storefront order response/locale unavailable')
        if len(response.content)>5*1024**2:raise ValueError('Storefront order response exceeds verified size limit')
        return BeautifulSoup(response.text,'html.parser')
    def collect(self):
        try:
            robots=self.page(self.base+'/robots.txt')
            # BeautifulSoup.get_text preserves plain robots.txt responses.
            self.robot=RobotFileParser();self.robot.parse(robots.get_text().splitlines())
            home=self.page(self.base+'/');categories=navigation(home,self.base)
            if not categories:raise ValueError('No supported public category navigation found')
            for category in categories:
                current=category['url'];visited=set();position=0;seen_products=set();finished=False;declared_sort=dict(parse_qsl(urlsplit(current).query)).get('sort_by')
                for page_number in range(self.max_pages):
                    if not current or current in visited:break
                    visited.add(current);page=self.page(current);keys=grid_products(page,self.base)
                    if not keys:self.complete=False;break
                    checked=datetime.now(timezone.utc).isoformat()
                    for key in keys:
                        if key in seen_products:continue
                        seen_products.add(key);position+=1
                        self.evidence.setdefault(key,dict(category,product_order=position,source_url=current,checked_at=checked))
                    selected=page.select_one('select[name=sort_by] option[selected], #SortBy option[selected], select[data-sort-by] option[selected]')
                    if selected is not None and declared_sort is None:declared_sort=selected.get('value')
                    following=next_page(page,current)
                    if not following:finished=True;break
                    # Pagination must stay on this exact collection and its declared sort.
                    old,new=urlsplit(category['url']),urlsplit(following)
                    if old.path.rstrip('/')!=new.path.rstrip('/'):self.complete=False;break
                    previous=dict(parse_qsl(old.query));actual=dict(parse_qsl(new.query))
                    if actual.get('sort_by') not in (previous.get('sort_by'),declared_sort):self.complete=False;break
                    stable=lambda query:{k:v for k,v in query.items() if k not in ('page','start','sz','sort_by')}
                    if stable(previous)!=stable(actual):self.complete=False;break
                    current=following
                if not finished:self.complete=False
                self.log('WEBSITE ORDER: '+category['category']+' / '+category['subcategory']+' — '+str(position)+' unique displayed products observed')
            self.log('WEBSITE ORDER CAPTURE: '+str(len(self.evidence))+' product placements; '+('inspected navigation complete' if self.complete else 'bounded/partial capture; unknown positions remain unverified'))
        except Exception as exc:
            self.complete=False;self.log('WEBSITE ORDER UNVERIFIED: '+str(exc)[:220]+'; observed prefix retained, no price/bestseller fallback')
        return self.evidence

def position(value):
    if isinstance(value,bool):return float('inf')
    try:
        n=int(value)
        return n if n>0 and str(n)==str(value).strip() else float('inf')
    except (ValueError,TypeError):return float('inf')

def apply_order(rows,evidence=None):
    """Stable unknown tails; never substitute price, discount, or popularity order."""
    evidence=evidence or {};known=[]
    for row in rows:
        fact=evidence.get(product_key(row.get('source_url','')))
        if fact:
            row.update(category=fact['category'],subcategory=fact['subcategory'],website_category_order=fact['category_order'],website_subcategory_order=fact['subcategory_order'],website_product_order=fact['product_order'],website_order_source_url=fact['source_url'],website_order_checked_at=fact['checked_at'],website_order_status='observed_default_listing')
        else:
            for field in FIELDS:row.setdefault(field,'')
            if not row.get('website_order_status'):row['website_order_status']='unverified'
        valid=all(position(row.get(field))!=float('inf') for field in FIELDS[:3]) and public_link(row.get('source_url',''),row.get('website_order_source_url','')) and row.get('website_order_checked_at')
        if row.get('website_order_status')=='observed_default_listing' and valid:known.append(row)
        else:row['website_order_status']='unverified'
    marker='[Website listing order]'
    for row in rows:
        existing=str(row.get('analysis_note') or '').split(marker,1)[0].rstrip()
        if row.get('website_order_status')=='observed_default_listing':
            detail='Observed default collection listing position '+str(row.get('website_product_order'))+'. Source: '+str(row.get('website_order_source_url'))+'. Checked: '+str(row.get('website_order_checked_at'))+'. Website display order is not verified sales or bestseller rank. Only inspected pages are evidenced; saved-run responses may be cached.'
        else:detail='Website navigation/product position unverified. Original relative order retained among unknown records; no price, discount or bestseller priority substituted.'
        note=(existing+'\n\n' if existing else '')+marker+' '+detail
        if len(note)>32767:raise ValueError('Website-order analysis exceeds Excel cell limit; preserve source notes for review')
        row['analysis_note']=note
    # Membership by object identity avoids quadratic dictionary comparisons on large exports.
    known_ids={id(row) for row in known}
    rows.sort(key=lambda row:tuple(position(row.get(field)) for field in FIELDS[:3]) if id(row) in known_ids else (float('inf'),)*3)
    return known

def enable_website_order(g):
    if g.get('_chotu_website_order'):return
    original=g['_chotuapp_run_site_original']
    def run(base,name,template,log):
        tls=g['_chotu_tls'];tls.website_order_evidence={};tls.website_order_complete=False
        g.get('_chotu_debug_stage',lambda stage:None)('Website listing order')
        host=(urlsplit(base).hostname or '').lower().removeprefix('www.')
        if host not in ('pk.khaadi.com','khaadi.com','sapphireonline.pk','pk.sapphireonline.pk'):
            capture=Capture(g,base,log);tls.website_order_evidence=capture.collect();tls.website_order_complete=capture.complete
        old=g['verified_top20']
        def no_forced_sort(*args,**kwargs):
            tls.ranking_evidence={};log('WEBSITE ORDER POLICY: default storefront order; forced bestseller and cheapest-first sorts disabled');return []
        g['verified_top20']=no_forced_sort
        try:return original(base,name,template,log)
        finally:g['verified_top20']=old
    g['_chotuapp_run_site_original']=run;g['_chotu_website_order']=True
