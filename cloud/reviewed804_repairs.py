"""Remove demonstrably copied product prose using retained source identity/specifications."""
import re
from urllib.parse import urlsplit

def numbers(value):return set(re.findall(r'\d+(?:[.,]\d+)?',str(value)))
def roots(rows):
 result=set()
 for row in rows:
  match=re.match(r'([A-Za-z][A-Za-z-]{3,})',str(row.get('name') or ''))
  if match:result.add(match.group(1).lower())
 return result

def conflicting_name(row,catalogue):
 name=str(row.get('name') or '');own=re.match(r'([A-Za-z][A-Za-z-]{3,})',name)
 if not own:return None
 for match in re.finditer(r'\b([A-Z][a-z]{3,}) is (?:a |an |the )',str(row.get('description') or '')):
  other=match.group(1)
  if other.lower()!=own.group(1).lower() and other.lower() in catalogue:return other
 return None

def product_content(row):
 raw=str(row.get('description') or '')
 host=(urlsplit(str(row.get('source_url') or '')).hostname or '').removeprefix('www.')
 if host=='shopmodest.pk':
  marker=re.search(r'(?i)Four bulk inquiry contact us at',raw)
  if marker:
   options=re.search(r'(?im)^Product Options:',raw[marker.start():])
   prefix=raw[:marker.start()].rstrip()
   if not prefix and options:prefix=str(row.get('name') or '')
   raw=prefix+('\n\n'+raw[marker.start()+options.start():] if options else '')
 return raw

def description(row,store,catalogue):
 original=str(row.get('description') or '');title=str(row.get('name') or '');reason=None;fixed=product_content(row)
 if fixed!=original:reason='Removed bulk-contact and customer-review boilerplate; all product specifications, size tables and options retained.'
 if store=='Seran' and conflicting_name(row,catalogue):
  match=re.search(r'(?is)OUTFIT DESCRIPTION\s*\n.*?\nPRODUCT DETAIL\s*\n(.*)',original)
  if match:
   candidate=title+'\nPRODUCT DETAIL\n'+match.group(1)
   if numbers(original)<=numbers(candidate):fixed=candidate;reason='Copied narrative naming a different catalog product removed; selected listing identity and complete PRODUCT DETAIL specifications retained.'
 if store=='Farda Foods' and urlsplit(str(row.get('source_url') or '')).hostname=='shop.fardafoods.com':
  copied=(re.fullmatch(r'Ginger Powder',title,re.I) and re.search(r'\bturmeric\s+powder\b',original,re.I) and not re.search(r'\bginger\b',original,re.I)) or (re.fullmatch(r'Black Pepper Whole',title,re.I) and re.search(r'\bblack pepper powder\b',original,re.I))
  weight=re.search(r'(?is)\bWeight\s*:\s*(.+)$',original)
  if copied and weight:
   candidate=title+'. Supplied weight: '+weight.group(1)
   if numbers(original)<=numbers(candidate):fixed=candidate;reason='Copied prose about a different spice/form removed; exact product name and every supplied weight/option retained.'
 return fixed,reason
