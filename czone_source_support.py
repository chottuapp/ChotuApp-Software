"""Czone Webx adapter. Uses public product pages; never Shopify endpoints.
Unknown variants, mismatched prices and incomplete catalogs fail before publication.
"""
import csv, hashlib, json, re, time
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.parse import urlsplit, urljoin
from xml.etree import ElementTree
from bs4 import BeautifulSoup

BASE='https://www.czone.com.pk'
STATIC={'/','/products','/contact','/blog','/about-us','/privacy-policy','/return-exchange','/pc-builder'}


def canonical(url):
    p=urlsplit(urljoin(BASE+'/',url))
    if (p.hostname or '').lower() not in ('czone.com.pk','www.czone.com.pk'):
        raise ValueError('Czone source points to another website')
    return BASE+p.path.rstrip('/')


def nuxt(soup):
    tag=soup.select_one('#__NUXT_DATA__')
    if not tag:raise ValueError('Czone public product state missing')
    values=json.loads(tag.string or tag.get_text())
    if not isinstance(values,list):raise ValueError('Unsupported Webx state')
    def decode(value,stack=()):
        if isinstance(value,bool):return value
        if isinstance(value,int):
            if value<0:return None
            if value>=len(values) or value in stack:raise ValueError('Invalid/cyclic Webx state reference')
            return decode(values[value],stack+(value,))
        if isinstance(value,dict):return {k:decode(v,stack) for k,v in value.items()}
        if isinstance(value,list):return [decode(v,stack) for v in value]
        return value
    return values,decode


def structured(soup,kind):
    found=[]
    def walk(obj):
        if isinstance(obj,list):
            for value in obj:walk(value)
        elif isinstance(obj,dict):
            typ=obj.get('@type',[]);typ=[typ] if isinstance(typ,str) else typ
            if kind in typ:found.append(obj)
            if '@graph' in obj:walk(obj['@graph'])
    for tag in soup.select('script[type="application/ld+json"]'):
        try:walk(json.loads(tag.string or tag.get_text()))
        except ValueError:continue
    return found


def amount(value):
    try:v=Decimal(str(value).replace(',',''))
    except InvalidOperation:raise ValueError('Invalid source price')
    if not v.is_finite() or v<0:raise ValueError('Invalid source price')
    return v


def catalog(html,sitemap):
    soup=BeautifulSoup(html,'html.parser');values,decode=nuxt(soup)
    categories={canonical(decode(obj['url'])) for obj in values if isinstance(obj,dict) and 'categoryID' in obj and 'url' in obj}
    text=soup.get_text(' ',strip=True);match=re.search(r'([\d,]+)\s+Products\b',text)
    if not match:raise ValueError('Czone public catalog total missing')
    total=int(match[1].replace(',',''))
    urls=set()
    for node in ElementTree.fromstring(sitemap).iter():
        if node.tag.rsplit('}',1)[-1]=='loc' and node.text:
            try:url=canonical(node.text)
            except ValueError:continue
            path=urlsplit(url).path
            if url not in categories and path not in STATIC and not path.startswith('/blog/'):urls.add(url)
    for col in structured(soup,'CollectionPage'):
        for item in col.get('mainEntity',{}).get('itemListElement',[]):
            if item.get('url'):urls.add(canonical(item['url']))
    if not total or not urls:raise ValueError('Empty Czone catalog; existing export retained')
    return total,urls,categories


def parse_product(html,url):
    soup=BeautifulSoup(html,'html.parser');values,decode=nuxt(soup)
    objects=[decode(obj) for obj in values if isinstance(obj,dict) and 'productID' in obj and 'productPrice' in obj]
    if len(objects)!=1:raise ValueError('Expected exactly one primary Webx product')
    p=objects[0]
    if canonical(p['productURL'])!=canonical(url):raise ValueError('Product identity/URL mismatch')
    if p.get('productVariants') or p.get('productOptions') or str(p.get('isVariant','0'))!='0':
        raise ValueError('Webx variant schema needs verification; no variants silently omitted: '+url)
    schemas=structured(soup,'Product')
    if len(schemas)!=1:raise ValueError('Primary product structured data missing/ambiguous')
    schema=schemas[0];offer=schema.get('offers')
    if not isinstance(offer,dict) or offer.get('@type')!='Offer':raise ValueError('Unsupported product offer')
    if canonical(offer.get('url',''))!=canonical(url):raise ValueError('Offer belongs to another product')
    if offer.get('priceCurrency')!='PKR':raise ValueError('Non-PKR source price')
    price=amount(p['productPrice']['price'])
    if price!=amount(offer['price']):raise ValueError('Product-state and structured-data prices disagree')
    visible=soup.select_one('.wx-product-info-item-price .wx-product-price')
    if not visible:raise ValueError('Product-specific displayed price missing')
    match=re.search(r'Rs\.?\s*([\d,]+(?:\.\d+)?)',visible.get_text(' ',strip=True))
    if not match or amount(match[1])!=price:raise ValueError('Displayed and structured product prices disagree')
    if str(p['productPrice'].get('isHidePrice','0'))!='0':raise ValueError('Source hides this product price')
    condition=offer.get('itemCondition','').rsplit('/',1)[-1]
    if condition not in ('NewCondition','UsedCondition'):raise ValueError('Unknown source product condition')
    stock=p.get('productStock',{});state=str(stock.get('stockStatus','')).lower()
    availability=offer.get('availability','').rsplit('/',1)[-1]
    if state=='instock' and availability=='InStock':available=True
    elif state in ('outofstock','outstock','out-of-stock') or availability=='OutOfStock':available=False
    elif availability in ('PreOrder','BackOrder') or 'order' in state:available=False
    else:raise ValueError('Unknown source stock state: '+state+'/'+availability)
    fields=p.get('productFields',{});body=[]
    def add(value):
        if value:
            text=BeautifulSoup(str(value),'html.parser').get_text('\n',strip=True)
            if text and text not in body:body.append(text)
    add(p.get('productDesc'));add(str(p.get('productHighlights') or '').replace('_','\n'))
    # Scoped detail panels and source content; exclude store-wide shipping / returns / footer copy.
    for selector in ('.wx-product-overview','.wx-product-specifications','.wx-product-content'):
        for tag in soup.select(selector):add(str(tag))
    for obj in values:
        if isinstance(obj,dict):
            for key,value in obj.items():
                if key=='product-overview-'+str(p['productID']):
                    overview=decode(value)
                    if isinstance(overview,str):add(overview)
                    elif isinstance(overview,dict):
                        for key in ('content','productContent','description','specifications','html'):
                            if isinstance(overview.get(key),str):add(overview[key])
    if fields.get('customFields'):add('Specifications:\n'+json.dumps(fields['customFields'],ensure_ascii=False))
    if fields.get('warranty'):add('Warranty: '+fields['warranty'])
    if p.get('productNote'):add(p['productNote'])
    desc='\n\n'.join(body)
    if str(p.get('isSpecification','0'))=='1' and not soup.select('.wx-product-specifications, [class*="specification"] table, .wx-product-content table') and not fields.get('customFields'):
        raise ValueError('Czone technical specifications require rendered-page verification: '+url)
    if not desc:desc=p['productName']
    if len(desc)>32767:raise ValueError('Description exceeds Excel cell limit; no truncation performed')
    images=[]
    for image in sorted(p.get('productImages') or [],key=lambda x:(str(x.get('isMain'))!='1',int(x.get('priority') or 0))):
        if image.get('mediaType')=='image' and image.get('imageFile') and image['imageFile'] not in images:images.append(image['imageFile'])
    if p.get('imageFile'):
        if p['imageFile'] in images:images.remove(p['imageFile'])
        images.insert(0,p['imageFile'])
    if not images:raise ValueError('Product gallery missing')
    crumbs=structured(soup,'BreadcrumbList');cats=[]
    if crumbs:
        for crumb in crumbs[0].get('itemListElement',[]):
            if crumb.get('name') not in ('Home','Products',p['productName']):cats.append(crumb.get('name'))
    compare=amount(p['productPrice'].get('listPrice') or 0)
    if compare<=price:compare=price
    # Use source-reported sales only; never infer best sellers from price or copy.
    sold=int(stock.get('soldQuantity') or 0)
    return dict(id=str(p['productID']),name=p['productName'],description=desc,sku=fields.get('sku',''),brand=fields.get('vendorName',''),category=cats[0] if cats else fields.get('categoryName','Electronics'),subcategory=cats[-1] if len(cats)>1 else '',price=price,base=compare,available=available,images=images,url=canonical(url),warranty=fields.get('warranty',''),sold=sold,condition='used' if condition=='UsedCondition' else 'new')


def browser_catalog(expected,pause,log):
    """Follow the public site's actual infinite-scroll UI; no guessed private API."""
    from playwright.sync_api import sync_playwright
    with sync_playwright() as driver:
        browser=driver.chromium.launch(headless=True)
        try:
            page=browser.new_page();limited=[]
            page.on('response',lambda response: limited.append(response.status) if response.status in (429,503) else None)
            page.goto(BASE+'/products',wait_until='networkidle',timeout=90000)
            found=set();stagnant=0
            for step in range(max(100,expected//5+30)):
                pause()
                if limited:raise RuntimeError('Czone browser source rate-limited; stop and retry the saved run later')
                urls=page.eval_on_selector_all('.wx-listing-product-wrapper .listing-grid a[href]', '(nodes) => nodes.map(n => n.href)')
                before=len(found)
                for url in urls:
                    try:found.add(canonical(url))
                    except ValueError:continue
                page.evaluate('''() => { const grid = document.querySelector('.wx-listing-product-wrapper'); if (grid) { grid.scrollIntoView({block: 'end'}); window.scrollBy(0, 180); } else { window.scrollTo(0, document.body.scrollHeight); } }''')
                page.wait_for_timeout(1200)
                stagnant=stagnant+1 if len(found)==before else 0
                if step%20==0:log('CZONE: browser loading catalog, pass '+str(step+1))
                if stagnant>=8:break
            return found
        finally:browser.close()


def export(g,base,name,template,log):
    # Reuse the app's gated, checkpoint-aware HTTP session on the fetch thread.
    def get(url):
        g['_chotu_wait']();response=g['S'].get(url,timeout=45);response.raise_for_status();return response.content
    total,urls,categories=catalog(get(BASE+'/products'),get(BASE+'/sitemap.xml'))
    log('CZONE: public catalog '+str(total)+' products; sitemap candidates '+str(len(urls)))
    if len(urls)<total:
        urls.update(u for u in browser_catalog(total,g['_chotu_wait'],log) if u not in categories and urlsplit(u).path not in STATIC and not urlsplit(u).path.startswith('/blog/'))
    records={};nonproducts=0
    for index,url in enumerate(sorted(urls),1):
        html=get(url)
        if not structured(BeautifulSoup(html,'html.parser'),'Product'):
            nonproducts+=1;continue
        product=parse_product(html,url)
        if product['id'] in records and records[product['id']]!=product:raise RuntimeError('Conflicting duplicate Czone product identity')
        records[product['id']]=product
        if index%25==0:
            log('CZONE: checked '+str(index)+'/'+str(len(urls))+' product pages')
            log('__CHOTU_PROGRESS__|'+str(min(65,5+int(60*index/len(urls))))+'|Checking Czone products')
    if len(records)!=total:raise RuntimeError('CZONE catalog incomplete: website '+str(total)+', verified '+str(len(records))+'. Saved responses retained; existing Excel preserved.')
    products=[p for p in records.values() if p['available'] and p['price']>0 and not re.search(r'\bfree gift\b',p['name'],re.I)]
    if not products:raise RuntimeError('No in-stock priced Czone products; existing Excel retained')
    products.sort(key=lambda p:(0 if p['base']>p['price'] else 1,-p['sold'],-(p['base']-p['price'])/p['base'],p['name'].casefold()))
    wb=g['load_workbook'](template)
    for sheet in ('Products','Product Images','Option Groups','Options','Variant Combinations'):
        if sheet not in wb.sheetnames:raise RuntimeError('Template missing '+sheet)
        if wb[sheet].max_row>1:wb[sheet].delete_rows(2,wb[sheet].max_row-1)
    rows=[];images=[];combos=[]
    for p in products:
        pid=g['uid']('CP',BASE+'|'+p['id']);sale=float(p['price']) if p['base']>p['price'] else None
        warranty=re.fullmatch(r'\s*(\d+)\s*-?\s*Month\(s\) Warranty\s*',p['warranty'],re.I)
        row={'product_id':pid,'category':p['category'],'subcategory':p['subcategory'],'name':p['name'],'description':p['description'],'brand':p['brand'],'condition (new/used)':p['condition'],'warranty_months (agar ho)':int(warranty[1]) if warranty else '', 'base_price (PKR)':float(p['base']),'sale_price (PKR, agar discount ho)':sale,'sku':p['sku'],'scraped_image_url (cover, auto)':p['images'][0],'final_image_url (cover/thumbnail — hosted link)':'','option_groups':'','available (yes/no)':'yes','source_url':p['url'],'gallery_urls (extra photos, separate with |)':'|'.join(p['images'])}
        rows.append(row);g['write_row'](wb['Products'],row)
        combo={'combination_id':g['uid']('CC',BASE+'|'+p['id']),'product_id':pid,'source_variant_id':p['id'],'sku':p['sku'],'base_price (PKR)':float(p['base']),'sale_price (PKR, agar discount ho)':sale,'available (yes/no)':'yes','variant_image_url':p['images'][0],'source_url':p['url']}
        combos.append(combo);g['write_row'](wb['Variant Combinations'],combo)
        for i,url in enumerate(p['images'],1):
            image={'image_id':g['uid']('CI',pid+'|'+str(i)),'product_id':pid,'image_order':i,'scraped_image_url (auto)':url,'is_primary (yes/no)':'yes' if i==1 else 'no','source_url':p['url']}
            images.append(image);g['write_row'](wb['Product Images'],image)
    safe=re.sub(r'[^\w .-]','',name).strip() or 'Computer Zone';out=g['OUT'];out.mkdir(parents=True,exist_ok=True)
    tmp=out/(safe+' - BUILDING.xlsx');target=out/(safe+' - REFRESH REVIEW.xlsx')
    wb.save(tmp);wb.close();check=g['load_workbook'](tmp,read_only=True)
    assert check['Products'].max_row==len(products)+1;check.close();tmp.replace(target)
    def report(suffix,headers,data):
        with (out/(safe+' - '+suffix+'.csv')).open('w',encoding='utf-8-sig',newline='') as f:
            writer=csv.writer(f);writer.writerow(headers);writer.writerows(data)
    report('PRICE AUDIT',['product_url','status','detail'],[(p['url'],'MATCH','Webx state, JSON-LD and displayed price agree') for p in products])
    report('STOREFRONT AUDIT',['product_url','status','detail'],[(p['url'],'MATCH','Product-specific displayed PKR price verified') for p in products])
    report('IMAGE AUDIT',['product_url','status','cover_url','detail'],[(p['url'],'MATCH',p['images'][0],'Public product gallery; main image first') for p in products])
    # The outer finalizer reads this order; soldQuantity is a public source field, not independent sales proof.
    report('BEST SELLERS',['rank','product_id','name','category','source_url'],[(i,r['product_id'],r['name'],r['category'],r['source_url']) for i,r in enumerate(rows,1)])
    report('CHANGE REPORT',['change','product_url','field','detail'],[('REFRESHED',p['url'],'','Czone public source') for p in products])
    report('QUALITY REPORT',['severity','issue_code','source_url','detail'],[('WARNING','CZONE_SOURCE_REVIEW',BASE,'Webx adapter; source-reported soldQuantity ordering is not independent sales verification. Import requires review. Unknown variant schemas stop extraction.')])
    log('EXPORT BUILT: '+str(len(products))+' products; '+str(total-len(products))+' unavailable/unpriced/promotional products excluded')
    log('CZONE: prices verified against product state, JSON-LD and displayed price. Source-reported sales order; no invented ranking.')
    log('FILE: '+str(target))


def enable_czone_source(g):
    if g.get('_chotu_czone_source'):return
    original=g['_chotuapp_run_site_original']
    def run(base,name,template,log):
        host=(urlsplit(base).hostname or '').lower().removeprefix('www.')
        if host!='czone.com.pk':return original(base,name,template,log)
        return export(g,BASE,name,template,log)
    g['_chotuapp_run_site_original']=run;g['_chotu_czone_source']=True
