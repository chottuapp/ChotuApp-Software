"""804 Audit: independent all-row description/category and store identity gate.
Bounded automatic checks, not a claim of human semantic review. Uncertain files HOLD.
"""
import hashlib,html,json,re
from datetime import datetime,timezone
from pathlib import Path
from urllib.parse import urlsplit
from openpyxl import load_workbook
VERSION='804-audit-v1'
# Independent reviewer vocabulary; do not call the classification implementation.
TYPES=[
 ('laptop',r'\blaptops?\b',r'\blaptops?\b'),
 ('printer toner',r'\b(?:printer\s+toner|toner\s+(?:reload|cartridge))\b',r'\b(?:printer|toner|cartridge)\b'),
 ('keyboard',r'\bkeyboards?\b',r'\bkeyboards?\b'),
 ('earrings',r'\b(?:earrings?|hoops?|studs)\b',r'\b(?:earrings?|hoops?|studs)\b'),
 ('necklace',r'\bnecklaces?\b',r'\bnecklaces?\b'),
 ('body wash',r'\b(?:body\s+wash|shower\s+gel)\b',r'\b(?:body\s+wash|shower\s+gel)\b'),
 ('hand wash',r'\bhand\s+wash\b',r'\bhand\s+wash\b'),
 ('face wash',r'\b(?:face|facial)\s+wash\b',r'\b(?:face|facial)\s+(?:wash|cleanser)\b'),
 ('hair shampoo',r'\bshampoo\b',r'\bshampoo\b'),
 ('hair conditioner',r'\b(?:hair\s+)?conditioner\b',r'\bconditioner\b'),
 ('hair oil',r'\bhair\s+oil\b',r'\bhair\s+oil\b'),
 ('fragrance',r'\b(?:perfume|eau\s+de\s+parfum|fragrance\s+mist)\b',r'\b(?:fragrance|perfume)\b'),
 ('sunscreen',r'\b(?:sunscreen|sunblock)\b',r'\b(?:sunscreen|sunblock|sun\s+protection)\b'),
 ('lipstick',r'\b(?:lipstick|lip\s+paint)\b',r'\b(?:lipstick|lip\s+colour|lip\s+color)\b'),
 ('mascara',r'\bmascara\b',r'\bmascara\b'),
 ('foundation',r'\bfoundation\b',r'\bfoundation\b'),
 ('lip gloss',r'\blip\s*gloss\b',r'\blip\s*gloss\b'),
 ('lip liner',r'\blip\s+liners?\b',r'\blip\s+liners?\b'),
 ('lip balm',r'\blip\s+balms?\b',r'\blip\s+balms?\b'),
 ('eyeshadow',r'\beye\s*shadow\b',r'\beye\s*shadow\b'),
 ('eyeliner',r'\b(?:eye\s*liner|kajal|kohl)\b',r'\b(?:eye\s*liner|kajal|kohl)\b'),
 ('concealer',r'\bconcealers?\b',r'\bconcealers?\b'),
 ('makeup brush',r'\bmakeup\s+brush(?:es)?\b',r'\bmakeup\s+brush(?:es)?\b'),
 ('makeup sponge',r'\b(?:makeup|beauty)\s+sponges?\b',r'\b(?:makeup|beauty)\s+sponges?\b'),
 ('hair serum',r'\bhair\s+(?:growth\s+)?serum\b',r'\bhair\s+serum\b'),
 ('face serum',r'\b(?:facial|face)\s+serum\b',r'\b(?:facial|face)\s+serum\b'),
 ('body lotion',r'\bbody\s+(?:lotion|milk)\b',r'\bbody\s+(?:lotion|milk)\b'),
 ('face toner',r'\b(?:face|facial)\s+toner\b',r'\b(?:face|facial)\s+toner\b'),
 ('garam masala',r'\bgaram\s+masala\b',r'\bgaram\s+masala\b'),
 ('tea bags',r'\btea\s+bags?\b',r'\btea\s+bags?\b'),
 ('pizza cheese',r'\bpizza\s+cheese\b',r'\bpizza\s+cheese\b'),
 ('loose leaf tea',r'\btea\s+leaf\s+blend\b|\bloose[ -]leaf\s+tea\b',r'\bloose[ -]leaf\s+tea\b'),
 ('blush',r'\bblush(?:er)?s?\b',r'\bblush(?:er)?s?\b'),
 ('mozzarella',r'\bmozzarella\b',r'\bmozzarella\b'),
 ('unstitched',r'\bun[ -]?stitched\b',r'\bun[ -]?stitched\b'),
 ('jeans',r'\bjeans?\b|\bdenim\s+(?:pants?|trousers?)\b',r'\b(?:jeans?|denim|trousers?)\b'),
 ('hoodie',r'\bhood(?:ie|ies)\b',r'\bhood(?:ie|ies)\b'),
 ('kurta',r'\bkurt[ai]s?\b',r'\b(?:kurt[ai]s?|ready.to.wear|suits?|outfits?)\b'),
 ('trousers',r'\b(?:trousers?|pants?|culottes?|shalwars?)\b',r'\b(?:trousers?|pants?|culottes?|shalwars?|joggers?)\b'),
]
TYPES=[(name,re.compile(a,re.I),re.compile(b,re.I)) for name,a,b in TYPES]
CARE=re.compile(r'\b(?:care instructions|how to use|directions|usage|precautions|avoid contact|apply to|wash with)\b',re.I)
def plain(value):return re.sub(r'\s+',' ',html.unescape(re.sub('<[^>]*>',' ',str(value or '')))).strip()
def tokens(value):return set(re.findall(r'\d+(?:[.,]\d+)?',plain(value)))
def issues_for(row,source=None):
 name=plain(row.get('name'));description=plain(row.get('description'));category=plain(row.get('Category'));issues=[]
 if not name:issues.append('Missing product name')
 if not description or len(re.findall(r'\b\w+\b',description))<5 or description.rstrip('.')==name.rstrip('.'):
  issues.append('Description lacks enough product-specific content for review')
 if re.search(r'\b(?:lorem ipsum|description coming soon|no description available)\b',description,re.I):issues.append('Placeholder description')
 if not category:issues.append('Category blank or unresolved')
 if category.lower() in {'accessories','clothing','beauty','skin care','hair care','food','sale','new arrivals','collection','women','men','kids','general','products'}:issues.append('Category is too broad or promotional for product-purpose classification')
 if category and plain(row.get('brand')) and category.casefold()==plain(row.get('brand')).casefold():issues.append('Brand name used as product Category')
 if re.search(r'Product Clarification:|description refers to .*while this listing',description,re.I):issues.append('Conflicting source description requires attention')
 if source and not tokens(source.get('description'))<=tokens(description):issues.append('Description lost source numeric facts')
 body=CARE.split(plain((source or row).get('description')),1)[0][:700]
 category_review=category
 for plural,singular in {'glosses':'gloss','washes':'wash','shampoos':'shampoo','conditioners':'conditioner','mascaras':'mascara','foundations':'foundation','serums':'serum','toners':'toner','lotions':'lotion','concealers':'concealer','eyeliners':'eyeliner','eyeshadows':'eyeshadow','lipsticks':'lipstick'}.items():category_review=re.sub(r'\b'+plural+r'\b',singular,category_review,flags=re.I)
 primary=name or body
 found=[(kind,allowed) for kind,pattern,allowed in TYPES if pattern.search(primary)]
 if not found:found=[(kind,allowed) for kind,pattern,allowed in TYPES if pattern.search(body[:260])]
 bundle=bool(re.search(r'\b(?:bundle|combo|kit|duo|deal|set of)\b',name,re.I))
 if bundle and category:
  if not re.search(r'\b(?:bundle|combo|kit|set|pack|outfit|suit)s?\b',category,re.I):issues.append('Bundle appears classified as a single component')
  families={'dairy':r'cheese|milk|butter|ghee|dairy|yogh?urt|raita|lassi','makeup':r'lipstick|lip\s*gloss|eye\s*shadow|mascara|foundation|concealer|makeup','hair':r'hair|shampoo|conditioner','skin':r'skin|face|facial|serum|cream|lotion','spice':r'spice|masala|cumin|coriander|turmeric'}
  for family,pattern in families.items():
   if re.search(r'\b'+family+r'\b',category,re.I) and not re.search(pattern,name+' '+body,re.I):issues.append('Bundle family and product contents disagree')
  if category.lower().startswith('hair') and found and not found[0][0].startswith('hair'):issues.append('Hair bundle category conflicts with primary product purpose')
  if re.search(r'\b(?:skin|face)',category,re.I) and found and found[0][0] in ('lipstick','lip gloss','lip liner','eyeshadow','eyeliner','mascara','foundation','concealer'):issues.append('Cosmetics bundle incorrectly classified as skincare')
 elif found and category:
  if not found[0][1].search(category_review):issues.append('Primary product type and Category disagree: '+found[0][0])
 elif category:
  anchors=[w if w.endswith('ss') else w[:-2] if w.endswith(('ches','shes','xes','sses','zes')) else w[:-1] if w.endswith('s') else w for w in re.findall('[a-z]{3,}',category.lower()) if w not in {'and','for','with','care','sets','set'}]
  evidence=(name+' '+body).lower()
  if not anchors or not all(re.search(r'\b'+re.escape(w)+r'(?:s|es)?\b',evidence) for w in anchors):issues.append('Category lacks clear product-purpose evidence; manual review required')
 if re.search(r'\b[23]\s*[- ]?(?:pc|piece)',name,re.I) and re.search(r'\b(?:kurtas?|shirts?|trousers?|dupattas?)\b',category,re.I) and not re.search(r'suit|set|outfit|ready',category,re.I):issues.append('Multi-piece outfit may be classified as one component')
 return list(dict.fromkeys(issues))

def rows(path):
 book=load_workbook(path,read_only=True,data_only=False)
 try:
  sheet=book['Products'];iterator=sheet.iter_rows(values_only=True);headers=next(iterator)
  for values in iterator:
   if any(value is not None for value in values):yield dict(zip(headers,values))
 finally:book.close()

def run(path,store,codes,hosts,*,source=None):
 path=Path(path);findings=[];expected=codes.get(store);seen=set();count=0;finding_count=0
 originals={str(row.get('product_id')):row for row in rows(source)} if source else {}
 for row in rows(path):
  count+=1;pid=str(row.get('product_id') or '');issues=issues_for(row,originals.get(pid))
  if not pid or pid in seen:issues.append('Missing or duplicate product ID')
  seen.add(pid)
  if expected and str(row.get('shop_code') or '')!=expected:issues.append('Shop code missing, mixed or not confirmed for this store')
  if store=='LAAM' and not re.search(r'cloth|suit|unstitched|stitched|wear|kurta|kurti|dress|trouser|shirt|jean|hood|jacket|shawl|dupatta|abaya|kaftan|saree|lehenga|sweater|cardigan|jogger|short|polo|legging|coat|outfit|gown|skirt|shalwar|pant|frock|top|sweatshirt',str(row.get('Category') or ''),re.I):issues.append('Rule LAAM: clothing purpose not confirmed')
  url=urlsplit(str(row.get('source_url') or ''))
  if url.scheme!='https' or (url.hostname or '').lower().removeprefix('www.') not in hosts:issues.append('Store source host mismatch')
  if plain(row.get('Category')).casefold()==store.casefold():issues.append('Store name used as product Category')
  if issues:
   finding_count+=1
   if len(findings)<100:findings.append({'product_id':pid,'issues':issues})
 if expected and list(codes.values()).count(expected)>1:finding_count+=1;findings.append({'product_id':None,'issues':['Shop code assigned to multiple stores; identity review required']})
 if not expected:finding_count+=1;findings.append({'product_id':None,'issues':['Shop code not confirmed; Drive replacement held']})
 if not count:finding_count+=1;findings.append({'product_id':None,'issues':['Empty workbook']})
 if originals and set(originals)!=seen:finding_count+=1;findings.append({'product_id':None,'issues':['Source/output product identity mismatch']})
 return {'name':'804 Audit','version':VERSION,'store':store,'shop_code':expected,'status':'pass' if not finding_count else 'hold','products_checked':count,'findings_count':finding_count,'findings':findings,'details_truncated':finding_count>len(findings),'workbook_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'checked_utc':datetime.now(timezone.utc).isoformat(),'review_scope':'Every product description, independent product-type/category checks, source facts and confirmed shop-code identity. Ambiguity is held; this is not human semantic review or proof of full website coverage.'}
