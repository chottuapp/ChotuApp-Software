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
 ('Jeans',r'\bjeans?\b|\bdenim\s+(?:trousers?|pants?)\b'),('Cargo Trousers',r'\bcargo\s+(?:trousers?|pants?)\b'),('Joggers',r'\bjoggers?\b'),('Shorts',r'\bshorts\b'),('Boxers',r'\bboxers\b'),('Leggings',r'\bleggings?\b|\btights\b'),('Trousers',r'\btrousers?\b|\bpants?\b|\bculottes?\b|\bshalwars?\b'),
 ('Kurtas & Kurtis',r'\bkurt[ai]s?\b'),('Polo Shirts',r'\bpolo\s+(?:shirts?|t[ -]?shirts?)\b'),('T-Shirts',r'\bt[ -]?shirts?\b|\btees?\b'),('Shirts',r'\bshirts?\b'),('Dresses',r'\bdress(?:es)?\b|\bfrocks?\b'),('Caps',r'\b(?:baseball\s+)?caps?\b'),
 ('Lip Gloss',r'\blip\s*gloss\b'),('Lipstick',r'\blipsticks?\b|\blip\s+paint\b'),('Lip Liners',r'\blip\s+liners?\b'),('Lip Balms',r'\blip\s+balms?\b'),('Eyeshadow',r'\beye\s*shadow\b'),('Eyeliner',r'\beye\s*liners?\b|\bkajal\b|\bkohl\b'),('Mascara',r'\bmascaras?\b'),('Foundation',r'\bfoundations?\b'),('Concealer',r'\bconcealers?\b'),('Blush',r'\bblush(?:er)?\b'),('Highlighter',r'\bhighlighters?\b'),('Makeup Primer',r'\bprimers?\b'),('Face Powder',r'\b(?:face|setting|loose|compact)\s+powder\b'),
 ('Face Wash',r'\bface\s*wash\b|\bfacial\s+wash\b'),('Facial Cleanser',r'\b(?:facial|face|gel|gentle|foaming|milk)\s+cleanser\b|\bcleansing\s+milk\b'),('Hair Serum',r'\bhair\s+(?:growth\s+)?serum\b'),('Lip Treatments',r'\blip\s+serum\b'),('Face Serum',r'\b(?:face\s+)?serum\b'),('Face Toner',r'\btoners?\b'),('Sunscreen',r'\bsunscreen\b|\bsunblock\b'),
 ('Hair Shampoo',r'\bshampoo\b'),('Hair Conditioner',r'\bhair\s+conditioner\b'),('Hair Treatments',r'\bhair\s+(?:mask|treatment)\b|\bkeratin\s+mask\b'),('Hair Oil',r'\bhair\s+oil\b'),
 ('Body Lotion',r'\bbody\s+(?:lotion|milk)\b'),('Body Wash',r'\bbody\s+wash\b|\bshower\s+gel\b'),('Hand Wash',r'\bhand\s+wash\b'),('Hand Sanitiser',r'\bhand\s+saniti[sz]er\b'),('Facial Moisturiser',r'\bmoisturi[sz]er\b|\bface\s+cream\b|\bfacial\s+cream\b'),('Body Cream',r'\bbody\s+cream\b'),('Face Masks',r'\b(?:face|facial|clay|sheet)\s+mask\b'),('Wet Wipes',r'\b(?:wet|baby|cleansing|refreshing|travelling)\s+wipes\b'),('Fragrance',r'\bperfume\b|\beau\s+de\s+parfum\b|\bfragrance\s+mist\b'),
]
RULES=[(label,re.compile(pattern,re.I)) for label,pattern in RULES]

def plain(v):
    text=html.unescape(str(v or ''));text=re.sub(r'<[^>]+>',' ',text)
    return re.sub(r'\s+',' ',text).strip()
def _infer_type(name,description):
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
    path=str(row.get('website_category_path') or '')
    verified=row.get('website_category_status') in VERIFIED and path and row.get('website_category_source_url') and row.get('website_category_checked_at')
    if row.get('subcategory_source')=='manual' and row.get('subcategory'):return row
    result=infer(row.get('name'),row.get('description'),path if verified else '')
    if result:
        label,source,quote=result
        if verified and path.split(' > ')[-1]==label:
            row.update(subcategory=label,subcategory_source='website',subcategory_evidence=path,subcategory_checked_at=row['website_category_checked_at'])
        else:
            stamp=old[2] if old[0]==label and old[1]==source and old[2] else datetime.now(timezone.utc).isoformat()
            row.update(subcategory=label,subcategory_source=source,subcategory_evidence=quote,subcategory_checked_at=stamp)
        return row
    if verified:
        row.update(subcategory=path.split(' > ')[-1],subcategory_source='website',subcategory_evidence=path,subcategory_checked_at=row['website_category_checked_at']);return row
    if row.get('subcategory'):
        row.setdefault('subcategory_source','existing');row.setdefault('subcategory_evidence','Existing category retained; no clearer product type supported');row.setdefault('subcategory_checked_at','');return row
    row.update(subcategory_source='unverified',subcategory_evidence='No unambiguous product type in the supplied name/description',subcategory_checked_at='')
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

# Public Category describes what the product IS, rather than its fragrance range,
# ingredients, target shop collection, or marketing campaign. Website facts remain separate.
NORMAL_LABELS={
 'Face Wash':'Face Washes & Cleansers','Facial Cleanser':'Face Washes & Cleansers',
 'Face Serum':'Face Serums','Face Toner':'Face Toners','Sunscreen':'Sunscreens',
 'Facial Moisturiser':'Face Moisturisers & Creams','Body Lotion':'Body Lotions',
 'Body Cream':'Body Creams','Body Wash':'Body Washes & Shower Gels','Hand Wash':'Hand Washes',
 'Hand Sanitiser':'Hand Sanitisers','Hair Shampoo':'Hair Shampoos','Hair Conditioner':'Hair Conditioners',
 'Hair Serum':'Hair Serums','Hair Oil':'Hair Oils','Lip Gloss':'Lip Glosses','Lipstick':'Lipsticks',
 'Eyeshadow':'Eyeshadows','Eyeliner':'Eyeliners','Mascara':'Mascaras','Foundation':'Foundations',
 'Concealer':'Concealers','Blush':'Blushers','Highlighter':'Highlighters',
 'Face Powder':'Face Powders','Makeup Primer':'Makeup Primers','Salt':'Salts','Fragrance':'Perfumes & Fragrances','Ready-to-Wear':'Ready-to-Wear Outfits',
}
# These rules are ordered by intended purpose. They run before generic "shampoo",
# "baby", "milk", "tea" or scent words can pull an item into an unrelated domain.
PURPOSE_RULES=[
 ('Hand & Foot Creams',r'\bhand\s*(?:&|and)\s*foot\b.{0,25}\bcream\b'),
 ('Hand & Foot Lotions',r'\bhand\s*(?:&|and)\s*foot\b.{0,25}\blotion\b'),('Hand & Foot Scrubs',r'\bhand\s*(?:&|and)\s*foot\b.{0,25}\bscrub\b'),
 ('Eye Creams',r'\beye\s+cream\b'),('Makeup Removers',r'\bmicellar\s+water\b'),('Beard Care',r'\bbeard\s+leave[ -]in\s+cream\b'),
 ('Face & Body Creams',r'\bface\s*,?\s*hand\s*(?:&|and)\s*body\b'),
 ('Petroleum Jellies',r'\bpetroleum\s+jelly\b'),('Skin Soothing Gels',r'\b(?:rose|lavender|aloe vera)\s+skin\s+gel\b'),
 ('Eyelash Curlers',r'\blash\s+turner\b|\beyelash\s+curler\b'),('Eyebrow Products',r'\beyebrow\s+pencils?\b'),
 ('Multipurpose Makeup Pencils',r'\blip\s*(?:&|and)\s*eye\s+pencil\b'),
 ('Blackhead Removal Strips',r'\bnose\b.{0,30}\bstrips\b'),('Face Masks',r'\b(?:black|peel[ -]off)\s+mask\b|\bnose\s+blackhead\s+remover\b'),
 ('Hand Masks',r'\bhand\s+mask\b'),('Foot Masks',r'\bfoot\s+mask\b'),('Eye Patches',r'\beye\s+patches\b'),
 ('Hair Removal Waxes & Strips',r'\b(?:beads|hot)\s+wax\b'),('Nail Polishes',r'\bnail\s+colou?r\b'),('Nail Tools',r'\bnail\s+filer\b'),
 ('Massage Creams',r'\bmassage\s+cream\b'),('Skin Scrubs & Exfoliators',r'\bskin\s+polisher\b'),
 ('Tops',r'\b(?:tank|ribbed|rib)\s+tops?\b'),('Undershirts',r'\bundershirts?\b'),
 ('Shorts',r'\bcotton\s+short\b'),('Clothing Sets',r'\b(?:gharara|sharara)\s+outfit\b'),
 ('Hair Colours & Dyes',r'\bhair\s+colou?r\b'),('Beard Colours',r'\b(?:beard|mustache|moustache)\b.{0,40}\bcolou?r\b'),
 ('Hair Removal Creams',r'\bhair\s+remov(?:al|ing)\s+cream\b'),('Hair Removal Waxes & Strips',r'\b(?:body|face|hair removing)\s+wax\b|\bwax\s+strips?\b'),
 ('Makeup Setting Sprays',r'\b(?:makeup|make up)\s+fixer\b|\bsetting\s+spray\b'),('BB & CC Creams',r'\b(?:bb|cc)\s+cream\b'),
 ('Lip Tints',r'\blip\s+tints?\b'),('Lip Sets',r'\blip\s+duo\b'),('Contouring & Bronzers',r'\bcontour(?:ing)?\b|\bbronzer\b'),
 ('Press-On Nails',r'\b(?:press[ -]?on|stick[ -]?on)\s+nails\b'),('Nail Polishes',r'\bnail\s+(?:polish|enamel|varnish|top coat)\b'),('Nail Tools',r'\bnail\s+(?:file|clipper|cutter|buffer|scissor)\b'),
 ('Razors & Shaving Tools',r'\brazors?\b'),('Body Butters',r'\bbody\s+butter\b'),('Foot Creams',r'\bheel\s+(?:care|cream)\b'),
 ('Face Peels & Exfoliators',r'\bpeeling\s+solution\b'),('Face Washes & Cleansers',r'\bcleansing\s+(?:oil|milk|balm)\b'),
 ('Face Moisturisers & Creams',r'\b(?:face|facial|night|day|whitening|brightening|freckle|glow)\s+cream\b'),
 ('Skirts',r'\bskirts?\b'),('Co-ord Sets',r'\bco[ -]?ord\s+sets?\b'),('Polo Shirts',r'\bpolo(?:s| shirt)?\b'),
 ('Clothing Sets',r'\b[234]\s*(?:piece|pc)\b.{0,90}\b(?:gharara|sharara|lehenga|frock|dress|shalwar|kurta|suit|outfit|set)\b'),
 ('Bath Soaps',r'\b(?:luffa|loofah|beauty|bath|neem)\s+soap\b'),('Toothpaste Dispensers',r'\btooth\s*paste\s+dispenser\b'),('Dried Herbs',r'\bkasuri\s+methi\b'),
 ('Mosquito Repellents',r'\bmosquito\s+repellent\b'),('Hand Creams',r'\bhand(?:\s*(?:&|and)\s*nail)?\s+(?:cream|balm)\b'),('Foot Creams',r'\bfoot\s+cream\b'),('Nursing Pads',r'\bnursing\s+pads?\b'),('Paper Towels & Rolls',r'\bmaxi\s+roll\b'),
 ('Laundry Stain-Removal Wipes',r'\b(?:clothes|clothing|fabric)\b.{0,50}\bwipes\b|\bwipes\b.{0,90}\b(?:clothes|clothing)\b'),
 ('Fabric Softeners',r'\bfabric\s+soft(?:e)?ner\b'),
 ('Fabric Detergents',r'\b(?:white|fabric|abaya)\s+(?:cleansing\s+)?shampoo\b|\b(?:laundry|fabric|clothes|abaya)\s+(?:liquid\s+)?(?:detergent|cleanser|shampoo)\b'),
 ('Pet Shampoos',r'\b(?:dog|cat|pet|puppy|kitten)\b.{0,60}\bshampoo\b|\bshampoo\b.{0,80}\b(?:dog|cat|pet|puppy|kitten)\b'),
 ('Pet Deodorisers & Mists',r'\b(?:dog|cat|pet)\b.{0,60}\b(?:mist|deodori[sz])\w*|\bmist\b.{0,60}\b(?:dog|cat|pet)\b'),
 ('Baby Shampoos',r'\bbaby\s+shampoo\b'),
 ('Baby Bath & Body Washes',r'\bbaby\s+(?:washing\s+gel|body\s+wash|bath\s+wash|wash(?:ing)?)\b'),
 ('Baby Lotions & Creams',r'\bbaby(?:\s+milk)?\s+(?:lotion|cream)\b'),
 ('Baby Mists',r'\bbaby\s+mist\b'),('Baby Powders',r'\bbaby\s+powder\b'),
 ('Body Powders',r'\bprickly\s+heat\s+powder\b|\bbody\s+powder\b'),
 ('Makeup Remover Wipes',r'\b(?:make[ -]?up|cleansing)\b.{0,55}\b(?:remov\w*\s+)?wipes\b'),
 ('Surface Disinfectant Wipes',r'\bdisinfectant\s+wipes\b|\bwipes\b.{0,90}\b(?:surfaces|surface cleaning)\b'),
 ('Baby Wipes',r'\bbaby\s+wipes\b'),('Body Wipes',r'\bbody\s+wipes\b'),
 ('Wet Wipes',r'\b(?:wet|travelling|travel|refreshing)\s+wipes\b'),
 ('Cotton Buds',r'\bcotton\s+buds?\b'),('Cotton Pads',r'\bcotton\s+(?:pads?|balls?)\b'),
 ('Toilet Paper',r'\btoilet\s+(?:roll|paper|tissue)\b'),('Kitchen Paper Towels',r'\bkitchen\s+(?:roll|towel)\b'),
 ('Facial Tissues',r'\b(?:facial|mini|soft\s+pack|pocket|compact)\s+tissues?\b|\bcompact mini tissues?\b'),
 ('Hand Washes',r'\bhand\s+(?:wash|soap)\b'),('Hand Sanitisers',r'\bhand\s+saniti[sz]er\b'),
 ('Body Lotions',r'\bbody\s+(?:lotion|milk)\b|\bfragrance\s+lotion\b'),
 ('Body Washes & Shower Gels',r'\bbody\s+wash\b|\bshower\s+gel\b'),
 ('Body Creams',r'\bbody\s+cream\b'),('Bath Soaps',r'\b(?:bath|beauty|toilet)\s+soap\b|\bsoap\s+bars?\b'),
 ('Body Mists',r'\bbody\s+mists?\b'),('Room Fragrances',r'\broom\s+(?:spray|freshener)\b|\bair\s+freshener\b|\breed\s+diffuser\b'),
 ('Body Scrubs',r'\bbody\s+scrub\b'),('Face Scrubs & Exfoliators',r'\b(?:face|facial)\s+scrub\b'),
]
PURPOSE_RULES=[(label,re.compile(pattern,re.I)) for label,pattern in PURPOSE_RULES]

def _product_prose(description):
    # Application tools and ingredient names are not the item being sold.
    raw=str(description or '')
    boundary=re.search(r'(?im)(?:^|\n)\s*(?:how to use[^\n]*|directions[^\n]*|usage|ingredients|precautions[^\n]*|warnings?|care instructions|composition & care|available options|product options)\s*[:：.]?\s*(?:\n|$)',raw)
    if boundary:raw=raw[:boundary.start()]
    return plain(raw)[:2200]

def _quote(label,field,text,match=None):
    evidence=text[:300] if match is None else text[max(0,match.start()-55):match.end()+110]
    return label,'inferred_product_name' if field=='name' else 'inferred_description',field+': '+evidence

def _bundle(name,body):
    title=plain(name);context=(title+' '+body[:1200]).lower()
    bundle=bool(re.search(r'\b(?:bundle|combo|kit|deal|twin pack|triple pack|glow pack|glow set)\b',title,re.I))
    if re.search(r'\bduo\b',title,re.I) and not re.search(r'\blip\b',title,re.I):bundle=True
    if not bundle:return None
    if re.search(r'\b(?:dairy|cheese|ghee|butter|yogh?urt|raita|lassi|milky)\b',title,re.I):label='Dairy Bundles'
    elif re.search(r'\b(?:spice|masala|coriander|cumin)\b',context):label='Spice Bundles'
    elif re.search(r'\bhair\s+colou?r\b',context):label='Hair Colours & Dyes'
    elif re.search(r'\b(?:hair|shampoo|conditioner)\b',title,re.I):label='Hair Care Bundles'
    else:
        makeup=bool(re.search(r'\b(?:makeup|lipstick|lip gloss|eyeshadow|mascara|foundation|blush)\b',context))
        skin=bool(re.search(r'\b(?:skin care|skincare|serum|face wash|cleanser|toner|retinol|niacinamide|ceramide|pigmentation|oiliness|dark spots|lotion|moisturi[sz]er|acne|wrinkles)\b',context))
        if makeup and skin:label='Beauty Sets & Bundles'
        elif makeup:label='Makeup Sets'
        elif skin or re.search(r'\b(?:skin|face|facial|cream)\b',context):label='Skin Care Bundles'
        elif re.search(r'\b(?:hair|shampoo|conditioner)\b',context):label='Hair Care Bundles'
        elif re.search(r'\b(?:cheese|milk|ghee|butter|yogh?urt|raita|lassi)\b',context):label='Dairy Bundles'
        else:return None
    return _quote(label,'description',title+'; '+body)

def infer(name,description,website_path=''):
    title=plain(name);body=_product_prose(description)
    conflicting=bool(re.search(r'(?i)Product Clarification:|description refers to .*while this listing',body))
    if conflicting:body=''
    combined=title+' '+body[:1100]
    # Explicit intended-use wording disambiguates fabric shampoo, pet scents, and laundry wipes.
    cross_domain={'Pet Shampoos','Pet Deodorisers & Mists','Laundry Stain-Removal Wipes','Fabric Detergents'}
    for label,rule in PURPOSE_RULES:
        if label in cross_domain:
            match=rule.search(combined)
            if match:return _quote(label,'description',combined,match)
    bundle=_bundle(title,body)
    if bundle:return bundle
    for label,rule in PURPOSE_RULES:
        if label in cross_domain:continue
        match=rule.search(title)
        if match:return _quote(label,'name',title,match)
    if re.search(r'(?i)\bsoap\b',title):return _quote('Bath Soaps','name',title)
    if re.search(r'(?i)\bcream\b',title) and re.search(r'(?i)\bface\s*,?\s*hand\s*(?:&|and)\s*body\b',body):return _quote('Face & Body Creams','description',body)
    if re.search(r'(?i)\bcream\b',title) and re.search(r'(?i)\b(?:face|facial|skin|skincare)\b',body):return _quote('Face Moisturisers & Creams','description',body)
    if all(re.search(r'(?i)\b'+word+r'\s+notes\b',body) for word in ('top','heart','base')):return _quote('Perfumes & Fragrances','description',body)
    # Verified fragrance-domain membership resolves generic scent names without inventing notes.
    if re.search(r'(?i)\bfragrances?\b|\bperfumes?\b',website_path) and not re.search(r'(?i)\b(?:lotion|wash|cream|soap|shampoo|wipes|saniti[sz]er)\b',title):
        return 'Perfumes & Fragrances','inferred_product_type','Website domain path: '+website_path+'; name: '+title
    # A type explicitly named in the title outranks items mentioned as ingredients or application tools.
    result=_infer_type(title,'')
    if result:
        label,source,quote=result
        return NORMAL_LABELS.get(label,label),source,quote
    outfit=_infer_type(title,body)
    if outfit and outfit[0] in {'Unstitched Suits','Ready-to-Wear','Suits & Ensembles'}:
        return NORMAL_LABELS.get(outfit[0],outfit[0]),outfit[1],outfit[2]
    for label,rule in PURPOSE_RULES:
        if label in cross_domain:continue
        match=rule.search(body)
        if match:return _quote(label,'description',body,match)
    result=_infer_type(title,body)
    if result:
        label,source,quote=result
        return NORMAL_LABELS.get(label,label),source,quote
    # "Fragrance" in an INCI list is not perfume. Only explicit product prose can support this fallback.
    if re.search(r'(?i)\b(?:is|a|an|this)\b.{0,50}\b(?:perfume|fragrance|scent)\b|\beau de parfum\b',body) and not re.search(r'(?i)\b(?:wash|cream|lotion|soap|shampoo|wipes|colou?r)\b',title):
        return _quote('Perfumes & Fragrances','description',body)
    return None
