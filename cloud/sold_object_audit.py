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
