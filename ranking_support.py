"""Evidence-aware catalog merchandising; never infer sales from prices."""
from copy import copy
from decimal import Decimal, InvalidOperation
from urllib.parse import urlsplit
import re
from datetime import datetime, timezone

FIELDS=('category_priority','product_priority','popularity_basis','popularity_source_url','popularity_checked_at','analysis_note')
BEAUTY_HOSTS={'elitecosmeticspk.com','missrose.com.pk','rivaj-uk.com','vincecare.com'}
BEAUTY_CATEGORIES=('makeup','lip','eye','foundation','concealer','blush','primer','mascara','highlighter','skin','face','sun','hair','shampoo','conditioner','body','bath','fragrance','perfume','nail','beauty','serum','toner','cream','lotion','wax','razor','shav','deodorant','personal care')

def ensure_columns(sheet):
    headers=[c.value for c in sheet[1]];changed=False
    for field in FIELDS:
        if field not in headers:
            cell=sheet.cell(1,sheet.max_column+1,field)
            cell._style=copy(sheet.cell(1,cell.column-1)._style)
            headers.append(field);changed=True
    return changed

def category_priority(row):
    host=(urlsplit(row.get('source_url') or '').hostname or '').lower().removeprefix('www.')
    category=str(row.get('category') or '').lower()
    if host in BEAUTY_HOSTS:
        return 1 if any(word in category for word in BEAUTY_CATEGORIES) else 100
    return None

def number(value):
    try:
        result=Decimal(str(value))
        return result if result.is_finite() else None
    except (InvalidOperation,ValueError,TypeError):return None

def payable(row):
    base=number(row.get('base_price (PKR)'));sale=number(row.get('sale_price (PKR, agar discount ho)'))
    if base is None or base<=0:return Decimal('Infinity')
    return sale if sale is not None and 0<sale<base else base

def priority(value):
    n=number(value)
    return n if n is not None and n>0 and n==n.to_integral_value() else Decimal('Infinity')

NOTE_MARKER='[Popularity analysis]'

def evidence_checked_at():
    return datetime.now(timezone.utc).isoformat()

def product_page_evidence(soup,url):
    """Only explicit badges inside product information; never recommendations/navigation."""
    labels=[]
    for node in soup.select('.product__info-container .badge, .product__info .badge, [data-product-info] .badge'):
        text=node.get_text(' ',strip=True)
        if re.fullmatch(r'best[ -]?sellers?|best[ -]?selling|top[ -]?sellers?|top[ -]?selling|hot[ -]?selling|trending|most popular|top rated|featured',text,re.I):
            if text not in labels:labels.append(text)
    if not labels:return ''
    return 'Product-page merchant label: '+', '.join(labels)+'. Source: '+url+'. Checked: '+evidence_checked_at()+'. This is a merchant label, not an independently verified sales count.'

def collection_evidence(title,url,membership_url):
    """A promotional collection membership is a signal, never a verified sales rank."""
    if not re.search(r'(?i)\b(best[ -]?sellers?|best[ -]?selling|top[ -]?(?:selling|sellers?|collections?)|hot[ -]?selling|trending|most popular|customer favou?rites?|featured)\b',str(title)):
        return ''
    return 'Store collection signal: '+str(title)+'. Product membership observed at '+membership_url+'. Collection: '+url+'. Checked: '+evidence_checked_at()+'. Collection title/membership is a merchant signal only; no sales count or bestseller position verified.'


def annotate_analysis(row):
    existing=str(row.get('analysis_note') or '').split(NOTE_MARKER,1)[0].rstrip()
    if row.get('popularity_basis')=='store_bestseller' and row.get('popularity_source_url') and row.get('popularity_checked_at'):
        detail='Verified position '+str(row.get('product_priority'))+' in the inspected store-wide bestseller subset. Source: '+str(row['popularity_source_url'])+'. Evidence checked: '+str(row['popularity_checked_at'])+'. Storefront order is evidence of the displayed best-selling sort, not independently verified sales volume or a category-wide sales rank.'
    else:
        detail='No verified bestseller-order evidence recorded for this product. Only a bounded bestseller subset and recognized product-page labels are inspected; absence of evidence is not proof of low sales. No sales count inferred from price, discount, stock, or alphabetical order.'
    if row.get('category_priority') not in (None,''):
        detail+=' Category priority is manual merchandising, not sales evidence.'
    detail+=' Saved-run evidence may come from cached responses; the check time does not guarantee a fresh network response.'
    result=(existing+'\n\n' if existing else '')+NOTE_MARKER+' '+detail
    if len(result)>32767:raise ValueError('Product analysis_note exceeds Excel cell limit; review evidence before exporting: '+str(row.get('product_id')))
    row['analysis_note']=result


def order_rows(rows, handles=(), evidence=None):
    """Rank verified matches within categories, then payable price; preserve stable ties."""
    evidence=evidence or {};rank={h:i+1 for i,h in enumerate(dict.fromkeys(handles))};ranked=[]
    first_category={};category_keys={}
    for i,row in enumerate(rows):
        cat=str(row.get('category') or '')
        first_category.setdefault(cat,i)
        if row.get('category_priority') in (None,''):row['category_priority']=category_priority(row)
        cp=priority(row.get('category_priority'))
        if cat in category_keys and category_keys[cat]!=cp:raise ValueError('Conflicting category priorities: '+cat)
        category_keys[cat]=cp
        handle=urlsplit(row.get('source_url') or '').path.rstrip('/').rsplit('/',1)[-1]
        fact=evidence.get(handle)
        if handle in rank and fact and fact.get('url') and fact.get('checked_at'):
            row.update(product_priority=rank[handle],popularity_basis='store_bestseller',popularity_source_url=fact['url'],popularity_checked_at=fact['checked_at']);ranked.append(row)
    for row in rows:annotate_analysis(row)
    def key(row):
        cat=str(row.get('category') or '');base=number(row.get('base_price (PKR)'));price=payable(row)
        discount=(base-price)/base if base is not None and base>0 and price.is_finite() else Decimal(0)
        return category_keys[cat],first_category[cat],priority(row.get('product_priority')),price,-discount
    rows.sort(key=key)
    return sorted(ranked,key=lambda row:priority(row.get('product_priority')))


def reorder_sheet(sheet, rows):
    """Move complete cell objects so links/styles follow the product, not the old row."""
    headers=[c.value for c in sheet[1]];idcol=headers.index('product_id')
    original={cells[idcol].value:[copy(c) for c in cells] for cells in sheet.iter_rows(min_row=2)}
    if len(original)!=len(rows):raise ValueError('Duplicate product IDs or row count mismatch')
    for rowno,row in enumerate(rows,2):
        for col,header in enumerate(headers,1):
            cell=copy(original[row['product_id']][col-1]);cell.row=rowno;cell.column=col
            if cell.value!=row.get(header):cell.value=row.get(header)
            if cell.hyperlink:cell._hyperlink=copy(cell.hyperlink);cell._hyperlink.ref=cell.coordinate
            sheet._cells[(rowno,col)]=cell
