"""Conservative, source-labelled product-type inference; never website or sales evidence."""
import html,re
from datetime import datetime,timezone
FIELDS=('subcategory_source','subcategory_evidence','subcategory_checked_at')
VERIFIED={'verified_navigation_membership','verified_product_breadcrumb'}
# Specific types precede general ingredients, materials and use-case mentions.
RULES=[
 ('Stud Earrings',r'\bstuds\b'),('Hoop Earrings',r'\bhoops?\b'),('Earrings',r'\bearrings?\b'),('Rings',r'\brings?\b'),
 ('Makeup Sponges',r'\bbeauty\s+sponge\b|\bmakeup\s+sponge\b'),('Makeup Brushes',r'\bmakeup\s+brush\b'),('Body Lotion',r'\bfragrance\s+lotion\b'),('Lip & Cheek Colour',r'\blip\s*(?:&|and)\s*cheek\b'),('Makeup Adhesive',r'\bglitter\s+glue\b'),('Packaging Bags',r'\bpackaging\s+bag\b'),('Packaging Boxes',r'\bpackaging\s+box\b'),
 ('Gift Boxes',r'\bgift\s*box(?:es)?\b'),
 ('Loose-Leaf Tea',r'\btea\s+leaf\s+blend\b|\bloose[ -]leaf\s+tea\b'),('Tea Bags',r'\btea\s*bags?\b'),('Black Tea',r'\bblack\s+tea\b'),
 ('Garam Masala',r'\bgaram\s+masala\b'),('Spice Blends',r'\b(?:biryani|qorma|korma|karahi|seekh\s+kabab|chicken\s+tikka|achar\s+gosht|malai\s+boti|chaat)\s+masala\b'),
 ('Ground Spices',r'\b(?:ginger|garlic|coriander|cumin|turmeric|red\s+chill?i|black\s+pepper)\s+powder\b'),('Whole Spices',r'\b(?:black|white)\s+pepper\s+whole\b|\b(?:coriander|cumin|cardamom|clove|pepper)\s+seeds?\b|\bwhole\s+spices?\b'),('Salt',r'\b(?:pink|refined|iodized|iodised|himalayan|table)\s+salt\b'),
 ('Pickles',r'\bpickles?\b(?!-like)|\bachaar\b'),('Vermicelli',r'\bvermicelli\b'),
 ('Buffalo Mozzarella',r'\bbuffalo\s+mozzarella\b'),('Mozzarella Cheese',r'\bmozzarella(?:\s+cheese)?\b'),('Cheddar Cheese',r'\bcheddar(?:\s+cheese)?\b'),('Cottage Cheese',r'\bcottage\s+cheese\b'),('Cheese Slices',r'\b(?:burger|sandwich|toast|low[ -]fat)\s+cheese\b|\bcheese\s+slices\b'),('Pizza Cheese',r'\bpizza\s+cheese\b'),('Chilli Cheese',r'\bchill?i\s+cheese\b'),
 ('Butter',r'\b(?:salted|unsalted)\s+butter\b'),('Desi Ghee',r'\bdesi\s+ghee\b'),('Milk',r'\bpasteuri[sz]ed\s+milk\b'),('Lassi',r'\blassi\b'),('Raita',r'\braita\b'),('Yoghurt',r'\byogh?urt\b|\bdahi\b'),
 ('Unstitched Suits',r'\bun[ -]?stitched\b'),('Ready-to-Wear',r'\bready[ -]to[ -]wear\b|\brtw\b|\bstitched\s+(?:suit|ensemble)\b'),
 ('Kaftans',r'\bkaftans?\b'),('Shawls',r'\bshawls?\b'),('Dupattas',r'\bdupattas?\b'),('Abayas',r'\babayas?\b'),
 ('Hoodies',r'\bhood(?:ie|ies)\b'),('Sweatshirts',r'\bsweatshirts?\b'),('Sweaters',r'\bsweaters?\b'),('Cardigans',r'\bcardigans?\b'),('Jackets',r'\bjackets?\b'),
 ('Jeans',r'\bjeans?\b|\bdenim\s+(?:trousers?|pants?)\b'),('Cargo Trousers',r'\bcargo\s+(?:trousers?|pants?)\b'),('Joggers',r'\bjoggers?\b'),('Shorts',r'\bshorts\b'),('Boxers',r'\bboxers\b'),('Leggings',r'\bleggings?\b|\btights\b'),('Trousers',r'\btrousers?\b|\bpants\b|\bculottes?\b|\bshalwars?\b'),
 ('Kurtas & Kurtis',r'\bkurt[ai]s?\b'),('Polo Shirts',r'\bpolo\s+(?:shirts?|t[ -]?shirts?)\b'),('T-Shirts',r'\bt[ -]?shirts?\b|\btees?\b'),('Shirts',r'\bshirts?\b'),('Dresses',r'\bdresses?\b|\bfrocks?\b'),('Caps',r'\b(?:baseball\s+)?caps?\b'),
 ('Lip Gloss',r'\blip\s*gloss\b'),('Lipstick',r'\blipsticks?\b|\blip\s+paint\b'),('Lip Liners',r'\blip\s+liners?\b'),('Lip Balms',r'\blip\s+balms?\b'),('Eyeshadow',r'\beye\s*shadow\b'),('Eyeliner',r'\beye\s*liners?\b|\bkajal\b|\bkohl\b'),('Mascara',r'\bmascaras?\b'),('Foundation',r'\bfoundations?\b'),('Concealer',r'\bconcealers?\b'),('Blush',r'\bblush(?:er)?\b'),('Highlighter',r'\bhighlighters?\b'),('Makeup Primer',r'\bprimers?\b'),('Face Powder',r'\b(?:face|setting|loose|compact)\s+powder\b'),
 ('Face Wash',r'\bface\s*wash\b|\bfacial\s+wash\b'),('Facial Cleanser',r'\b(?:facial|face|gel|gentle|foaming|milk)\s+cleanser\b|\bcleansing\s+milk\b'),('Hair Serum',r'\bhair\s+(?:growth\s+)?serum\b'),('Lip Treatments',r'\blip\s+serum\b'),('Face Serum',r'\b(?:face\s+)?serum\b'),('Face Toner',r'\btoners?\b'),('Sunscreen',r'\bsunscreen\b|\bsunblock\b'),
 ('Hair Shampoo',r'\bshampoo\b'),('Hair Conditioner',r'\bhair\s+conditioner\b'),('Hair Treatments',r'\bhair\s+(?:mask|treatment)\b|\bkeratin\s+mask\b'),('Hair Oil',r'\bhair\s+oil\b'),
 ('Body Lotion',r'\bbody\s+(?:lotion|milk)\b'),('Body Wash',r'\bbody\s+wash\b|\bshower\s+gel\b'),('Hand Wash',r'\bhand\s+wash\b'),('Hand Sanitiser',r'\bhand\s+saniti[sz]er\b'),('Facial Moisturiser',r'\bmoisturi[sz]er\b|\bface\s+cream\b|\bfacial\s+cream\b'),('Body Cream',r'\bbody\s+cream\b'),('Face Masks',r'\b(?:face|facial|clay|sheet)\s+mask\b'),('Wet Wipes',r'\b(?:wet|baby|cleansing|refreshing|travelling)\s+wipes\b'),('Fragrance',r'\bperfume\b|\beau\s+de\s+parfum\b|\bfragrance\s+mist\b'),
]
RULES=[(label,re.compile(pattern,re.I)) for label,pattern in RULES]

def plain(v):
    text=html.unescape(str(v or ''));text=re.sub(r'<[^>]+>',' ',text)
    return re.sub(r'\s+',' ',text).strip()
def infer(name,description):
    title=plain(name);body=plain(description)
    if re.search(r'(?i)Product Clarification:|description refers to .*while this listing',body):return None
    # Real bundles are not assigned the first component's type. Generic "set" alone is insufficient.
    if re.search(r'\b(?:bundle|combo|kit|duo|deal)\b',title,re.I):
        context=(title+' '+body[:1200]).lower()
        if re.search(r'\b(?:dairy|cheese|ghee|butter|yogh?urt|raita|lassi|milky)\b',title,re.I):label='Dairy Bundles'
        elif re.search(r'\b(?:spice|masala|coriander|cumin)\b',context):label='Spice Bundles'
        elif re.search(r'\b(?:makeup|lipstick|lip\s+gloss|eyeshadow|mascara|foundation)\b',title,re.I):label='Makeup Sets'
        elif re.search(r'\b(?:hair|shampoo|conditioner)\b',title,re.I):label='Hair Care Bundles'
        elif re.search(r'\b(?:skin|face|facial|serum|cream|lotion)\b',context):label='Skin Care Bundles'
        elif re.search(r'\b(?:hair|shampoo|conditioner)\b',context):label='Hair Care Bundles'
        elif re.search(r'\b(?:cheese|milk|ghee|butter|yogh?urt|raita|lassi)\b',context):label='Dairy Bundles'
        elif re.search(r'\b(?:lipstick|lip\s+gloss|foundation|mascara|eyeshadow|makeup)\b',context):label='Makeup Sets'
        else:return None
        return label,'inferred_description','name: '+title+'; description: '+body[:240]
    if re.search(r'(?i)\bpaint\s+stick\b',title) and re.search(r'(?i)\bfoundation\b',body) and re.search(r'(?i)\bconcealer\b',body):
        return 'Foundation & Concealer Sticks','inferred_description','description: '+body[:300]
    if re.search(r'(?i)\bpaint\s+stick\b',title) and re.search(r'(?i)\bmakeup\b',body):
        return 'Makeup Sticks','inferred_description','description: '+body[:300]
    for field,text in [('name',title),('description',body[:1800].split('Available Options:')[0].split('Product Options:')[0])]:
        candidates=[]
        for label,rule in RULES:
            match=rule.search(text)
            if match:candidates.append((label,match))
        if not candidates:
            if field=='description' and re.search(r'(?i)\btea\b',title) and re.search(r'(?i)\btea\b',body):
                return 'Tea Blends' if re.search(r'(?i)\bblend(?:s|ed|ing)?\b',title+' '+body) else 'Tea','inferred_description','description: '+body[:300]
            continue
        if field=='description':
            outfit=bool(re.search(r'(?i)\b(?:suit|ensemble|outfit|[23][ -]?(?:pc|piece))\b',text))
            unstitched=bool(re.search(r'(?i)\bun[ -]?stitched\b',text));ready=bool(re.search(r'(?i)\bready[ -]to[ -]wear\b|\brtw\b',text))
            if outfit and unstitched and ready:
                return 'Suits & Ensembles','inferred_description','description: '+text[:300]
            if outfit and unstitched!=ready:
                chosen='Unstitched Suits' if unstitched else 'Ready-to-Wear'
                candidates=[v for v in candidates if v[0]==chosen]
        if field=='description':
            # Supporting prose can list unrelated components/uses. Require an unambiguous product type.
            labels={label for label,match in candidates}
            apparel={'Unstitched Suits','Ready-to-Wear','Kaftans','Shawls','Dupattas','Abayas','Hoodies','Sweatshirts','Sweaters','Cardigans','Jackets','Jeans','Cargo Trousers','Joggers','Shorts','Boxers','Leggings','Trousers','Polo Shirts','T-Shirts','Shirts','Dresses','Kurtas & Kurtis'}
            if labels & apparel and re.search(r'(?i)\b(?:garment details|rtw|un[ -]?stitched|composition & care)\b',text):labels &= apparel
            if labels & {'Hair Serum','Lip Treatments'}:labels.discard('Face Serum')
            if 'Kaftans' in labels:labels.difference_update({'Ready-to-Wear','Shirts','Dresses','Kurtas & Kurtis'})
            if labels & {'Shirts','Kurtas & Kurtis'}:labels.discard('Ready-to-Wear')
            if 'Kurtas & Kurtis' in labels:labels.discard('Shirts')
            if 'T-Shirts' in labels:labels.discard('Shirts')
            if 'Polo Shirts' in labels:labels.difference_update({'Shirts','T-Shirts'})
            if 'Cargo Trousers' in labels:labels.discard('Trousers')
            if labels & {'Stud Earrings','Hoop Earrings'}:labels.discard('Earrings')
            if len(labels)>1:
                # Ingredient and serving suggestions later in a paragraph are not the product type.
                opening=re.split(r'(?<=[.!?])\s+',text,maxsplit=1)[0]
                early=[(label,match) for label,match in candidates if match.end()<=len(opening) and label in labels]
                if len({label for label,match in early})!=1:return None
                labels={early[0][0]}
            candidates=[v for v in candidates if v[0] in labels]
        label,match=candidates[0];quote=text[max(0,match.start()-65):min(len(text),match.end()+100)]
        return label,'inferred_product_name' if field=='name' else 'inferred_description',field+': '+quote
    return None

def apply(row,previous=None):
    old=previous or (row.get('subcategory'),row.get('subcategory_source'),row.get('subcategory_checked_at'))
    path=str(row.get('website_category_path') or '');verified=row.get('website_category_status') in VERIFIED and path and row.get('website_category_source_url') and row.get('website_category_checked_at')
    if row.get('subcategory'):
        # Preserve explicit website and owner labels; inference only fills missing values.
        if verified:
            row.update(subcategory_source='website',subcategory_evidence=path,subcategory_checked_at=row['website_category_checked_at'])
        else:
            row.setdefault('subcategory_source','existing');row.setdefault('subcategory_evidence','Existing subcategory retained');row.setdefault('subcategory_checked_at','')
        return row
    if verified:
        row.update(subcategory=path.split(' > ')[-1],subcategory_source='website',subcategory_evidence=path,subcategory_checked_at=row['website_category_checked_at']);return row
    result=infer(row.get('name'),row.get('description'))
    if result:
        label,source,quote=result
        stamp=old[2] if old[0]==label and old[1]==source and old[2] else datetime.now(timezone.utc).isoformat()
        row.update(subcategory=label,subcategory_source=source,subcategory_evidence=quote,subcategory_checked_at=stamp)
    else:row.update(subcategory_source='unverified',subcategory_evidence='No unambiguous product type in the supplied name/description',subcategory_checked_at='')
    return row


# Owner-locked public export contract: shop_code first, one Category field.
SHOP_CODES={
 'fardafoods.com':'SE10002','adamsestore.com':'SE10003','islamabadtea.pk':'SE10004',
 'seran.com.pk':'SE10005','shopmodest.pk':'SE10006','thehangerpakistan.com':'SE10007',
 'vincecare.com':'SE10008','tawakkalfabrics.co':'SE10009','stylo.pk':'SE10010',
 'junaidjamshed.com':'SE10011','rivaj-uk.com':'SE10012','rawayat.com.pk':'SE10013',
 'missrose.com.pk':'SE10014','elitecosmeticspk.com':'SH10003',
}
def export_values(row):
    from urllib.parse import urlsplit
    values=dict(row)
    values['Category']=row.get('Category') or row.get('subcategory')
    if not values.get('shop_code'):
        host=(urlsplit(str(row.get('source_url') or '')).hostname or '').lower().removeprefix('www.')
        values['shop_code']=SHOP_CODES.get(host,'')
    return values
