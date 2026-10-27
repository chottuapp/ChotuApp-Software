"""Keep source product details for all categories, without extra HTTP requests."""
import re
import html
from bs4 import BeautifulSoup

DETAIL_SELECTORS=', '.join([
    'product-info table','.product__info-container table','[id^="ProductInfo"] table',
    '.product__description','[data-product-description]',
    '.product-specifications','#specifications','[data-product-specifications]',
    'product-info .accordion__content','.product__info-container .accordion__content',
    '[id^="ProductInfo"] .accordion__content','[id^="ProductAccordion-"] .accordion__content',
    '.product-tabs .tab-content','.t4s-product-tabs-wrapper .t4s-tab-content',
    '.t4s-product-description'
])
BAD='script, style, noscript, iframe, svg, form, button, nav, product-recommendations, .related-products, .recommendations'

def collect_product_details(soup):
    selected=[];used=set()
    for node in soup.select(DETAIL_SELECTORS):
        if any(id(p) in used for p in node.parents):continue
        ancestry=[node]+list(node.parents)
        if any(re.search(r'recommend|related.product',str(p.get('id',''))+' '+' '.join(p.get('class',[]))+' '+str(p.name),re.I) for p in ancestry):continue
        text=node.get_text(' ',strip=True)
        if not text:continue
        # Standalone policy panels are not product specifications.
        parent=node.find_parent('details')
        summary=parent.find('summary') if parent else None
        if summary and re.match(r'^(shipping|delivery|returns?|refund|payment)\b',summary.get_text(' ',strip=True),re.I):continue
        fragment=BeautifulSoup(str(node),'html.parser')
        for tag in fragment.select(BAD):tag.decompose()
        if fragment.get_text(' ',strip=True):
            heading=summary.get_text(' ',strip=True) if summary else ''
            if not heading and node.get('aria-labelledby'):
                label=soup.find(id=node.get('aria-labelledby'))
                if label:heading=label.get_text(' ',strip=True)
            selected.append(('<h3>'+html.escape(heading)+'</h3>' if heading else '')+str(fragment));used.add(id(node))
    return '\n'.join(selected)


def complete_description(product,txt,detailed_description,debug):
    title=txt(product.get('title'))
    body=(product.get('body_html') or '')+'\n'+(product.get('_storefront_specs_html') or '')
    soup=BeautifulSoup(body,'html.parser')
    for node in soup.select(BAD):node.decompose()
    # Preserve factual sentences even if a separate call to action shares a paragraph.
    for text in list(soup.find_all(string=True)):
        if re.fullmatch(r'\s*(?:add to cart|buy now|shop now|order now|subscribe|share|read more)\s*[!.]?\s*',str(text),re.I):text.extract()
    result=detailed_description(product,soup)
    option_lines=[]
    for i,option in enumerate((product.get('options') or [])[:3],1):
        label=txt(option.get('name')) or f'Option {i}';values=[]
        for variant in product.get('variants') or []:
            value=txt(variant.get('option'+str(i)))
            if value and value not in values:values.append(value)
        if values and not (len(values)==1 and values[0].casefold() in ('default','default title')):
            option_lines.append(label+': '+', '.join(values))
    if option_lines:result+='\n\nProduct Options:\n'+'\n'.join(option_lines)
    if not result.strip():result=title
    if len(result)>32767:
        debug('DESCRIPTION LIMIT: Excel cell maximum reached for '+title+'; review the source for remaining detail.')
        result=result[:32767]
    return result


def collect_maali_plant_details(soup,title,url):
    """Read only identity-matched product care panels; never sitewide nursery copy."""
    from urllib.parse import urlsplit,urljoin
    p=urlsplit(url)
    if p.hostname not in ('hellomaali.com','www.hellomaali.com') or not p.path.startswith('/products/'):return ''
    canonical=soup.select_one('link[rel="canonical"]');titles=soup.select('h1')
    if canonical is None or len(titles)!=1 or titles[0].get_text(' ',strip=True).casefold()!=str(title).strip().casefold():return ''
    c=urlsplit(urljoin(url,canonical.get('href','')))
    if (c.hostname or '').removeprefix('www.')!=(p.hostname or '').removeprefix('www.') or c.path.rstrip('/')!=p.path.rstrip('/'):return ''
    root=titles[0].find_parent(class_=re.compile(r'^maali-prod-wrapper-'))
    if root is None:return ''
    facts={}
    for panel in root.select('[class*="maali-stats-"]'):
        for label in panel.find_all('div'):
            key=label.get_text(' ',strip=True).casefold()
            if key not in ('light','water','size','pet-safe'):continue
            value=label.find_next_sibling('div')
            if value is not None and value.get_text(' ',strip=True):facts[key]=value.get_text(' ',strip=True)
    if not {'light','water'}<=facts.keys():return ''
    lines=['<h3>Live plant care</h3>']
    for key in ('light','water','size','pet-safe'):
        if key in facts:lines.append('<p>'+html.escape({'light':'Light','water':'Watering','size':'Plant size','pet-safe':'Source-listed pet-safe'}[key])+': '+html.escape(facts[key])+'</p>')
    return '\n'.join(lines)
