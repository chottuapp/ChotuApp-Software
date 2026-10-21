"""LAAM's public Nuxt catalog; preserve observed variants and explicit PKR only."""
import csv,json,re,time,hashlib,sqlite3,zlib
from pathlib import Path
from decimal import Decimal,InvalidOperation
from urllib.parse import urlsplit,urljoin,unquote
from urllib.robotparser import RobotFileParser
from xml.etree import ElementTree as ET
from bs4 import BeautifulSoup,SoupStrainer
BASE='https://laam.com'
AGENT='ChotuAppCatalogRefresh'

class TemporaryProductError(RuntimeError):
    """A retryable page failure; never a missing or successfully exported product."""

class ConfirmedOutOfStock(ValueError):
    """An explicit empty, zero-inventory public product, never an invented variant."""

class SourceAccessError(ValueError):
    """Public source access/locale cannot be verified; distinct from parser failures."""


class HiddenProduct(ValueError):
    """Explicitly hidden, draft or archived LAAM product; never exported."""

class OutsideClothingScope(ValueError):
    """Not confirmed clothing under the requested LAAM clothing-only scope."""

def is_clothing(raw):
    category=str(raw.get('node_l2') or '').strip().casefold()
    if category:return category=='clothing'
    soup=BeautifulSoup(raw.get('description') or '', 'html.parser')
    for label in soup.find_all('strong'):
        if label.get_text(' ',strip=True).replace('\xa0',' ').strip().rstrip(':').strip().casefold()=='category':
            value=''.join(str(n) for n in label.next_siblings)
            return BeautifulSoup(value,'html.parser').get_text(' ',strip=True).casefold()=='clothing'
    return False

def require_active(raw):
    status=str(raw.get('status') or '').lower()
    if status not in ('active','draft','archived'):raise ValueError('LAAM publication status unverified')
    if status!='active' or any(raw.get(k) is True for k in ('hidden','is_hidden')) or any(raw.get(k) is False for k in ('visible','is_visible','published','is_published')) or str(raw.get('visibility') or '').lower() in ('hidden','private','unlisted'):
        raise HiddenProduct('LAAM product explicitly hidden, unpublished or inactive')

def product_state(soup,handle,clothing_only=False,active_only=False,in_stock_only=False):
    script=soup.find('script',id='__NUXT_DATA__')
    if script is None:raise ValueError('LAAM public product state missing')
    flat=json.loads(script.string or script.get_text())
    if not isinstance(flat,list):raise ValueError('Unexpected LAAM state format')
    def decode(index,seen=frozenset(),depth=0):
        if not isinstance(index,int) or isinstance(index,bool):return index
        if index<0 or index>=len(flat) or index in seen or depth>24:return None
        value=flat[index];seen=seen|{index}
        if isinstance(value,dict):return {k:decode(v,seen,depth+1) for k,v in value.items()}
        if isinstance(value,list):
            if value and value[0] in ('Ref','ShallowRef','Reactive','ShallowReactive'):return decode(value[1],seen,depth+1) if len(value)>1 else None
            return [decode(v,seen,depth+1) for v in value]
        return value
    candidates=[]
    for raw in flat:
        if not isinstance(raw,dict) or not {'handle','description','variants','options','status'}<=set(raw):continue
        if decode(raw['handle'])!=handle:continue
        value={k:decode(v) for k,v in raw.items()};candidates.append(value)
    if len(candidates)!=1:raise ValueError('LAAM exact product state is missing or ambiguous')
    if active_only:require_active(candidates[0])
    currencies=set()
    for tag in soup.find_all('script',type='application/ld+json'):
        try:tree=json.loads(tag.string or tag.get_text())
        except (ValueError,TypeError):continue
        def walk(value):
            if isinstance(value,dict):
                if value.get('@type') in ('Product','ProductGroup'):
                    offers=value.get('offers',[]);offers=offers if isinstance(offers,list) else [offers]
                    currencies.update(str(o['priceCurrency']).upper() for o in offers if isinstance(o,dict) and o.get('priceCurrency'))
                for item in value.values():walk(item)
            elif isinstance(value,list):
                for item in value:walk(item)
        walk(tree)
    if currencies!={'PKR'}:raise SourceAccessError('LAAM Pakistan currency unverified; no foreign price export')
    if clothing_only and not is_clothing(candidates[0]):raise OutsideClothingScope('Not source-confirmed clothing')
    product=normalize(candidates[0],handle,active_only=active_only,in_stock_only=in_stock_only)
    from website_category_support import breadcrumb
    product['_website_category_evidence']=breadcrumb(soup,BASE+'/products/'+handle)
    return product

def normalize(raw,handle,active_only=False,in_stock_only=False):
    if raw.get('handle')!=handle or raw.get('id') is None or not raw.get('title'):raise ValueError('Incomplete LAAM identity')
    if str(raw.get('status') or '').lower() not in ('active','draft','archived'):raise ValueError('LAAM publication status unverified')
    if active_only:require_active(raw)
    options=raw.get('options');variants=raw.get('variants')
    if variants==[] and str(raw.get('stock_status') or '').lower() in ('out-of-stock','sold-out'):
        quantity=raw.get('total_inventory_quantity');stores=raw.get('total_sellable_inventory_on_store')
        if isinstance(quantity,int) and not isinstance(quantity,bool) and quantity==0:
            if stores is not None and (not isinstance(stores,dict) or any(not isinstance(v,int) or isinstance(v,bool) or v!=0 for v in stores.values())):raise ValueError('Conflicting LAAM out-of-stock evidence')
            raise ConfirmedOutOfStock('Explicit out-of-stock product with zero source inventory and no variants')
    if not isinstance(options,list) or len(options)>3 or not isinstance(variants,list) or not variants:raise ValueError('Unsupported LAAM option/variant schema')
    if any(not isinstance(item,dict) for item in options):raise ValueError('Incomplete LAAM option schema')
    positions=[item.get('position') for item in options]
    if any(position is not None for position in positions):
        if any(not isinstance(position,int) or isinstance(position,bool) for position in positions) or set(positions)!=set(range(1,len(options)+1)):
            raise ValueError('LAAM option positions are missing, duplicated or invalid')
        options=sorted(options,key=lambda item:item['position'])
    dims=[]
    for item in options:
        if not isinstance(item,dict) or not item.get('name') or not isinstance(item.get('values'),list):raise ValueError('Incomplete LAAM option values')
        dims.append({'name':str(item['name']),'values':[str(v) for v in item['values']]})
    result=[]
    for variant in variants:
        vid=variant.get('shopify_id') or variant.get('id')
        if vid is None:raise ValueError('LAAM source variant ID missing')
        try:
            price=Decimal(str(variant['price']));compare=Decimal(str(variant['compare_at_price'])) if variant.get('compare_at_price') is not None else None
            if not price.is_finite() or price<0 or compare is not None and (not compare.is_finite() or compare<0):raise ValueError('Invalid LAAM variant price')
        except (KeyError,InvalidOperation):raise ValueError('Unreadable LAAM variant price')
        stock=str(variant.get('stock_status') or '').lower()
        if stock in ('in-stock','limited-stock'):available=True
        elif stock in ('out-of-stock','sold-out'):available=False
        else:raise ValueError('LAAM variant availability unverified')
        row={'id':vid,'title':variant.get('title'),'price':str(price),'compare_at_price':str(compare) if compare is not None else None,'available':available,'sku':variant.get('sku') or ''}
        quantity=variant.get('inventory_quantity')
        if isinstance(quantity,int) and not isinstance(quantity,bool) and quantity>=0:
            row.update(inventory_quantity=quantity,inventory_management='public')
        explicit=[variant.get('option'+str(i)) for i in range(1,len(dims)+1)]
        values=explicit if all(v is not None for v in explicit) else str(variant.get('title') or '').split(' / ') if dims else []
        if len(values)!=len(dims) or any(str(value) not in dim['values'] for value,dim in zip(values,dims)):raise ValueError('LAAM observed variant does not match declared option values')
        row.update({'option'+str(i):str(value) for i,value in enumerate(values,1)})
        image=variant.get('featured_image') or variant.get('image')
        if isinstance(image,dict) and str(image.get('src') or '').startswith('https://'):row['featured_image']={'src':image['src']}
        result.append(row)
    if in_stock_only:
        available=[row for row in result if row['available']]
        if not available:raise ConfirmedOutOfStock('No source-confirmed in-stock variants')
        if str(raw.get('stock_status') or '').lower() in ('out-of-stock','sold-out'):raise ValueError('Conflicting LAAM product and variant availability')
        result=available
        for i,dimension in enumerate(dims,1):dimension['values']=[value for value in dimension['values'] if any(row.get('option'+str(i))==value for row in result)]
    images=[]
    for item in raw.get('media') or []:
        if not isinstance(item,dict) or not str(item.get('src') or '').startswith('https://'):continue
        # LAAM media emits shopify_id=0 on distinct images; position is the export identity.
        images.append({'src':item['src'],'position':len(images)+1,'alt':str(item.get('alt') or '')})
    if not images:raise ValueError('LAAM product gallery unavailable')
    category=next((str(raw[k]) for k in ('node_l4','node_l3','node_l2') if raw.get(k)), '')
    return {'id':raw['id'],'handle':handle,'title':str(raw['title']).strip(),'status':str(raw.get('status') or '').lower(),'body_html':raw.get('description') or '', 'product_type':category,'vendor':raw.get('brand') or '', 'tags':raw.get('tags') or [],'options':dims,'variants':result,'images':images,'image':images[0],'_source_url':BASE+'/products/'+handle}

class ParsedProductCache:
    """Derived results belong to one saved run and one exact adapter revision."""
    def __init__(self,path,revision=None):
        from resume_support import configure_response_database
        self.revision=revision or hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
        self.db=sqlite3.connect(path,timeout=30);configure_response_database(self.db)
        self.db.execute('CREATE TABLE IF NOT EXISTS parsed_products(url TEXT PRIMARY KEY,revision TEXT NOT NULL,payload BLOB NOT NULL,checksum TEXT NOT NULL)')
        self.db.execute('CREATE TABLE IF NOT EXISTS temporary_failures(url TEXT PRIMARY KEY,retry_after REAL NOT NULL)');self.db.commit()
    def get(self,url):
        row=self.db.execute('SELECT payload,checksum FROM parsed_products WHERE url=? AND revision=?',(url,self.revision)).fetchone()
        if row is None:return None
        body,checksum=row
        try:
            if hashlib.sha256(body).hexdigest()!=checksum:raise ValueError('Cache checksum mismatch')
            decoder=zlib.decompressobj();raw=decoder.decompress(body,20*1024**2)
            if not decoder.eof or decoder.unused_data:raise ValueError('Invalid parsed product cache')
            product=json.loads(raw)
            if not isinstance(product,dict) or product.get('_source_url')!=url or not isinstance(product.get('variants'),list):raise ValueError('Invalid parsed product identity')
            return product
        except (ValueError,TypeError,zlib.error):
            self.db.execute('DELETE FROM parsed_products WHERE url=?',(url,));self.db.commit();return None
    def put(self,url,product):
        body=zlib.compress(json.dumps(product,ensure_ascii=True,separators=(',',':')).encode(),1)
        self.db.execute('INSERT OR REPLACE INTO parsed_products VALUES(?,?,?,?)',(url,self.revision,body,hashlib.sha256(body).hexdigest()));self.db.commit()
    def defer(self,url,seconds=3600):
        self.db.execute('INSERT OR REPLACE INTO temporary_failures VALUES(?,?)',(url,time.time()+seconds));self.db.commit()
    def cooling(self,url):
        row=self.db.execute('SELECT retry_after FROM temporary_failures WHERE url=?',(url,)).fetchone()
        return bool(row and 0<row[0]-time.time()<=3600)
    def clear_deferred(self,url):
        self.db.execute('DELETE FROM temporary_failures WHERE url=?',(url,));self.db.commit()
    def close(self):self.db.close()

class PublicCatalog:
    def __init__(self,g,log):
        self.g=g;self.log=log;self.robots=None;self.last=0;self.products={};self.cache=None;self.cache_hits=0
        path=getattr(g.get('_chotu_tls'),'saved_api_path',None)
        if path:self.cache=ParsedProductCache(Path(path).with_name('laam-parsed.sqlite3'))
    def close(self):
        if self.cache:self.cache.close();self.cache=None
    def read(self,url,allow_missing=False,fresh=False):
        p=urlsplit(url)
        if p.scheme!='https' or p.hostname!='laam.com' or p.username or p.password or p.port not in (None,443):raise SourceAccessError('LAAM public source changed host')
        if self.robots and not self.robots.can_fetch(AGENT,url):raise SourceAccessError('LAAM source path disallowed by robots')
        self.g['_chotu_wait']()
        cache=getattr(self.g.get('_chotu_tls'),'saved_response_cache',None)
        response=cache.get(url) if cache and not fresh else None;cached=response is not None
        if not cached:
            self.g['_chotu_backoff'](max(0,self.last+1.5-time.monotonic()),'Public catalog pacing');self.last=time.monotonic()
        self.g['_chotu_debug_request'](url,1)
        if response is None:
            session=self.g['S'];getter=(getattr(session,'get_fresh',None) or session.get) if fresh else session.get
            response=getter(url,timeout=35,allow_redirects=False)
        self.g['_chotu_debug_response'](response.status_code,len(response.content),cached=cached)
        for retry in range(1,1 if allow_missing else 3):
            if response.status_code not in (500,502,504):break
            self.log('LAAM SERVER RETRY: HTTP '+str(response.status_code)+' '+url+'; cooldown 60s; retry '+str(retry)+'/2')
            self.g['_chotu_backoff'](60,'LAAM temporary server cooldown')
            self.g['_chotu_wait']()
            self.g['_chotu_debug_request'](url,retry+1)
            session=self.g['S'];getter=getattr(session,'get_fresh',None) or session.get
            response=getter(url,timeout=35,allow_redirects=False);self.last=time.monotonic()
            self.g['_chotu_debug_response'](response.status_code,len(response.content),cached=False)
        if response.status_code in (500,502,504):
            raise TemporaryProductError('SOURCE PAUSED: LAAM temporary server failure (HTTP '+str(response.status_code)+'); retry saved store after at least 60s. Checkpoint retained')
        if response.status_code in (429,503):
            gate=getattr(self.g.get('_chotu_tls'),'fast_gate',None)
            if gate is not None:raise gate.blocked_error()
            raise RuntimeError('SOURCE PAUSED: LAAM rate limit; checkpoint retained')
        if allow_missing and response.status_code in (404,410):return response
        if response.status_code!=200:raise SourceAccessError('LAAM public source unavailable (HTTP '+str(response.status_code)+'); cached work retained')
        if len(response.content)>20*1024**2:raise ValueError('LAAM source exceeds verified response size limit')
        return response
    def catalog(self):
        robot=self.read(BASE+'/robots.txt');self.robots=RobotFileParser();self.robots.parse(robot.text.splitlines())
        maps=list(dict.fromkeys(re.findall(r'(?im)^Sitemap:\s*(https://\S+)',robot.text)))
        if not maps:raise ValueError('LAAM declared sitemap missing')
        queue=list(maps);seen=set();urls=set()
        while queue:
            url=queue.pop(0)
            if url in seen:continue
            if len(seen)>=100:raise ValueError('LAAM sitemap coverage limit reached; catalog incomplete')
            seen.add(url);tree=ET.fromstring(self.read(url).content);local=lambda tag:tag.rsplit('}',1)[-1]
            if local(tree.tag)=='sitemapindex':
                queue.extend((node.text or '').strip() for node in tree.iter() if local(node.tag)=='loc');continue
            if local(tree.tag)!='urlset':raise ValueError('Unknown LAAM sitemap format')
            for node in tree:
                if local(node.tag)!='url':continue
                loc=next(((child.text or '').strip() for child in node if local(child.tag)=='loc'),'')
                p=urlsplit(loc)
                if p.hostname=='laam.com' and re.fullmatch('/products/[^/]+',p.path) and not p.query:urls.add(loc)
            self.log('LAAM SITEMAP: '+str(len(urls))+' distinct public product URLs discovered')
        if not urls:raise ValueError('LAAM sitemap has no public product URLs')
        deferred=[];consecutive=0
        for index,url in enumerate(sorted(urls),1):
            self.g.get('_chotu_wait',lambda:None)()
            if index==1 or (index-1)%50==0:self.log(f'PUBLIC PRODUCT PAGES: {index-1}/{len(urls)} LAAM pages inspected; {len(self.products)} clothing products retained; {len(deferred)} pages deferred')
            if self.cache and self.cache.cooling(url):
                deferred.append(url);continue
            product=self.cache.get(url) if self.cache else None
            if product is not None and product.get('_excluded_reason'):continue
            if product is not None:self.cache_hits+=1
            else:
                handle=unquote(urlsplit(url).path.rsplit('/',1)[-1])
                try:response=self.read(url,allow_missing=True)
                except TemporaryProductError:
                    deferred.append(url);consecutive+=1
                    if self.cache:self.cache.defer(url)
                    self.log('LAAM PRODUCT DEFERRED: '+url+'; temporary server failure, not exported or marked complete')
                    if consecutive>=5:
                        healthy=next(iter(self.products.values()),None)
                        if not healthy:raise TemporaryProductError('SOURCE PAUSED: LAAM consecutive server failures with no verified health sample; checkpoint retained')
                        try:self.read(healthy['_source_url'],fresh=True)
                        except (RuntimeError,ValueError) as health_error:raise TemporaryProductError('SOURCE PAUSED: LAAM product service health check failed; checkpoint retained') from health_error
                        self.log('LAAM HEALTH: verified product URL still responds; failed individual pages deferred while healthy pages continue')
                        consecutive=0
                    continue
                consecutive=0
                if self.cache:self.cache.clear_deferred(url)
                if response.status_code in (404,410):
                    self.log('LAAM SOURCE REMOVED: HTTP '+str(response.status_code)+' '+url+'; absent public product excluded')
                    continue
                # Nuxt state and currency evidence live in scripts; don't build a full page DOM.
                try:product=product_state(BeautifulSoup(response.text,'html.parser',parse_only=SoupStrainer('script')),handle,clothing_only=True,active_only=True,in_stock_only=True)
                except OutsideClothingScope:
                    if self.cache:self.cache.put(url,{'_source_url':url,'variants':[],'_excluded_reason':'not-confirmed-clothing'})
                    self.log('LAAM CLOTHING FILTER: excluded non-clothing or unclassified product '+url)
                    continue
                except HiddenProduct:
                    if self.cache:self.cache.put(url,{'_source_url':url,'variants':[],'_excluded_reason':'hidden-or-inactive'})
                    self.log('LAAM HIDDEN FILTER: excluded hidden/inactive product '+url)
                    continue
                except ConfirmedOutOfStock:
                    if self.cache:self.cache.put(url,{'_source_url':url,'variants':[],'_excluded_reason':'confirmed-out-of-stock'})
                    self.log('LAAM SOURCE OUT OF STOCK: '+url+'; no source-confirmed available variants; unavailable product excluded, no variants invented')
                    continue
                except SourceAccessError:raise
                except (ValueError,TypeError,KeyError) as exc:raise ValueError('Product '+handle+': '+str(exc)) from exc
                if self.cache:self.cache.put(url,product)
            if product['id'] in self.products:raise ValueError('LAAM sitemap returned repeated product identity')
            self.products[product['id']]=product
            if index==1 or index%50==0 or index==len(urls):self.log(f'PUBLIC PRODUCT PAGES: {index}/{len(urls)} LAAM pages inspected; {len(self.products)} clothing products retained')
        if deferred:raise TemporaryProductError('SOURCE PAUSED: LAAM '+str(len(deferred))+' product pages still unavailable; other successful products cached. Retry saved store after at least 60s; catalog incomplete')
        if self.cache_hits:self.log('LAAM PARSED CACHE: '+str(self.cache_hits)+' verified products reused without reparsing; current adapter revision only')
        self.log('LAAM SOURCE: active visible in-stock clothing only; hidden/inactive and out-of-stock products excluded; available source variants only; non-clothing and unclassified excluded; explicit PKR, observed variants, public stock and image URLs retained. No sales popularity assumed.')
        return list(self.products.values()),True

def enable_laam_source(g):
    if g.get('_chotu_laam_source'):return
    original=g['_chotuapp_run_site_original']
    def run(base,name,template,log):
        if (urlsplit(base).hostname or '').lower().removeprefix('www.')!='laam.com':return original(base,name,template,log)
        source=PublicCatalog(g,log)
        replacements={key:g[key] for key in ('discover','collections','refresh_variant_prices','storefront_cover','verified_top20','audit_fractional_prices','storefront_price_audit')}
        def cover(base,p,pictures,log):
            # Gallery comes from the exact product page, but hero ordering is not independently verified.
            g['_chotu_tls'].image_audit.append([p['_source_url'],'REVIEW',pictures[0]['src'] if pictures else '','Exact public product gallery retained; visual hero unverified'])
            return None
        def audit(base,rows,combos,output,log):
            with output.open('w',encoding='utf-8-sig',newline='') as handle:
                writer=csv.writer(handle);writer.writerow(['status','product_url','detail']);writer.writerow(['REVIEW',BASE,'Prices and variants extracted from exact PKR product page state; independent live price/checkout validation unavailable'])
            log('PRICE AUDIT: '+str(output)+' (REVIEW=1, MISMATCH=0; same-page source validation only)')
        def display(rows,output,log):
            with output.open('w',encoding='utf-8-sig',newline='') as handle:
                writer=csv.writer(handle);writer.writerow(['status','product_url','detail']);writer.writerow(['REVIEW',BASE,'Visual storefront/checkout price not independently verified'])
            log('STOREFRONT AUDIT: '+str(output)+' (REVIEW required)');return set()
        def ranking(base,log,*args,**kwargs):
            g['_chotu_tls'].ranking_evidence={};log('TOP 20: UNVERIFIED — LAAM verified sales ordering unavailable; no guessed popularity');return []
        g.update(discover=lambda base,log:source.catalog(),collections=lambda base,log:{},refresh_variant_prices=lambda base,p,log:p['variants'],storefront_cover=cover,verified_top20=ranking,audit_fractional_prices=audit,storefront_price_audit=display)
        try:return original(BASE,name,template,log)
        except SourceAccessError as exc:raise RuntimeError('SOURCE BLOCKED: '+str(exc)) from exc
        except (ValueError,TypeError,KeyError) as exc:raise RuntimeError('ADAPTER ERROR: LAAM '+str(exc)+'. Saved responses retained; no options, prices or stock guessed.') from exc
        finally:
            source.close();g.update(replacements)
    g['_chotuapp_run_site_original']=run;g['_chotu_laam_source']=True
