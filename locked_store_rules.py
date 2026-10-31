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

# Owner lock, 31 October: explicit owner instruction is required to re-enable.
OWNER_PAUSED_STORES={'Gift4U','Xcessories Hub','LAAM','Khaadi','Bachaa Party'}
OWNER_PAUSED_HOSTS={'gift4u.pk','xcessorieshub.com','laam.com','khaadi.com','pk.khaadi.com','bachaaparty.com'}

def owner_paused(name='',url=''):
 return name in OWNER_PAUSED_STORES or (urlsplit(str(url)).hostname or '').lower().removeprefix('www.') in OWNER_PAUSED_HOSTS

def has_source_photo(product):
 """At least one real source-linked photo; placeholders are not sellable photos."""
 def valid(value):
  return isinstance(value,str) and value.startswith(('https://','http://','//')) and not re.search(r'placeholder|no[-_]image|image[-_]not[-_]available',value,re.I)
 def image(value):
  if isinstance(value,str):return valid(value)
  return isinstance(value,dict) and any(valid(value.get(k)) for k in ('src','url','original_src'))
 if image(product.get('image')) or image(product.get('featured_image')):return True
 if any(image(v) for v in product.get('images',[]) or []):return True
 if any(image(v.get('image')) or image(v.get('featured_image')) or valid(v.get('image_url')) for v in product.get('variants',[]) or []):return True
 return any(valid(v) for k,v in product.items() if str(k).startswith(('scraped_image_url','final_image_url','variant_image_url','fallback_image_url','image_url')))
