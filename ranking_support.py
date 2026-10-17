"""Evidence-aware catalog merchandising; never infer sales from prices."""
from copy import copy
from decimal import Decimal, InvalidOperation
from urllib.parse import urlsplit

FIELDS=('category_priority','product_priority','popularity_basis','popularity_source_url','popularity_checked_at')
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
