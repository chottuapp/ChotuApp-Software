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
 'shop.fardafoods.com':'SE10002','fardafoods.com':'SE10002','adamsestore.com':'SE10003','islamabadtea.pk':'SE10004',
 'seran.com.pk':'SE10005','shopmodest.pk':'SE10006','thehangerpakistan.com':'SE10007',
 'vincecare.com':'SE10008','tawakkalfabrics.co':'SE10009','stylo.pk':'SE10010',
 'junaidjamshed.com':'SE10011','rivaj-uk.com':'SE10012','rawayat.com.pk':'SE10013',
 'missrose.com.pk':'SE10014','elitecosmeticspk.com':'SH10003',
}
# Owner-confirmed host aliases for the full 29-store registry (22 October 2026).
SHOP_CODES.update({'missrose.com.pk': 'SE10014', 'rawayat.com.pk': 'SE10013', 'rivaj-uk.com': 'SE10012', 'junaidjamshed.com': 'SE10011', 'stylo.pk': 'SE10010', 'tawakkalfabrics.co': 'SE10009', 'vincecare.com': 'SE10008', 'elitecosmeticspk.com': 'SH10003', 'thehangerpakistan.com': 'SE10007', 'shopmodest.pk': 'SE10006', 'seran.com.pk': 'SE10005', 'islamabadtea.pk': 'SE10004', 'adamsestore.com': 'SE10003', 'fardafoods.com': 'SE10002', 'czone.com.pk': 'SE10015', 'laam.com': 'SE10016', 'nisanaturals.pk': 'SE10017', 'pk.khaadi.com': 'SE10018', 'sapphireonline.pk': 'SE10019', 'gulahmedshop.com': 'SE10020', 'pk.hemaniherbals.com': 'SE10021', 'saeedghani.pk': 'SE10022', 'coolandcool.pk': 'SE10023', 'denimleftover.com': 'SE10024', 'skinfactor.pk': 'SE10025', 'outfitters.com.pk': 'SE10026', 'bonanzasatrangi.com': 'SE10027', 'zellbury.com': 'SE10028', 'zerolifestyle.co': 'SE10029'})
SHOP_CODES.update({'pk.khaadi.com':'SE10018','pk.sapphireonline.pk':'SE10019'})
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
 ('Hair Conditioners',r'\bconditioner\b'),('Face Masks',r'\b(?:face|facial|sheet|tissue|mud)\s+mask\b'),('Car-Care Products',r'\bcar\s+(?:wax|shampoo|polish)\b|\bdashboard\s+(?:polish|cleaner)\b'),
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
 ('Skirts',r'\bskirts?\b'),('Co-ord Sets',r'\bco[ -]?ord\s+sets?\b'),('Polo Shirts',r'\bpolo(?:s| shirts?| t-shirts?)\b'),
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
    jewellery=re.search(r'(?im)(?:^|\n)\s*(?:\d+[.)]\s*)?(?:jewelry|jewellery)\s+care\s*[:：]',raw)
    if jewellery and (boundary is None or jewellery.start()<boundary.start()):boundary=jewellery
    detail=re.search(r'(?im)^\s*product description\s*[:：]?\s*$',raw)
    extra=''
    if detail:
        extra=re.split(r'(?im)^\s*(?:product options|available options|care instructions|composition & care)\s*[:：]?',raw[detail.end():],maxsplit=1)[0]
    if boundary:raw=raw[:boundary.start()]
    return plain(raw+' '+extra)[:2200]

def _quote(label,field,text,match=None):
    evidence=text[:300] if match is None else text[max(0,match.start()-55):match.end()+110]
    return label,'inferred_product_name' if field=='name' else 'inferred_description',field+': '+evidence

def _bundle(name,body):
    title=plain(name);context=(title+' '+body[:1200]).lower()
    bundle=bool(re.search(r'\b(?:bundle|combo|kit|deal|twin pack|triple pack|glow pack|glow set)\b',title,re.I))
    if re.search(r'\bduo\b',title,re.I) and not re.search(r'\blip\b',title,re.I):bundle=True
    if not bundle:return None
    if re.search(r'\b(?:perfume|attar|fragrance|body spray)\b',title,re.I):label='Fragrance Sets'
    elif re.search(r'\b(?:dairy|cheese|ghee|butter|yogh?urt|raita|lassi|milky)\b',title,re.I):label='Dairy Bundles'
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


# Explicit named item types for electronics, home goods and herbal ranges.
# Read the leading item phrase first; specifications describe components too.
NAMED_TYPES=[
 ('Bomber Jackets',r'\bbomber zipper\b'),('Activewear',r'\bactivewear\b'),
 ('Backpacks',r'\bbackpacks?\b'),('Blazers & Coats',r'\b(?:blazers?|coats?)\b'),('Dungarees',r'\bdungarees?\b'),
 ('Heels & Pumps',r'\b(?:heels|pumps)\b'),('Mules',r'\bmules\b'),('Mary Jane Shoes',r'\bmary jane\b'),('Boat Shoes',r'\bboat shoes\b'),
 ('Chinos',r'\bchinos?\b'),('Scarves',r'\bscar(?:f|ves)\b'),('Beanies',r'\bbeanie\b'),('Cardholders',r'\bcardholder\b'),
 ('Headbands',r'\bheadbands?\b'),('Keychains',r'\bkeychains?\b'),('Hair Accessories',r'\bhair accessor(?:y|ies)\b'),('Earrings',r'\bearings\b'),
 ('Sunglasses',r'\bsuglasses\b'),('Shopping Bags',r'\bshopping bags?\b'),('Tops',r'\b(?:bandeau|peplum)\s+top\b'),
 ('Pullovers',r'\bpull[ -]?overs?\b'),('Forehead Jewellery',r'\bbindiya kanta\b'),

 ('Jewellery Sets',r'\b(?:locket|mala|choker|pendant|dora|jhumka|necklace|kundan)\s+sets?\b'),
 ('Bangles & Karas',r'\b(?:bangles?|kara|karay|kada)\b'),('Bracelets',r'\bbracelets?\b'),('Watches',r'\bwatch(?:es)?\b'),
 ('Anklets',r'\banklets?\b'),('Pendants & Lockets',r'\b(?:pendants?|lockets?)\b'),('Necklaces',r'\b(?:necklaces?|choker|mala)\b'),
 ('Jewellery Chains',r'\bchains?\b'),('Nose Jewellery',r'\b(?:nath|nose\s+(?:pin|ring|stud))\b'),
 ('Hand Harnesses',r'\b(?:hand harness|angla)\b'),('Jhumka Earrings',r'\b(?:jhumk(?:a|ay|ey|y|i)s?|bali)\b'),
 ('Hair Clips & Pins',r'\b(?:hair|bobby|scarf)\s+(?:clips?|pins?)\b'),('Hair Ties & Accessories',r'\b(?:hair ties?|ponytail|scrunchies?|hair band|hair catcher)\b'),
 ('Forehead Jewellery',r'\b(?:tikka|matha patti)\b'),('Sneakers & Trainers',r'\b(?:sneakers?|trainers?)\b'),
 ('Flats',r'\bflats\b'),('Sandals & Slides',r'\b(?:sandals?|slides?|flip[ -]flops?)\b'),('Clogs',r'\bclogs?\b'),('Loafers',r'\bloafers?\b'),('Boots',r'\bboots?\b'),
 ('Briefs & Underwear',r'\b(?:briefs|trunks|underwear)\b'),('Hats',r'\b(?:bucket hat|hats?)\b'),('Belts',r'\bbelts?\b'),('Wallets',r'\bwallets?\b'),
 ('Sunglasses',r'\bsunglasses\b'),('Blouses',r'\bblouses?\b'),('Tops',r'\b(?:printed|ribbed|knitted|cropped)\s+tops?\b|\bcamisoles?\b'),
 ('Jumpsuits',r'\b(?:jumpsuit|playsuit|romper)\b'),('Vests & Gilets',r'\b(?:vests?|gilets?)\b'),('Denim Shorts',r'\bjorts\b'),('Shackets',r'\bshackets?\b'),

 ('Shoe-Care Products',r'\bshoe\s+(?:cleaner|polish\w*)\b|\bfoam cleaner for sneakers\b'),
 ('Car-Care Products',r'\bcar\s+(?:all purpose cleaner|engine degreaser|glass cleaner|interior dressing|waterless wash)\b'),
 ('Craft Colourants',r'\bliquid colou?rs\b'),('Polishing Compounds',r'\bluster bars\b|\bpolishing compounds\b'),
 ('Furniture Polishes',r'\bfurniture\s+(?:shiner|polish)\b'),('Liquid Droppers',r'\bplastic droppers\b'),('pH Test Papers',r'\bph papers\b'),
 ('Dishwashing Liquids',r'\bdish\s*wash\b'),('Descalers',r'\bdescal[ae]r\b'),('Toilet Cleaners',r'\btoilet cleaner\b'),
 ('Face Masks',r'\b(?:essence|gold)\s+mask\b'),('Makeup Removers',r'\bmakeup remover\b'),('Face Washes & Cleansers',r'\b(?:squalane|fade)\s+cleanser\b'),
 ('Herbal Massage Balms',r'\bvapou?r rub\b'),('Herbal & Cosmetic Oils',r'\bherbal oil\b'),('Herbal Supplements',r'\bherbal supplement\b'),
 ('Herbal Powders',r'\b(?:black seed|berberine|papaya leaves|pain relief)\s+powder\b'),
 ('Food Flavourings',r'\bfood essence\b'),('Saffron',r'\b(?:premium quality |pure )?saffron\s+\d+(?:\.\d+)?\s*g\b'),('Instant Drink Mixes',r'\binstant drink powder\b'),
 ('Quinoa',r'\bquinoa\b'),
 ('Tablets',r'\bipad\b|\b(?:android|drawing|graphics|pen)\s+tablet\b'),('Wall Chargers',r'\b(?:wall charger|gan.*charger)\b'),('Security Cameras',r'\b(?:security.*camera|home camera)\b'),
 ('Computer Cases',r'\b(?:tower case|tower chassis)\b'),('Gaming Chairs',r'\b(?:gaming|office)\s+chair\b'),('Gaming Consoles',r'\b(?:playstation|gaming console)\b'),
 ('Ink & Toner',r'\b(?:ink bottle|toner cartridge|toner reload kit|ink cartridge)\b'),
 ('Game Controllers',r'\b(?:game ?pad|(?:wireless |bluetooth |mode )?controller)\b'),
 ('Keyboard & Mouse Sets',r'\bdesktop set\b|\b(?:keyboard.*mouse|mouse.*keyboard)\b|\bquietkey combo\b'),
 ('Laptop Bags & Backpacks',r'\blaptop\s+(?:backpack|bag|sleeve)\b'),('Laptop Chargers',r'\blaptop\s+(?:charger|adapter)\b'),
 ('Laptop Stands',r'\blaptop\s+(?:stand|cooling pad)\b'),('Laptops',r'\b(?:laptop|notebook|macbook|chromebook)\b'),
 ('Headsets & Headphones',r'\b(?:headsets?|headphones?|earphones?|earbuds?)\b'),
 ('Mouse Pads',r'\b(?:mouse\s*pad|desk\s*mat)\b'),('Computer Mice',r'\bmouse\b(?!\s+trap)'),('Keyboards',r'\bkeyboard\b'),
 ('Webcams',r'\bweb\s*cam\b'),('Microphones',r'\bmicrophone\b'),('Speakers',r'\b(?:speaker|soundbar|subwoofer)\b'),
 ('SSD Enclosures',r'\b(?:ssd|drive|hdd)\s+enclosure\b'),('External Storage Drives',r'\bexternal\s+(?:hard|ssd|drive|hdd)\b|\bportable\s+(?:hdd|ssd)\b'),
 ('USB Flash Drives',r'\b(?:flash drive|pen drive|usb drive)\b'),('Memory Cards',r'\b(?:microsd|sdhc|sdxc|memory card)\b'),
 ('USB Hubs & Docks',r'\b(?:multiport hub|usb hub|docking station|multiport adapter)\b'),('Stylus Pens',r'\bstylus\b'),
 ('Phone Holders & Mounts',r'\b(?:mobile|phone)\s+holder\b'),('Power Banks',r'\bpower\s*bank\b'),
 ('Power Supplies',r'\bpower\s+supply\b|\bPSU\b'),('UPS & Voltage Stabilisers',r'\b(?:UPS|stabili[sz]er)\b'),
 ('Graphics Cards',r'\bgraphics?\s+card\b|\b(?:geforce|radeon)\b'),
 ('Motherboards',r'\bmotherboard\b'),('Processors',r'\b(?:processor|CPU)\b'),('Computer Memory (RAM)',r'\b(?:RAM|memory module)\b'),
 ('Computer Cases',r'\b(?:computer|PC|ATX|gaming)\s+(?:case|casing)\b'),('CPU Coolers',r'\b(?:cpu|processor|liquid)\s+cooler\b'),
 ('Cooling Fans',r'\b(?:case|cooling|chassis)\s+fan\b'),('Thermal Paste',r'\bthermal\s+(?:paste|compound)\b'),
 ('Solid-State Drives',r'\bSSD\b|\bsolid.state drive\b'),('Hard Drives',r'\bHDD\b|\bhard\s+(?:disk|drive)\b'),
 ('Monitors',r'\bmonitor\b'),('Printers',r'\bprinter\b'),('Ink & Toner',r'\b(?:toner cartridge|ink cartridge)\b'),
 ('Network Routers',r'\brouter\b'),('Network Switches',r'\b(?:network|ethernet|gigabit)\s+switch\b'),
 ('Wireless Network Adapters',r'\b(?:wifi|wi-fi|wireless)\s+(?:usb\s+)?adapter\b'),('Network Range Extenders',r'\b(?:range extender|wifi extender)\b'),
 ('Cables',r'\bcable\b'),('Adapters & Converters',r'\b(?:adapter|adaptor|converter)\b'),
 ('Eyelash Adhesives',r'\beyelash\s+glue\b'),('Mouth Fresheners',r'\bmouth spray\b'),
 ('Electric Kettles',r'\belectric kettle\b'),('Pest-Control Traps',r'\b(?:mouse trap|rat catch)\b'),('Hair Colouring Caps',r'\b(?:hair streaking|highlighting)\s+cap\b'),('Car Chargers',r'\bcar\s+charger\b'),
 ('Toothpaste',r'\btoothpaste\b'),('Mouth Fresheners',r'\bmouth freshener\b'),('Hair Brushes & Combs',r'\bhair\s+(?:round\s+)?brush\b|\bhair comb\b'),
 ('Electric Toothbrushes',r'\b(?:spinbrush|electric brush|electric toothbrush)\b'),('Toothbrushes',r'\btoothbrush\b'),('Contact Lens Solutions',r'\blens\s+(?:water|solution)\b'),
 ('Body Scrubs',r'\b(?:shower|foot)\s+scrub\b'),('Hair Styling Waxes',r'\bwax stick\b|\bhair\s+(?:styling\s+)?wax\b'),('Hair Creams',r'\bhair\s+(?:protein|cream)\b'),
 ('Honey',r'\bhoney\b'),('Herbal Massage Gels',r'\bpain relief\s+massage\s+gel\b'),('Baby Oils',r'\b(?:herbal )?oil for baby\b'),
 ('Face Mists & Toners',r'\bface\s+mist\b'),('Lip Balms',r'\blip\s+butter\b|\btinted\s+(?:colou?r\s+)?balm\b'),
 ('Massage Devices',r'\b(?:massager|massage gun|fascia gun)\b'),('Hair Dryers',r'\bhair\s*dryer\b'),
 ('Hair Straighteners',r'\b(?:straightener|straightening brush)\b'),('Hair Curlers',r'\b(?:hair curler|curling iron|curling wand)\b'),
 ('Trimmers & Clippers',r'\b(?:trimmer|hair clipper)\b'),('Electric Shavers',r'\b(?:electric shaver|foil shaver)\b'),
 ('Socks',r'\bsocks?\b'),('Handbags',r'\b(?:handbag|shoulder bag|crossbody bag|tote bag|clutch bag)\b'),
 ('Hair Colour & Henna',r'\b(?:henna|mehndi|mehendi)\b'),('Ubtan Powders',r'\bubtan\b'),
 ('Clay Face Masks',r'\b(?:multani|fuller.s earth|mud mask)\b'),('Rose Water & Face Mists',r'\brose\s*water\b|\bgulab\s*jal\b'),
 ('Herbal Supplements',r'\b(?:capsules?|gummies|shilajit)\b'),('Herbal Powders',r'\b(?:moringa|ashwagandha|amla|neem)\s+powder\b'),
 ('Attars & Perfume Oils',r'\battar\b|\bperfume oil\b'),('Bakhoor & Incense',r'\b(?:bakhoor|bakhour|incense)\b'),
 ('Body Sprays & Deodorants',r'\b(?:body spray|deodorant|roll.on)\b'),('Hair Oils',r'\b(?:hair|beard)\b.{0,15}\boil\b'),
 ('Herbal & Cosmetic Oils',r'\b(?:coconut|castor|almond|neem|kalonji|black seed|argan|jojoba|olive|mustard)\s+oil\b'),
 ('Essential Oils',r'\bessential\s+oil\b|\btea tree oil\b'),('Glycerin',r'\b(?:glycerin|glycerine)\b(?!\s+cream)'),
 ('Eyebrow Products',r'\b(?:eyebrow|brow pen|brow wax|brow gel)\b'),('Lipsticks',r'\blip\s+cream\b'),
 ('Face Scrubs & Exfoliators',r'\b(?:face|skin)\s+polish\b'),('Eye Creams',r'\bunder\s+eye\b.{0,20}\b(?:cream|gel)\b'),
]
NAMED_TYPES=[(label,re.compile(pattern,re.I)) for label,pattern in NAMED_TYPES]

# Reviewed primary objects precede compatibility targets, ingredients and generic features.
PRIMARY_OBJECTS=[
 ('CPU Coolers',r'\b(?:cpu|processor|liquid)\s+cooler\b'),
 ('Monitor Arms & Mounts',r'\bmonitor\s+(?:arm|mount|stand)\b'),
 ('Stylus Pens',r'\bstylus(?:\s+pen)?\b'),('Webcams',r'\bweb\s*cam\b'),
 ('Laptop Bags & Backpacks',r'\blaptop\s+(?:backpack|bag|sleeve)\b|\btop\s+load\s+laptop\s+bag\b'),
 ('Game Controllers',r'\b(?:dualsense|gamepad|wireless controller)\b'),
 ('Cables',r'\b(?:coiled|usb|type.c|hdmi|displayport|ethernet)\s+cable\b'),
 ('Keyboard & Mouse Sets',r'\b(?:wireless|desktop|bluetooth|keys s)\s+combo\b'),
 ('Eyelash Serums',r'\b(?:eyelash|lash)\s+serum\b'),
 ('False Eyelashes',r'\b(?:mink lashes|false eyelashes|false lashes)\b'),
 ('Multipurpose Makeup Pencils',r'\blip\s+liner\s+(?:plus|and|&)\s+eyebrow\b'),
 ('Lip & Cheek Colour',r'\blip\s*(?:&|and)\s*cheek\b'),
 ('Lip Colour Sets',r'\bdual[ -]ended\b.*\blipstick\b.*\blip\s+gloss\b'),
 ('Lip Oils',r'\blip\s+oil\b'),('Lipsticks',r'\blip\s+batom\s+crayon\b'),
 ('Face Powders',r'\b(?:loose|compact|setting)\s+powder\b'),
 ('Makeup Brushes',r'\b(?:face|makeup|paint)\s+brush\b'),
 ('Makeup Adhesives',r'\bglitter\s+glue\b'),
 ('Eyeshadow Palettes',r'\b(?:eye|eyeshadow)\s+palette\b'),
 ('Fragrance Sets',r'\bbody\s+mists?\s+set\s+of\b'),
]
PRIMARY_OBJECTS=[(label,re.compile(pattern,re.I)) for label,pattern in PRIMARY_OBJECTS]

def named_type(title,body):
    phrase=title.split(',')[0]
    for label,rule in PRIMARY_OBJECTS:
        match=rule.search(phrase)
        if match:return _quote(label,'name',phrase,match)
    # Don't turn a pet's baby-powder scented mist into perfume, or hair colour into a shaver.
    for label,rule in NAMED_TYPES:
        match=rule.search(phrase)
        if label=='Cables' and re.search(r'(?i)\bknit(?:ted)?\b',title):continue
        if label=='Saffron' and re.search(r'(?i)perfume|attar|cream|soap|face|mist',title):continue
        if label=='Game Controllers' and not re.search(r'(?i)game ?pad|joystick|hall effect|xbox|playstation|switch pro|8bitdo',title+' '+body[:500]):continue
        if match:return _quote(label,'name',phrase,match)
    # Stitching is a garment state; semi-stitched is not a fully stitched outfit.
    garment=title+' '+body[:600]
    if re.search(r'(?i)\bsemi[ -]?stitched\b',garment):return _quote('Semi-Stitched Suits','description',garment)
    if re.search(r'(?i)\bstitched\s+(?:\d[ -]?piece|collection|printed|embroidered|emb)\b',garment) and not re.search(r'(?i)\bun[ -]?stitched\b',garment):return _quote('Ready-to-Wear Outfits','description',garment)
    if re.search(r'(?i)\blength\s*:',body) and re.search(r'(?i)\bfabric\s*:',body) and re.search(r'(?i)\bmeters?\b',body):return _quote('Unstitched Fabric','description',body)
    return None

def _structured_clothing(title,description):
    raw=re.split(r'(?im)^\s*(?:Product Options|Available Options)\s*:',str(description),maxsplit=1)[0]
    body=plain(raw);context=title+' '+re.split(r'(?i)Note: Stitched Orders',body,maxsplit=1)[0]
    garment=re.search(r'(?i)\b(?:shirt|kurta|kameez|trouser|dupatta|frock|dress|maxi|gharara|sharara|suit|ensemble|outfit)\b',context)
    if not garment:return None
    named_count=re.search(r'(?i)\b([1234])\s*[- ]?\s*(?:pc|piece)s?\b',title)
    stated_count=re.search(r'(?i)\b(?:rtw|unstitched|stitched|suit|outfit)\s*[:-]?\s*([1234])\s*(?:pc|piece)s?\b',body)
    prose_count=re.search(r'(?i)\b([234])\s*[- ]?(?:pc|piece)s?\b.{0,70}\b(?:ensemble|suit|outfit|stitched|stiched)\b',body)
    count=int((named_count or stated_count or prose_count).group(1)) if named_count or stated_count or prose_count else None
    unstitched=bool(re.search(r'(?i)\bun[ -]?stitched\b',context))
    semi=bool(re.search(r'(?i)\bsemi[ -]?stitched\b',context))
    ready=bool(re.search(r'(?i)\brtw\b|ready[ -]to[ -]wear|\bstitched\b',re.sub(r'(?i)\b(?:un|semi)[ -]?stitched\b','',context)))
    if semi:return _quote('Semi-Stitched Suits','description',body)
    if unstitched and ready:return None
    components=sum(bool(re.search(r'(?im)^\s*'+word+r'\s*:',raw)) for word in ('shirt','trouser','dupatta','bottom','top'))
    if unstitched:return _quote('Unstitched Suits' if count and count>1 or components>=2 else 'Unstitched Fabric','description',body)
    if ready and count==1:
        if re.search(r'(?i)\bmaxi\b',title+' '+body[:500]):return _quote('Dresses','description',body)
        if re.search(r'(?im)^\s*(?:shirt|top)\s*:',raw):return _quote('Shirts','description',body)
        if re.search(r'(?im)^\s*(?:trouser|bottom)\s*:',raw):return _quote('Trousers','description',body)
    if ready and (count and count>1 or components>=2):return _quote('Ready-to-Wear Outfits','description',body)
    if count and count>1:return _quote('Clothing Sets','name',title)
    return None

def infer(name,description,website_path=''):
    title=plain(name);body=_product_prose(description)
    if re.search(r'(?i)\blotion\b',title) and re.search(r'(?i)\bface\b',title) and re.search(r'(?i)\bbody\b',title):return _quote('Face & Body Lotions','name',title)
    for label,pattern in [
        ('Forehead Jewellery',r'\bbindiya\b'),
        ('Hair Ties & Scrunchies',r'\bhair\s+ties\b|\bscrunchies\b'),
        ('Lip Sets',r'\blipstick\b.{0,30}\bset\b'),
        ('Hair Removal Sprays',r'\bhair\s+removal\s+spray\b'),
        ('Depilatory Waxes',r'\bwax\s+cream\b'),
    ]:
        if re.search(pattern,title,re.I):return _quote(label,'name',title)
    if not re.search(r'(?i)\b(?:strap|band|charger|cable|protector|case)\b',title):
        if re.search(r'(?i)\bsmart\s*watch\b',title+' '+body[:200]):return _quote('Smartwatches','name and description',title+' '+body[:200])
        if re.search(r'(?i)\b(?:earbuds?|earphones?|tws)\b',body[:800]) and re.search(r'(?i)\b(?:z\s*buds|earbuds?|arcade)\b',title):return _quote('Earphones/Earbuds','description',body[:800])
    garment=_structured_clothing(title,description)
    if garment:return garment
    if re.search(r'(?i)\bcharcoal\s+mask\b',title) and re.search(r'(?i)\bskin\b',body):return _quote('Skin Masks','description',body)
    if re.search(r'(?i)\beye\s+roller\b',title):return _quote('Eye Treatments','name',title)
    if re.search(r'(?i)\bcream\b',title) and re.search(r'(?i)\b(?:intimate areas|underarms|inner thighs)\b',body[:800]):return _quote('Body Creams','description',body)
    if re.search(r'(?i)\bcream\b',title) and re.search(r'(?i)\b(?:skin|skincare)\b',body[:800]) and not re.search(r'(?i)\b(?:face|facial|eye|lip|hand|foot|heel|body|hair)\b',title+' '+body[:300]) and not re.search(r'(?i)\bbaby\b',title):return _quote('Skin Moisturisers & Creams','description',body)
    if re.search(r'(?i)\bpack\b',title) and re.search(r'(?i)\b(?:combination|contains|includes)\b',body[:500]):
        bundle=_bundle(title+' Bundle',body)
        if bundle:return bundle
    if re.search(r'(?i)\blip\b.{0,35}\bserum\b',title):return _quote('Lip Treatments','name',title)
    explicit_bundle=bool(re.search(r'(?i)\bbundle\b|\b(?:kit|set|trio|duo|pack)\s+(?:of|featuring)\b',body[:250]))
    if explicit_bundle:
        hair=bool(re.search(r'(?i)\b(?:hair|shampoo|conditioner|scalp)\b',body[:1400]))
        skin=bool(re.search(r'(?i)\b(?:skin|face|facial|cream|serum|lotion)\b',body[:1400]))
        if hair and skin:return _quote('Personal Care Bundles','description',body)
        if skin:return _quote('Skin Care Bundles','description',body)
        if hair:return _quote('Hair Care Bundles','description',body)
    if not re.search(r'(?i)\btea\s+bags?\b',title) and re.search(r'(?i)\b(?:curled|tea)\s+leaves\b',body) and re.search(r'(?i)\btea\b',body):return _quote('Loose-Leaf Tea','description',body)
    # A paid product with a free gift retains the paid product's purpose.
    promotion=re.match(r'(?is)^buy\s+(.+?)\s*(?:&|and)\s*get\s+.+?\s+free$',title)
    if promotion:
        main=infer(promotion.group(1),'')
        if main:return main[0],main[1],'Paid product: '+promotion.group(1)+'; complimentary gift retained in description'
    primary=named_type(title,body)
    if primary and any(label==primary[0] for label,_ in PRIMARY_OBJECTS):return primary

    # Prefer the complete named outfit/accessory over individual components.
    named_rules=[
      ('Kurta & Trouser Sets',r'\bkurta\s+(?:and\s+|&\s*)?trousers?\b'),
      ('Kurta & Dupatta Sets',r'\b(?:kurta|shirt)\s+(?:and\s+|&\s*)?dupatta\b'),
      ('Kameez Shalwar Sets',r'\b(?:kameez\s+shalwar|shalwar\s+kameez)\b'),
      ('Sweatshirts',r'\bsweat\s+shirts?\b'),
      ('Cross-Body Bags',r'\bcross[ -]?body\s+bags?\b'),
      ('Shoulder Bags',r'\bshoulder\s+bags?\b'),('Bucket Bags',r'\bbucket\s+bags?\b'),
      ('Tunics',r'\btunics?\b'),('Jubbas & Thobes',r'\b(?:jubbas?|thobes?)\b'),
      ('Waistcoats',r'\bwaist\s*coats?\b'),('Sherwanis',r'\bsherwanis?\b'),
      ('Towel Sets',r'\btowel\s+sets?\b'),('Boxers & Trunks',r'\b(?:boxers?|trunks?)\b'),
      ('Hand Towels',r'\bhand\s+towels?\b'),('Bath Towels',r'\bbath\s+(?:towels?|sheets?)\b'),
      ('Hobo Bags',r'\bhobo\s+bags?\b'),('Cardholders',r'\bcard\s+holders?\b'),
      ('Tote Bags',r'\btote\s+bags?\b'),('Canvas Bags',r'\bcanvas\s+bags?\b'),('Clutches',r'\bclutch(?:es)?\b'),
      ('Polo Shirts',r'\bpolo\b'),('Briefs & Underwear',r'\bbriefs?\b'),
      ('Ponchos & Capes',r'\b(?:poncho|capelet)\b'),
      ('Shirts',r'\bbutton[ -]?down\b'),('Tops',r'\btops?\b'),

    ]
    if re.search(r'(?i)\bkameez\s+shalwar\b.*\bwaistcoat\b',title):
        return _quote('Kameez Shalwar & Waistcoat Sets','name',title)
    for label,pattern in named_rules:
        if label=='Tops' and re.search(r'(?i)\b(?:kurta|shirt|blouse|dress|co[ -]?ord)\b',title):continue
        if re.search(pattern,title,re.I):return _quote(label,'name',title)
    if re.search(r'(?i)\b(?:[23]\s*(?:pc|piece)|[23]-piece)\b',title) and not re.search(r'(?i)\bun[ -]?stitched\b',title):
        if re.search(r'(?i)\bstitched\b',title):return _quote('Stitched Outfit Sets','name',title)
    if re.search(r'(?i)\bun[ -]?stitched\s+fabric\b',title):return _quote('Unstitched Fabric','name',title)
    if re.search(r'(?i)\bdenim\b',title) and re.search(r'(?i)\b(?:pants?|trouser waist)\b',str(description or '')):return _quote('Denim Trousers','description',body)
    conflicting=bool(re.search(r'(?i)Product Clarification:|description refers to .*while this listing',body))
    if conflicting:body=''
    # Structured olfactory notes identify fragrances even when the name is opaque.
    raw=str(description or '')
    structured=all(re.search(r'(?im)^\s*'+('(?:hear(?:t)?|mid(?:dle)?)' if word=='heart' else word)+r'(?:\s+notes?)?\s*(?:[:：].*|\s*)$',raw) for word in ('top','heart','base'))
    if structured and (re.search(r'(?i)\b(?:fragrance|\d+\s*ml|gender)\b',raw) or re.search(r'(?im)^\s*top notes?\s*:',raw)):
        return _quote('Body Mists' if re.search(r'(?i)\bmist notes\b',raw) else 'Perfumes & Fragrances','description',body)
    if re.search(r'(?i)\bpads\b',title) and re.search(r'(?i)\b(?:period|heavy flow|menstrual|sanitary)\b',body):return _quote('Sanitary Pads','description',body)
    if re.search(r'(?i)\bpalette\b',title) and re.search(r'(?i)\b(?:eye looks|eyeshadow|eye makeup)\b',body):return _quote('Eyeshadow Palettes','description',body)
    if re.search(r'(?i)\bashwagandha\b',title) and re.search(r'(?i)\b(?:super|herbal)\s+powder\b',body):return _quote('Herbal Powders','description',body)
    if re.search(r'(?i)\bshort set\b',title) and re.search(r'(?i)jewellery care|jewelry care|gold platt?ed',raw):return _quote('Jewellery Sets','name',title)
    combined=title+' '+body[:1100]
    # Explicit intended-use wording disambiguates fabric shampoo, pet scents, and laundry wipes.
    cross_domain={'Pet Shampoos','Pet Deodorisers & Mists','Laundry Stain-Removal Wipes','Fabric Detergents'}
    for label,rule in PURPOSE_RULES:
        if label in cross_domain:
            match=rule.search(combined)
            if match:return _quote(label,'description',combined,match)
    named=named_type(title,body)
    technology={'Game Controllers','Keyboard & Mouse Sets','Laptop Bags & Backpacks','Laptop Chargers','Laptop Stands','Laptops','Headsets & Headphones','Mouse Pads','Computer Mice','Keyboards','Webcams','Microphones','Speakers','SSD Enclosures','External Storage Drives','USB Flash Drives','Memory Cards','USB Hubs & Docks','Stylus Pens','Phone Holders & Mounts','Power Banks','Power Supplies','UPS & Voltage Stabilisers','Graphics Cards','Motherboards','Processors','Computer Memory (RAM)','Computer Cases','CPU Coolers','Cooling Fans','Thermal Paste','Solid-State Drives','Hard Drives','Monitors','Printers','Ink & Toner','Network Routers','Network Switches','Wireless Network Adapters','Network Range Extenders','Cables','Adapters & Converters','Tablets','Wall Chargers','Security Cameras','Gaming Chairs','Gaming Consoles','Semi-Stitched Suits','Ready-to-Wear Outfits','Car Chargers'}
    if named and named[0] in technology:return named
    if named and named[0] in {'Shoe-Care Products','Car-Care Products'}:return named
    bundle=_bundle(title,body)
    if bundle:return bundle
    for label,rule in PURPOSE_RULES:
        if label in cross_domain:continue
        match=rule.search(title)
        if match:return _quote(label,'name',title,match)
    if named and named[0]=='Herbal Supplements':return named
    explicit=_infer_type(title,'')
    if explicit:return NORMAL_LABELS.get(explicit[0],explicit[0]),explicit[1],explicit[2]
    if named:return named
    if re.search(r'(?i)\bsoap\b',title):return _quote('Bath Soaps','name',title)
    if re.search(r'(?i)\bcream\b',title) and re.search(r'(?i)\bface\s*,?\s*hand\s*(?:&|and)\s*body\b',body):return _quote('Face & Body Creams','description',body)
    if re.search(r'(?i)\bcream\b',title) and re.search(r'(?i)\b(?:face|facial|skin|skincare)\b',body):return _quote('Face Moisturisers & Creams','description',body)
    if all(re.search(r'(?i)\b'+word+r'\s+notes?\b',body) for word in ('top','heart','base')):return _quote('Perfumes & Fragrances','description',body)
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
    opening=named_type(body[:450],'')
    if opening and opening[0] in {'Jewellery Sets','Bangles & Karas','Bracelets','Anklets','Pendants & Lockets','Necklaces','Jewellery Chains','Nose Jewellery','Hand Harnesses','Jhumka Earrings','Hair Clips & Pins','Hair Ties & Accessories','Forehead Jewellery'}:
        return opening[0],'inferred_description','description: '+body[:300]
    result=_infer_type(title,body)
    if result:
        label,source,quote=result
        return NORMAL_LABELS.get(label,label),source,quote
    # "Fragrance" in an INCI list is not perfume. Only explicit product prose can support this fallback.
    if re.search(r'(?i)\b(?:is|a|an|this)\b.{0,50}\b(?:perfume|fragrance|scent)\b|\beau de parfum\b',body) and not re.search(r'(?i)\b(?:wash|cream|lotion|soap|shampoo|wipes|colou?r)\b',title):
        return _quote('Perfumes & Fragrances','description',body)
    return None
