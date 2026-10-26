"""Owner store-specific selection rules, keyed by canonical source host."""
import re
from urllib.parse import urlsplit
ASTORE_HOST='astorebags.pk'
# Exact four optional gift-box products linked by the reviewed China Palm page.
MAALI_GIFTBOX_HANDLES={'ralli-patchwork','desi-pop','colour-playground','clay-sage'}

def allowed_product(base,product):
 host=(urlsplit(base).hostname or '').lower().removeprefix('www.')
 if host=='hellomaali.com':return product.get('handle') not in MAALI_GIFTBOX_HANDLES
 if host!=ASTORE_HOST:return True
 title=str(product.get('title') or '')
 kind=str(product.get('product_type') or '')
 # Evaluate sold objects, not cross-selling/care prose or unrelated collection tags.
 if re.search(r'\b(?:bag\s+(?:charms?|straps?|covers?|organizers?)|sleeves?|straps?|watches|watch|shoes?|perfumes?|jewellery|jewelry|clothes?|sunglasses|belts?)\b',title,re.I):return False
 return bool(re.search(r'\b(?:bags?|wallets?|handbags?|backpacks?|rucksacks?|totes?|clutches|clutch|purses?|satchels?|briefcases?|duffels?|crossbody|mini\s+pouches|mini\s+pouch)\b',title+' '+kind,re.I))
