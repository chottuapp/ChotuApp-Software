"""Independent footwear/category boundary checks; no classifier-output approval."""
import re

def review(row,source=None):
 from hold804_repairs import public_facts
 fact=public_facts(source or row,'Blackbeiger') if 'blackbeiger.com/' in str((source or row).get('source_url') or '') else None
 cat=str(row.get('Category') or '').casefold()
 title=str(row.get('name') or '');body=str(row.get('description') or '')
 primary=re.split(r'(?im)(?:^|\n)\s*(?:delivery|refund policy|return.{0,10}exchange|how to style|styling tips)\b',body)[0]
 primary=re.sub(r'(?i)\b(?:can be worn|wear (?:yours|it|them)|pair(?:ed|s)?(?: (?:it|them|yours|these))?|style(?:d)?(?: (?:it|them|yours|these))?)\s+with\b[^.!?\n]*','',primary)
 excluded=bool(re.search(r'\b(?:cream|lotion|scrub|mask|brush|polish|cleaner|charm|rack|organizer|holder|insoles?|laces?)\b',title,re.I))
 kinds={'khussas':r'\bkhuss(?:a|as|ay|ey)\b','chappals':r'\b(?:chappals?|chapals?|peshawari)\b','sandals & slides':r'\b(?:sandals?|slides?|flip[ -]flops?)\b','heels & pumps':r'\b(?:heels?|pumps?|court shoes?)\b','flats':r'\b(?:flats?|ballet shoes?)\b','loafers':r'\bloafers?\b','sneakers & trainers':r'\b(?:sneakers?|trainers?)\b','boots':r'\bboots?\b','mules':r'\bmules?\b','slippers':r'\bslippers?\b'}
 source_kind=str(row.get('source_product_type') or '').casefold()
 context=title+' '+primary[:1000]+' '+source_kind
 strong=not excluded and (re.search(r'\b(?:khussas?|sandals?|slippers?|footbed|inner sole|ankle strap|court shoes|ballet shoes)\b',context,re.I) or fact and fact.get('source_category_label'))
 if strong and re.search(r'trouser|pants|jacket|coat|dress|maxi|foundation|jewellery|necklace',cat,re.I):return ['Primary footwear incorrectly assigned apparel/cosmetic/jewellery Category; styling words are not the sold object']
 if fact and fact.get('source_category_label'):
  expected=fact['source_category_label']
  # Verify evidence is an actual collection on this exact merchant domain.
  from urllib.parse import urlsplit
  url=urlsplit(str(fact.get('source_category_url') or ''))
  if url.hostname=='blackbeiger.com' and url.path.startswith('/collections/') and fact.get('source_category_title'):
   if row.get('Category')!=expected:return ['Category differs from identity-matched source collection evidence']
   return []
 if not excluded and cat in kinds and re.search(kinds[cat],context,re.I):return []
 return None

def category_boundary_issues(row,source=None):
 """Non-waivable source audience and cross-family checks for every seller."""
 from urllib.parse import urlsplit
 original=source or row;category=str(row.get('Category') or '')
 fields=[str(original.get('name') or ''),str(original.get('source_product_type') or '')]
 path=str(original.get('website_category_path') or '')
 if original.get('website_category_status') in {'verified_navigation_membership','verified_product_breadcrumb'} and original.get('website_category_checked_at') and urlsplit(str(original.get('source_url') or '')).hostname and (urlsplit(str(original.get('website_category_source_url') or '')).hostname or '').removeprefix('www.')==(urlsplit(str(original.get('source_url') or '')).hostname or '').removeprefix('www.'):
  fields.extend(path.split(' > '))
 context=' '.join(fields)
 audience=[]
 for label,pattern in [('men',r"\b(?:men(?:['’]?s)?|gents|male)\b"),('women',r"\b(?:women(?:['’]?s)?|ladies|female)\b")]:
  if re.search(pattern,context,re.I):audience.append(label)
 category_audience='women' if re.match(r"(?i)^(?:women(?:['’]?s)?|ladies|female)\b",category) else 'men' if re.match(r"(?i)^(?:men(?:['’]?s)?|gents|male)\b",category) else None
 issues=[]
 if category_audience and audience!=[category_audience]:issues.append('Category audience is unsupported or conflicts with original product evidence')
 # Exact product-type fields, never ingredient/styling/care text, establish family.
 kind=str(original.get('source_product_type') or '').strip().casefold()
 families={'apparel':r'^(?:shirt|shirts|trousers|jeans|kurta|shalwar|clothing sets)$',
  'footwear':r'^(?:flats|sandals|slippers|sneakers|heels|boots|loafers)$',
  'beauty':r'^(?:shampoo|face wash|face serum|foundation|lipstick|mascara)$',
  'stationery':r'^(?:notebook|notebooks|pencil|pencils)$'}
 incompatible={'apparel':r'\b(?:shampoos?|serums?|foundations?|lipsticks?|sandals|slippers|notebooks)\b',
  'footwear':r'\b(?:shirts|trousers|jeans|dresses|shampoos?|serums?|foundation)\b',
  'beauty':r'\b(?:shirts|trousers|jeans|dresses|sandals|slippers|notebooks)\b',
  'stationery':r'\b(?:shirts|trousers|jeans|dresses|shampoos?|serums?|foundations?|sandals)\b'}
 for family,pattern in families.items():
  if re.fullmatch(pattern,kind) and re.search(incompatible[family],category,re.I):issues.append('Category family conflicts with original exact merchant product type')
 return issues
