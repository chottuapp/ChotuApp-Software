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
 if re.search(r'\b(?:cream|lotion|scrub|mask|brush|polish|cleaner|charm|insoles?|laces?|shoe care|rack|organizer|holder)\b',title,re.I):return None
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
