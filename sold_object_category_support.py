"""Primary sold-object evidence, excluding styling suggestions and policy boilerplate."""
import html,re
FOOTWEAR=[('Khussas',r'\bkhuss(?:a|as|ay|ey)\b'),('Chappals',r'\b(?:chappals?|chapals?|peshawari)\b'),('Heels & Pumps',r'\b(?:heels?|pumps?|court shoes?)\b'),('Sandals & Slides',r'\b(?:sandals?|slides?|flip[ -]flops?)\b'),('Flats',r'\b(?:ballet (?:flats?|shoes?)|flats?)\b'),('Loafers',r'\bloafers?\b'),('Sneakers & Trainers',r'\b(?:sneakers?|trainers?)\b'),('Boots',r'\bboots?\b'),('Mules',r'\bmules?\b'),('Slippers',r'\bslippers?\b')]
EXACT={'khussa':'Khussas','khussas':'Khussas','chappal':'Chappals','chappals':'Chappals','sandals':'Sandals & Slides','sandal':'Sandals & Slides','slides':'Sandals & Slides','sandals & slides':'Sandals & Slides','heels':'Heels & Pumps','pumps':'Heels & Pumps','heels & pumps':'Heels & Pumps','flats':'Flats','ballet flats':'Flats','loafers':'Loafers','boots':'Boots','mules':'Mules','sneakers':'Sneakers & Trainers','sneakers & trainers':'Sneakers & Trainers','slippers':'Slippers'}
def plain(v):return re.sub(r'\s+',' ',html.unescape(re.sub(r'<[^>]*>',' ',str(v or '')))).strip()
def primary_prose(body):
 text=html.unescape(str(body or ''));text=re.sub(r'</(?:p|li|h[1-6])\s*>|<br\s*/?>','\n',text,flags=re.I);text=re.sub(r'<[^>]*>',' ',text)
 text=re.split(r'(?im)(?:^|\n)\s*(?:delivery\s*[I|/]?\s*return|refund policy|return.{0,10}exchange|how to style|styling tips|care instructions|complete the look)\b',text)[0]
 # Suggestions name companion clothes, not included/sold objects. Preserve preceding identity prose.
 text=re.sub(r'(?i)\b(?:wear (?:yours|it|them|these)|can be worn|pair (?:it|them|yours|these)|paired|style (?:it|them|yours|these))\s+with\b[^.!?\n]*','',text)
 text=re.sub(r'(?i)\b(?:pair(?:s|ed)?|wear|worn|(?<!in )style(?:d)?)\s+with\b[^.!?\n]*','',text)
 text=re.sub(r'(?i)\b(?:wear|pair|(?<!in )style)\s+(?:this|these|your|our|the)\b[^.!?\n]{0,70}?\s+with\b[^.!?\n]*','',text)
 return text.strip()
def source_object(name,description,product_type='',website_path=''):
 title=plain(name);body=plain(primary_prose(description))
 # A corroborated sold object outranks erroneous merchant collection/type labels.
 direct=explicit_object(name,description)
 if direct:return direct
 if re.search(r'\b(?:cream|lotion|scrub|mask|brush|polish|cleaner|charm|insoles?|shoe[ -]?laces?|replacement laces?|shoe care|rack|organizer|holder)\b',title,re.I):return None
 kind=EXACT.get(plain(product_type).casefold())
 if kind:return kind,'source_product_type','Exact merchant product type: '+plain(product_type)
 for part in reversed(str(website_path or '').split(' > ')):
  kind=EXACT.get(plain(part).casefold())
  if kind:return kind,'verified_source_category','Actual source category: '+website_path
 if re.search(r'\b(?:shirts?|kurtas?|trousers?|pants|jeans|dresses?|jackets?|socks?|stockings?)\b',title,re.I):return None
 for field,text in [('name',title),('description',body[:1000])]:
  matches=[(m.start(),label,m) for label,pattern in FOOTWEAR if (m:=re.search(pattern,text,re.I))]
  for _,label,match in sorted(matches,key=lambda v:v[0]):
   if match:
    if label=='Heels & Pumps' and not re.search(r'\b(?:shoes?|footwear|soles?|footbed|ankle|straps?|sandals?|pumps?|heels)\b',title+' '+body,re.I):continue
    return label,'source_sold_object_'+field,field+': '+text[max(0,match.start()-70):match.end()+130]
 return None

# Exact merchant types extend object recovery beyond footwear. Generic ranges,
# brands, colours and styling prose are deliberately absent.
EXACT.update({'shirt':'Shirts','shirts':'Shirts','trousers':'Trousers','jeans':'Jeans',
 'shampoo':'Shampoos','toothpaste':'Toothpastes','toothbrush':'Toothbrushes',
 'face wash':'Face Wash','face serum':'Face Serums','foundation':'Foundations',
 'lipstick':'Lipsticks','mascara':'Mascaras','notebook':'Notebooks','backpack':'Backpacks',
 'lunch box':'Lunch Boxes','water bottle':'Water Bottles'})

def correct_audience_category(row,category):
 """Repair existing gender labels only; never infer audience from brand/colour."""
 label=str(category or '')
 prefix=re.match(r"(?i)^(women(?:['’]?s)?|ladies|female|men(?:['’]?s)?|gents|male)\s+(.+)$",label)
 if not prefix:return label
 from urllib.parse import urlsplit
 fields=[str(row.get('name') or ''),str(row.get('source_product_type') or '')]
 path=str(row.get('website_category_path') or '')
 if row.get('website_category_status') in {'verified_navigation_membership','verified_product_breadcrumb'} and row.get('website_category_checked_at') and urlsplit(str(row.get('source_url') or '')).hostname and (urlsplit(str(row.get('website_category_source_url') or '')).hostname or '').removeprefix('www.')==(urlsplit(str(row.get('source_url') or '')).hostname or '').removeprefix('www.'):
  fields.extend(path.split(' > '))
 evidence=' '.join(fields)
 male=bool(re.search(r"\b(?:men(?:['’]?s)?|gents|male)\b",evidence,re.I))
 female=bool(re.search(r"\b(?:women(?:['’]?s)?|ladies|female)\b",evidence,re.I))
 if male==female:return prefix[2] # unknown/conflicting audience: keep the object neutral
 return ("Men's " if male else "Women's ")+prefix[2]


def explicit_object(name,description):
 title=plain(name);body=plain(primary_prose(description))
 from product_description_support import evidence_text
 lines=evidence_text(description)
 if re.search(r'\b(?:replacement|sewing pattern|case for|cover for)\b',title,re.I):return None
 result=None
 primary_forms=[('Costumes',r'\bcostume\b(?!\s+jewel)'),('Sunglasses',r'\bsunglasses\b'),('Keychains',r'\bkeychain\b'),('Baby Walkers',r'\bbaby walker\b'),('Baby Bath Gloves',r'\bbaby bath gloves\b'),
  ('Handheld Fans',r'\b(?:hand fan|handheld fan)\b'),('Desk Lamps',r'\bdesk lamp\b'),('Decorative Lights',r'\b(?:roof light|moon lamp|night light)\b'),('Insect Killers',r'\binsect killer\b'),
  ('Fidget Pouches',r'\bpop it\b.*\b(?:zipper bag|pouch)\b'),('Fidget Toys',r'\b(?:push pop it|pop it bubble)\b'),
  ('Remote-Control Vehicles',r'\bremote control\b.*\b(?:car|truck|bus|tank|jeep|motorcycle)\b'),('Robot Toys',r'\b(?:robot dog|robot toy|robot dinosaur)\b'),
  ('Plush Toys',r'\b(?:plush|soft toy|stuffed toy)\b'),('Construction Toys',r'\b(?:building blocks|building bricks|construction toy)\b'),
  ('Drawing Boards',r'\b(?:drawing (?:board|tablet)|writing (?:board|tablet))\b'),('Colouring Paper',r'\b(?:coloring|colouring|drawing)\b.*\b(?:roll|paper)\b'),('Scratch Art Paper',r'\bscratch paper\b'),
  ('Art & Craft Sets',r'\b(?:art|craft|painting) (?:set|kit)\b'),('Xylophones',r'\bxylophone\b'),('Pianos',r'\bpiano\b'),('Bubble Toys',r'\bbubble (?:gun|machine|blower)\b'),
  ('Money Boxes',r'\b(?:piggy bank|money box|atm machine)\b'),('Baby Rattles',r'\b(?:baby rattle|rattle toy)\b'),('Toy Vehicles',r'\btoy (?:car|truck|bus|train|plane)\b'),
  ('Bath Toys',r'\bbath toy\b'),('Animal Toys',r'\banimal\b.*\btoy\b'),('Activity Tables',r'\blearning table\b'),('Handheld Games',r'\bhand game\b')]
 primary_title=re.split(r'\b(?:with|for)\b',title,maxsplit=1,flags=re.I)[0]
 if re.search(r'\b(?:magic|foldable) phone\b',primary_title,re.I) and re.search(r'\blcd drawing board\b',title,re.I) and re.search(r'\bdraw\w*\b',body,re.I):return 'Drawing Boards','corroborated_primary_sold_object','Source explicitly describes the drawing function of its phone-shaped LCD board.'
 wearable=bool(re.search(r'\b(?:t[ -]?shirt|shirt|kurta|trouser|jeans|dress|hoodie|sweater|earrings?|pendant|necklace|bracelet|socks|backpack|handbag|wallet)\b',primary_title,re.I))
 for label,pattern in primary_forms:
  if not wearable and re.search(pattern,primary_title,re.I):return label,'corroborated_primary_sold_object','Explicit sold form in original product title; incidental components and character names do not override it.'
 if re.search(r'\bride[ -]on (?:car|truck|bike|motorcycle)\b',title,re.I):result='Ride-On Vehicles'
 if re.search(r'\bbeauty set\b',title,re.I) and re.search(r'\btoy collection\b',body,re.I) and re.search(r'\bset contents\b',body,re.I):result='Beauty Play Sets'
 if re.search(r'\bmagic slate\b',title,re.I) and re.search(r'\b(?:drawing|writing|write)\b',body,re.I):result='Drawing Boards'
 if re.search(r'\bchef\b.*\bbagpack\b',title,re.I) and re.search(r'\b(?:kitchen|cooking|pretend)\b',body,re.I):result='Kitchen Play Sets'
 if re.search(r'\b(?:children|princess)\b.*\b(?:cosmetic|makeup) set\b',title,re.I):result='Kids Makeup Sets'
 if result:return result,'corroborated_primary_sold_object','Explicit source sold form and matching supplied purpose; no components or quantities invented.'
 if re.search(r'\bbaby\b',title,re.I):
  for label,noun in [('Baby Soaps',r'\bsoap\b'),('Baby Lotions',r'\blotion\b'),('Baby Washes',r'\bwash\b'),('Baby Creams',r'\bcream\b')]:
   if re.search(noun,title,re.I):result=label;break
 if not result and re.search(r'\bfix\b',title,re.I) and re.search(r'\bmist\b',body,re.I) and re.search(r'\bset makeup\b',body,re.I):result='Makeup Setting Mists'
 if not result and re.search(r'\bcc\s*cr(?:eam|eme)\b',title,re.I):result='CC Creams'
 if not result and re.search(r'\bglossy balm\b',title,re.I) and re.search(r'\blip balm\b',body,re.I):result='Lip Balms & Treatments'
 if not result and re.search(r'\bgloss\b',title,re.I) and re.search(r'\bgloss[ -]lipstick hybrid\b',body,re.I):result='Gloss Lipsticks'
 if not result and re.search(r'\boil\b',title,re.I) and re.search(r'\blips\b',body[:700],re.I) and not re.search(r'\bhair\b',title,re.I):result='Lip Oils'
 if not result and re.search(r'\bset\b',title,re.I) and re.search(r'\bmakeup tool (?:collection|set)\b',body,re.I):result='Makeup Tool Sets'
 if not result and re.search(r'\b(?:kit|set|palette)\b',title,re.I) and re.search(r'\b(?:collection of highlighters|highlighter shades)\b',body,re.I):result='Highlighter Sets'
 if not result and re.search(r'\bhair oil\b',title,re.I):result='Hair Oils'
 if not result and re.search(r'\bset\b',title,re.I) and re.search(r'\bnecklace set\b',body,re.I):result='Necklace Sets'
 if not result and re.search(r'\beye cream\b',title,re.I):result='Eye Creams'
 if not result and re.search(r'\bblush\s*(?:and|&)\s*bronzer\b',title,re.I):result='Blush & Bronzer'
 if not result and re.search(r'\bfoundcealer\b',title,re.I) and re.search(r'\bfoundation\b',body,re.I) and re.search(r'\bconcealer\b',body,re.I):result='Foundation & Concealer Sticks'
 if not result and re.search(r'\bmoisturizing cream\b',title,re.I) and re.search(r'\bface\s*(?:&|and)\s*body\b',body,re.I):result='Face & Body Creams'
 if not result and re.search(r'\b(?:kabuki brush|brush set)\b',title,re.I):result='Makeup Brush Sets' if re.search(r'\bset\b',title,re.I) else 'Makeup Brushes'
 if not result and re.search(r'\b(?:set|kit|pack|duo|palette)\b',title,re.I):
  terms={'mascara':r'\bmascara\b','blush':r'\bblush(?:er)?\b','bronzer':r'\bbronzer\b','highlighter':r'\bhighlighter\b','eyeshadow':r'\beye\s*shadow\b','eyeliner':r'\b(?:eyeliner|khol|kohl|eye pencil)\b','lip liner':r'\blip liner\b','lip gloss':r'\blip\s*(?:gloss|luminizer)\b','lipstick':r'\blipstick\b','hair oil':r'\bhair oil\b','hair mask':r'\bhair mask\b','lip oil':r'\blip oil\b'}
  supplied={key for key,pattern in terms.items() if re.search(pattern,title+' '+body,re.I)}
  explicit_pack=bool(re.search(r'\b(?:includes?|contains?|contents|features|featuring)\b|brings together',body,re.I)) or sum(bool(re.search(pattern,title,re.I)) for pattern in terms.values())>=2
  explicit_pack=explicit_pack or bool(re.search(r'\b(?:face|cheek) palette\b',title,re.I))
  if len(supplied)>=2 and explicit_pack:
   result='Hair & Lip Care Sets' if any(x.startswith('hair') for x in supplied) and any(x.startswith('lip') for x in supplied) else 'Hair Care Sets' if any(x.startswith('hair') for x in supplied) else 'Lip Sets' if all(x.startswith('lip') for x in supplied) else 'Makeup Palettes' if re.search(r'\bpalette\b',title,re.I) and 'eyeshadow' in supplied else 'Face Palettes' if re.search(r'\bpalette\b',title,re.I) else 'Makeup Sets'
  if not result and re.search(r'\bhand care\b',title,re.I) and re.search(r'\b(?:hand wash|hand lotion|hand cream)\b',body,re.I):result='Hand Care Sets'
 if not result and re.search(r'\bset\b',title,re.I) and re.search(r'\bnecklace\b',body,re.I) and re.search(r'\bearrings?\b',body,re.I) and not re.search(r'\b(?:without|not included|sold separately)\b',body,re.I):result='Jewellery Sets'
 if not result:
  named=[('Lunch Boxes',r'\blunch box\b'),('Pen & Stationery Organizers',r'\bstationery organizer\b'),('Beanies',r'\bbeanie\b'),('BB Creams',r'\bbb\s*cream\b'),('Lipsticks',r'\blipstick\b'),('Contour Sticks',r'\bcontour stick\b'),('Brow & Lash Serums',r'\bbrow\s*(?:&|and)\s*lash serum\b')]
  for label,pattern in named:
   if re.search(pattern,title,re.I) and not re.search(r'\b(?:case|holder|pouch|bag)\b',title,re.I):result=label;break
  if not result and re.search(r'\b(?:conditioner|condtnr)\b',title,re.I) and re.search(r'\bhair\b',body,re.I):result='Hair Conditioners'
 if result:return result,'corroborated_primary_sold_object','Explicit source sold form and supplied details; pack contents, purpose and quantities are preserved.'
 if re.search(r'\beyebrow\b',title,re.I) and re.search(r'\beyeliner\b',title,re.I) and re.search(r'\bpencil\b',title,re.I):result='Eyebrow & Eyeliner Pencils'
 elif re.search(r'\bscalp serum\b',title,re.I):result='Scalp Serums'
 elif re.search(r'\bbaby soap\b',title,re.I):result='Baby Soaps'
 elif re.search(r'\blip therapy\b',title,re.I) and re.search(r'\blip balm\b',body,re.I):result='Lip Balms & Treatments'
 elif re.search(r'\bshackets?\b',title,re.I):result='Shackets'
 elif re.search(r'\bsweatpants\b',title,re.I):result='Sweatpants'
 elif re.search(r'\btracksuit\b',title,re.I):result='Tracksuits'
 elif re.search(r'\b(?:lehenga|lehnga) set\b',title,re.I):result='Lehenga Sets'
 elif re.search(r'\bmaxi\b',title,re.I) and re.search(r'\b(?:maxi|dress|frock)\b',body,re.I):result='Maxi Dresses'
 elif re.search(r'\bsharara set\b',title,re.I) and re.search(r'\b(?:shirt|kurta)\b',body,re.I):result='Clothing Sets'
 elif re.search(r'\b(?:2|two|3|three)[ -]*(?:pcs?|pieces?)\b.*\bsuit\b',title,re.I) and re.search(r'\bshirt\b',body,re.I) and re.search(r'\btrouser\b',body,re.I):result='Clothing Sets'
 elif re.search(r'\bdenim\b',title,re.I) and re.search(r'\btrousers?\b',title,re.I):result='Jeans'
 elif re.search(r'\beye\s*shadow\b',title,re.I) and re.search(r'\bpalette\b',title+' '+body,re.I):result='Eyeshadow Palettes'
 elif re.search(r'\bbrush set\b',title,re.I):result='Makeup Brush Sets'
 elif re.search(r'\blip tint\b',title,re.I):result='Lip Tints'
 elif re.search(r'\b(?:gloss|glossy balm)\b',title,re.I) and re.search(r'\blips?\b',body,re.I):result='Lip Glosses'
 elif re.search(r'\b(?:eyeliner|glitter liner|eye pencil)\b',title,re.I):result='Eyeliners'
 elif re.search(r'\blip (?:oil|drip)\b',title,re.I):result='Lip Oils'
 elif re.search(r'\beye cream\b',title,re.I):result='Eye Creams'
 elif re.search(r'\bSPF\s*\d+',title,re.I) and re.search(r'\b(?:sun protection|sunscreen|UVA|UVB)\b',body,re.I) and not re.search(r'\b(?:foundation|lipstick|powder)\b',title,re.I):result='Sunscreens'

 elif re.search(r'\b(?:jewellery|jewelry)\b.*\bset\b',title,re.I) and re.search(r'\b(?:necklace|earrings?|ring|bracelet)\b',body,re.I):result='Jewellery Sets'
 if not result:
  # Explicit source footwear title plus source footwear construction, never studs/care.
  for label,pattern in FOOTWEAR:
   if re.search(pattern,title,re.I) and re.search(r'\b(?:sole|soles|footbed|upper|lace.up|ballet flats|boots|sandals|shoes)\b',body,re.I):result=label;break
 if not result and not re.search(r'\b(?:set|kit|palette|brush|case|holder|cream|serum|remover|cleanser|lotion|wash|soap|conditioner)\b',title,re.I):
  # Explicit self-description in the primary paragraph, not care/styling/ingredients.
  first=body[:700]
  for label,pattern in [('Lipsticks',r'\blipstick\b'),('Lip Oils',r'\blip oil\b'),('Eyeliners',r'\beyeliner\b'),('Hair Masks',r'\bhair mask\b'),('Hair Oils',r'\bhair oil\b'),('False Eyelashes',r'\bfalse eyelashes\b'),('Makeup Setting Sprays',r'\b(?:setting spray|makeup fixer|fixing mist)\b'),('Foundation Enhancers',r'\bfoundation enhancer\b')]:
   match=re.search(pattern,first,re.I)
   if match and not re.search(r'\b(?:removes?|removing|mix|mixed|mixing|pair|paired|apply|cleans?|cleaning|dissolves?|dissolving)\b',first[:match.start()],re.I):result=label;break
 if not result and re.match(r'(?i)^(?:an?\s+)?earrings?\b',body):result='Earrings'
 if not result and re.match(r'(?i)^(?:an?\s+)?necklace\b',body):result='Necklaces'
 if not result and re.match(r'(?i)^(?:an?\s+)?rings?\b',body) and not re.search(r'\bearrings\b',body[:150],re.I):result='Rings'
 if not result and re.search(r'\bgift set\b',title,re.I):
  if re.search(r'\bnotebook\b',body,re.I) and re.search(r'\b(?:gel pen|sticky note)\b',body,re.I):result='Stationery Gift Sets'
  elif re.search(r'\b(?:crafts?|paints?)\b',title,re.I) and re.search(r'\bpaint brush\b',body,re.I) and re.search(r'\b(?:coloring card|pigment|paint)\b',body,re.I):result='Painting & Craft Sets'
 if not result and re.match(r'(?i)^pair this .{0,35}\btrouser\b',plain(description)) and re.search(r'\bfabric\b',plain(description),re.I):result='Trousers'
 if result:return result,'corroborated_primary_sold_object','Explicit original product identity and matching source details; collection/type cannot override sold object.'
 return None
