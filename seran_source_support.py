"""Seran-only public catalog fallback, accepted only with sitemap coverage."""
from urllib.parse import urlsplit,unquote
from xml.etree import ElementTree as ET

HOST='seran.com.pk'


def same_store(url):
    p=urlsplit(url)
    return p.scheme=='https' and p.hostname is not None and p.hostname.lower().removeprefix('www.')==HOST and not p.username and not p.password and p.port in (None,443)


def public_handles(g,base):
    def read(url):
        if not same_store(url):raise ValueError('Seran sitemap references another host')
        g['_chotu_wait']();response=g['S'].get(url,timeout=35)
        if response.status_code in (429,503):
            gate=getattr(g.get('_chotu_tls'),'fast_gate',None)
            if gate is not None:raise gate.blocked_error()
            raise RuntimeError('SOURCE PAUSED: Seran sitemap rate limit; retry this saved store after at least 60s')
        if response.status_code!=200:raise ValueError('Seran sitemap unavailable (HTTP '+str(response.status_code)+')')
        if not same_store(response.url):raise ValueError('Seran sitemap redirected to another source')
        if len(response.content)>20*1024*1024:raise ValueError('Seran sitemap exceeds verified size limit')
        return ET.fromstring(response.content)
    root=read(base+'/sitemap.xml');local=lambda tag:tag.rsplit('}',1)[-1]
    if local(root.tag)=='urlset':roots=[root]
    elif local(root.tag)=='sitemapindex':
        locations=[(n.text or '').strip() for n in root.iter() if local(n.tag)=='loc']
        locations=[url for url in locations if urlsplit(url).path.rsplit('/',1)[-1].startswith('sitemap_products')]
        if not 1<=len(locations)<=50:raise ValueError('Seran product sitemap index missing or too large')
        roots=[read(url) for url in locations]
    else:raise ValueError('Unexpected Seran sitemap format')
    handles=set()
    for root in roots:
        if local(root.tag)!='urlset':raise ValueError('Expected a product sitemap URL list')
        for node in root:
            if local(node.tag)!='url':continue
            loc=next(((child.text or '').strip() for child in node if local(child.tag)=='loc'),'')
            if not same_store(loc):raise ValueError('Product sitemap URL belongs to another source')
            parts=urlsplit(loc).path.strip('/').split('/')
            if len(parts)==2 and parts[0]=='products' and parts[1]:handles.add(unquote(parts[1]))
    if not handles:raise ValueError('Seran product sitemap has no products')
    return handles


def fallback_catalog(g,base,log):
    log('SERAN SOURCE: catalog API denied; checking public all-products collection and sitemap coverage.')
    # Validate the allowed collection source before enumerating any further pages.
    items={};handles=set()
    for page in range(1,101):
        data=g['get_json'](base+'/collections/all/products.json?limit=250&page='+str(page))
        if not isinstance(data,dict) or not isinstance(data.get('products'),list):raise ValueError('Invalid Seran collection product schema')
        batch=data['products']
        for product in batch:
            if not isinstance(product,dict) or product.get('id') is None or not product.get('handle') or not isinstance(product.get('variants'),list) or not product['variants']:
                raise ValueError('Incomplete Seran product schema')
            for variant in product['variants']:
                if not isinstance(variant,dict) or variant.get('id') is None or 'price' not in variant or not isinstance(variant.get('available'),bool):raise ValueError('Incomplete Seran variant schema')
            if product['id'] in items or product['handle'] in handles:raise ValueError('Repeated Seran product in collection pagination')
            items[product['id']]=product;handles.add(product['handle'])
        log('SERAN PUBLIC COLLECTION: page '+str(page)+', '+str(len(batch))+' products')
        if len(batch)<250:break
    else:raise ValueError('Seran collection pagination did not finish')
    if not items:raise ValueError('Seran public collection is empty')
    expected=public_handles(g,base)
    if handles!=expected:raise ValueError('Seran catalog coverage unverified: '+str(len(expected-handles))+' sitemap products missing and '+str(len(handles-expected))+' collection products absent from sitemap')
    log('SERAN SOURCE VERIFIED: '+str(len(items))+' unique products match the public product sitemap; existing price/variant/image checks follow.')
    return list(items.values()),True


def enable_seran_source(g):
    if g.get('_chotu_seran_source'):return
    original=g['discover']
    def discover(base,log):
        if (urlsplit(base).hostname or '').lower().removeprefix('www.')!=HOST:return original(base,log)
        try:return original(base,log)
        except RuntimeError as exc:
            if 'Website endpoint unavailable (403): '+base+'/products.json?' not in str(exc):raise
        try:
            result=fallback_catalog(g,base,log)
            tls=g.get('_chotu_tls')
            if tls is not None:tls.fast_products=result[0]
            return result
        except Exception as exc:
            # Rate-limit state belongs to the existing request gate; don't bypass it.
            if 'SOURCE PAUSED:' in str(exc):raise
            raise RuntimeError('SOURCE BLOCKED: Seran public catalog could not be verified from this server. '+str(exc)+'. Existing Excel and checkpoints retained; use the PC extractor or request source access.') from exc
    g['discover']=discover;g['_chotu_seran_source']=True
