"""Owner store-specific selection rules, keyed by canonical source host."""
import re
from urllib.parse import urlsplit
ASTORE_HOST='astorebags.pk'

def allowed_product(base,product):
 if (urlsplit(base).hostname or '').lower().removeprefix('www.')!=ASTORE_HOST:return True
 title=str(product.get('title') or '')
 kind=str(product.get('product_type') or '')
 # Evaluate sold objects, not cross-selling/care prose or unrelated collection tags.
 if re.search(r'\b(?:bag\s+(?:charms?|straps?|covers?|organizers?)|watches|watch|shoes?|perfumes?|jewellery|jewelry|clothes?|sunglasses|belts?)\b',title,re.I):return False
 return bool(re.search(r'\b(?:bags?|wallets?|handbags?|backpacks?|rucksacks?|totes?|clutches|clutch|purses?|satchels?|briefcases?|duffels?)\b',title+' '+kind,re.I))
