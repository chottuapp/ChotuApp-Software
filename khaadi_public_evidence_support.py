"""Inspect Khaadi public product evidence; not a complete variant/export adapter."""
import json
from decimal import Decimal,InvalidOperation
from urllib.parse import urljoin,urlsplit
from bs4 import BeautifulSoup
BASE='https://pk.khaadi.com'
def public_product_evidence(html,url):
    requested=urlsplit(url)
    if requested.scheme!='https' or requested.hostname!='pk.khaadi.com':raise ValueError('Pakistan product URL required')
    soup=BeautifulSoup(html,'html.parser');canonical=soup.select_one('link[rel="canonical"]')
    if canonical is None:raise ValueError('Canonical public product URL missing')
    canonical=urljoin(BASE,canonical.get('href',''))
    if urlsplit(canonical).hostname!='pk.khaadi.com' or urlsplit(canonical).path!=requested.path:raise ValueError('Canonical product identity mismatch')
    identity=requested.path.rsplit('/',1)[-1].removesuffix('.html');matches=[]
    for script in soup.find_all('script',type='application/ld+json'):
        try:obj=json.loads(script.get_text())
        except (ValueError,TypeError):continue
        if isinstance(obj,dict) and obj.get('@type')=='Product' and obj.get('sku')==identity:matches.append(obj)
    if len(matches)!=1:raise ValueError('Exact public product JSON-LD missing or ambiguous')
    product=matches[0];offer=product.get('offers')
    if not isinstance(offer,dict) or offer.get('priceCurrency')!='PKR':raise ValueError('Explicit Pakistan price unavailable')
    if urlsplit(urljoin(BASE,offer.get('url',''))).path!=requested.path:raise ValueError('Offer belongs to a different product')
    try:price=Decimal(str(offer['price']))
    except (KeyError,InvalidOperation):raise ValueError('Invalid public product price')
    if not price.is_finite() or price<=0:raise ValueError('Invalid public product price')
    scopes=[x for x in soup.select('.set-item[data-pid]') if x.get('data-pid')==identity]
    if len(scopes)!=1:raise ValueError('Exact main product scope missing or ambiguous')
    sizes=[]
    for node in scopes[0].select('[data-attr="size"] input.options-select'):
        label=node.parent.select_one('span');value=node.get('data-attr-value')
        if node.get('data-pid')!=identity:raise ValueError('Size belongs to another product')
        if value and label:sizes.append({'source_value':value,'label':label.get_text(' ',strip=True),'price':None,'available':None})
    if len({x['source_value'] for x in sizes})!=len(sizes):raise ValueError('Duplicate size identity')
    images=[urljoin(BASE,x) for x in product.get('image',[]) if isinstance(x,str)]
    if not all(urlsplit(x).scheme=='https' and urlsplit(x).hostname=='pk.khaadi.com' for x in images):raise ValueError('Unexpected image host')
    return {'product_id':identity,'name':product.get('name'),'source_url':canonical,'description':product.get('description'),'product_price_pkr':str(price),'product_availability_statement':offer.get('availability'),'sizes':sizes,'images':images,'website_breadcrumbs':[x.get_text(' ',strip=True) for x in soup.select('.breadcrumb a')], 'variant_data_verified':False,'import_ready':False,'issues':['Public offer is product-level; exact per-size price and stock unverified. Matching outfit components are excluded.']}
