"""Owner store-specific selection rules, keyed by canonical source host."""
import re
from urllib.parse import urlsplit
ASTORE_HOST='astorebags.pk'
# Exact four optional gift-box products linked by the reviewed China Palm page.
MAALI_GIFTBOX_HANDLES={'ralli-patchwork','desi-pop','colour-playground','clay-sage'}

def allowed_product(base,product):
 host=(urlsplit(base).hostname or '').lower().removeprefix('www.')
 if host=='chenone.com':return not chenone_furniture(product)
 if host=='hellomaali.com':return product.get('handle') not in MAALI_GIFTBOX_HANDLES
 if host!=ASTORE_HOST:return True
 title=str(product.get('title') or '')
 kind=str(product.get('product_type') or '')
 # Evaluate sold objects, not cross-selling/care prose or unrelated collection tags.
 if re.search(r'\b(?:bag\s+(?:charms?|straps?|covers?|organizers?)|sleeves?|straps?|watches|watch|shoes?|perfumes?|jewellery|jewelry|clothes?|sunglasses|belts?)\b',title,re.I):return False
 return bool(re.search(r'\b(?:bags?|wallets?|handbags?|backpacks?|rucksacks?|totes?|clutches|clutch|purses?|satchels?|briefcases?|duffels?|crossbody|mini\s+pouches|mini\s+pouch)\b',title+' '+kind,re.I))


def chenone_furniture(product):
 """Owner lock: exclude furniture, keep bedding, textiles and other goods."""
 title=str(product.get('title') or product.get('name') or '')
 kind=str(product.get('product_type') or product.get('Category') or '').strip()
 if re.search(r'\b(?:furniture|beds?|chairs?|sofas?|tables?|dressers?|wardrobes?|ottomans?|bookcases?|sideboards?|nightstands?|cabinets?|stools?|benches|recliners?)\b',kind,re.I) and not re.search(r'\b(?:spreads?|sheets?|covers?|linen|runners?|mats?|cloths?|lamps?|protectors?|skirts?)\b',kind,re.I):return True
 if re.search(r'\b(?:bed\s*(?:spreads?|sheets?|covers?|linen|skirts?)|table\s*(?:cloths?|runners?|mats?|linen|lamps?)|(?:cushion|pillow|sofa|chair|duvet|quilt|mattress)\s*(?:covers?|protectors?)|filled\s+cushions?)\b',title,re.I):return False
 return bool(re.search(r'\b(?:furniture|chairs?|sofas?|dressers?|wardrobes?|ottomans?|bookcases?|sideboards?|nightstands?|cabinets?|stools?|benches|recliners?|(?:coffee|dining|breakfast|side|bedside|console|end)\s+tables?)\b',title,re.I) or re.search(r'\bbed$',title,re.I))
