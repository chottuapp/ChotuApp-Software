"""Strict source categories: observed navigation membership or product breadcrumbs only."""
import json,re
from datetime import datetime,timezone
from urllib.parse import urlsplit
FIELDS=('website_category_path','website_category_source_url','website_category_checked_at','website_category_status')
PROMOTIONAL=re.compile(r'^(?:home(?: page)?|all(?: products| collections)?|shop(?: all| now)?|catalog(?:ue)?|collections?|products?|sale|sales|clearance|deals?|offers?|featured(?: products)?|new(?: in| arrivals?)?|best[ -]?sell(?:ers?|ing)|top[ -]?sell(?:ers?|ing)|trending|under\s+(?:rs\.?|pkr)?\s*[\d,]+|in stock feed|uncategorized)$',re.I)
def substantive(label):
    label=str(label or '').strip()
    return bool(label) and not PROMOTIONAL.fullmatch(label) and not re.search(r'(?i)\b(?:sales?|clearance|discounts?|new arrivals?|featured products|best[ -]?sellers?|trending)\b',label)
def fact(path,url,status):
    path=[str(p).strip() for p in path if str(p).strip()]
    if not path or any(not substantive(p) for p in path):return None
    return {'category':path[0],'subcategory':path[-1] if len(path)>1 else '',FIELDS[0]:' > '.join(path),FIELDS[1]:url,FIELDS[2]:datetime.now(timezone.utc).isoformat(),FIELDS[3]:status,'_category_depth':len(path)}
def breadcrumb(soup,url):
    from website_order_support import public_link
    trails=[]
    def accept(items):
        labels=[]
        for label,link in items:
            label=str(label or '').strip();resolved=public_link(url,link) if link else ''
            if not label or not resolved or '/products/' in urlsplit(resolved).path or resolved.rstrip('/')==url.rstrip('/'):continue
            if substantive(label) and urlsplit(resolved).path not in ('','/') and label not in labels:labels.append(label)
        if labels:trails.append(labels)
    for node in soup.select('script[type="application/ld+json"]'):
        try:tree=json.loads(node.string or node.get_text())
        except (ValueError,TypeError):continue
        queue=tree if isinstance(tree,list) else [tree]
        while queue:
            entry=queue.pop(0)
            if not isinstance(entry,dict):continue
            graph=entry.get('@graph',[])
            if isinstance(graph,list):queue.extend(graph)
            if entry.get('@type')!='BreadcrumbList':continue
            elements=entry.get('itemListElement',[])
            if not isinstance(elements,list):continue
            try:elements=sorted(elements,key=lambda e:int(e.get('position',0)))
            except (ValueError,TypeError,AttributeError):continue
            items=[]
            for el in elements:
                if not isinstance(el,dict):continue
                item=el.get('item',{});label=el.get('name') or (item.get('name') if isinstance(item,dict) else '')
                link=item.get('@id') or item.get('url') if isinstance(item,dict) else item
                items.append((label,link))
            accept(items)
    for node in soup.select('nav[aria-label*=readcrumb], .breadcrumb, .breadcrumbs, [itemtype$="BreadcrumbList"]'):
        accept([(a.get_text(' ',strip=True),a.get('href')) for a in node.select('a[href]')])
    unique={tuple(t) for t in trails}
    if len(unique)!=1:return None
    return fact(list(next(iter(unique))),url,'verified_product_breadcrumb')
def choose(current,candidate):
    if not candidate:return current
    if not current:return candidate
    score=lambda x:(x.get(FIELDS[3])=='verified_product_breadcrumb',x.get('_category_depth',1))
    return candidate if score(candidate)>score(current) else current

def navigation_membership(tls,base,get_json,wait,log,max_requests=400):
    """Only actual menu categories, exact labels; API verifies membership, not taxonomy/order."""
    from website_order_support import public_link
    evidence={};mapping={};requests=0
    tls.website_category_evidence=evidence
    for nav in tls.website_category_navigation:
        path=nav.get('category_path') or [nav['category']]+([nav['subcategory']] if nav.get('subcategory') else [])
        if any(not substantive(p) for p in path):continue
        url=public_link(base,nav['url'])
        if not url or not re.fullmatch(r'/collections/[^/]+/?',urlsplit(url).path):continue
        for page in range(1,101):
            endpoint=url.split('?',1)[0].rstrip('/')+'/products.json?limit=250&page='+str(page)
            robots=getattr(tls,'website_category_robot',None)
            if requests>=max_requests or robots is not None and not robots.can_fetch('ChotuAppCatalogRefresh',endpoint):
                log('CATEGORY UNVERIFIED: membership request bound or source robots restriction');return mapping
            wait();requests+=1
            try:
                batch=get_json(endpoint).get('products')
                if not isinstance(batch,list):raise ValueError('Missing collection products')
            except Exception as exc:
                log('CATEGORY UNVERIFIED: menu membership unavailable; no inferred fallback: '+str(exc)[:160]);return mapping
            item=fact(path,endpoint,'verified_navigation_membership')
            for product in batch:
                if not isinstance(product,dict):continue
                pid=product.get('id');handle=product.get('handle')
                if handle:evidence[handle]=choose(evidence.get(handle),item)
                if pid is not None:mapping.setdefault(pid,[]).append(path[-1])
            if len(batch)<250:break
        log('CATEGORY VERIFIED: '+' > '.join(path)+'; observed menu labels and collection membership')
    return mapping

def apply(row,evidence=None):
    from website_order_support import product_key,public_link
    url=row.get('source_url','');candidate=(evidence or {}).get(product_key(url))
    existing={key:row.get(key) for key in ('category','subcategory')+FIELDS}
    # Preserve a full path, including intermediate levels, without flattening/relabeling the source.
    def trustworthy(data):
        if not data or not data.get(FIELDS[0]):return False
        path=str(data[FIELDS[0]]).split(' > ')
        return bool(data.get(FIELDS[3]) in ('verified_navigation_membership','verified_product_breadcrumb') and data.get(FIELDS[1]) and public_link(url,data[FIELDS[1]]) and data.get(FIELDS[2]) and all(substantive(p) for p in path) and data.get('category')==path[0] and ((data.get('subcategory') or '')==(path[-1] if len(path)>1 else '') or len(path)==1 and data.get('subcategory_source')=='website' and data.get('subcategory')==path[0]))
    existing['subcategory_source']=row.get('subcategory_source','')
    existing['_category_depth']=len(str(existing.get(FIELDS[0]) or '').split(' > '))
    selected=choose(existing if trustworthy(existing) else None,candidate if trustworthy(candidate) else None)
    if selected:
        row.update({key:selected.get(key,'') for key in ('category','subcategory')+FIELDS})
    else:
        row.update(category='',subcategory='',**{FIELDS[0]:'',FIELDS[1]:'',FIELDS[2]:'',FIELDS[3]:'unverified'})
    return row
