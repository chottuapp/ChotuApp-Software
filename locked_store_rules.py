"""Owner store-specific selection rules, keyed by canonical source host."""
import re
from urllib.parse import urlsplit
ASTORE_HOST='astorebags.pk'
# Exact four optional gift-box products linked by the reviewed China Palm page.
MAALI_GIFTBOX_HANDLES={'ralli-patchwork','desi-pop','colour-playground','clay-sage'}

def allowed_product(base,product):
 host=(urlsplit(base).hostname or '').lower().removeprefix('www.')
 if host=='freshbasket.com.pk':return not freshbasket_produce(product)
 if host=='chenone.com':return not chenone_furniture(product)
 if host=='hellomaali.com':return product.get('handle') not in MAALI_GIFTBOX_HANDLES
 if host!=ASTORE_HOST:return True
 title=str(product.get('title') or '')
 kind=str(product.get('product_type') or '')
 # Evaluate sold objects, not cross-selling/care prose or unrelated collection tags.
 if re.search(r'\b(?:bag\s+(?:charms?|straps?|covers?|organizers?)|sleeves?|straps?|watches|watch|shoes?|perfumes?|jewellery|jewelry|clothes?|sunglasses|belts?)\b',title,re.I):return False
 return bool(re.search(r'\b(?:bags?|wallets?|handbags?|backpacks?|rucksacks?|totes?|clutches|clutch|purses?|satchels?|briefcases?|duffels?|crossbody|mini\s+pouches|mini\s+pouch)\b',title+' '+kind,re.I))


def freshbasket_produce(product):
 """Owner lock: Fresh Basket fruit/vegetable goods cannot enter sale exports.

 Use sold-object names and explicit taxonomy, never ingredients/descriptions.
 Fruit-flavoured dairy, drinks, preserves and other prepared foods are retained.
 """
 title=str(product.get('title') or product.get('name') or '')
 if re.search(r'\b(?:yog[hu]rt|juice|nectar|drink|smoothie|jam|jelly|marmalade|sauce|ketchup|pickle|chutney|chips|crisps|biscuit|cookie|cake|chocolate|ice\s*cream|tea|shampoo|soap|oil|vinegar|soup|cereal)\b',title,re.I):return False
 labels=[str(product.get(k) or '') for k in ('product_type','Category','category','source_category','source_product_type')]
 for value in product.get('categories',[]) or []:
  labels.append(str(value.get('name','') if isinstance(value,dict) else value))
 if any(re.search(r'\b(?:fruits?|vegetables?|veggies|fresh produce)\b',label,re.I) for label in labels):return True
 names=r'apples?|bananas?|oranges?|mandarins?|tangerines?|mango(?:es|s)?|grapes?|guavas?|peach(?:es)?|pears?|plums?|apricots?|cherr(?:y|ies)|strawberr(?:y|ies)|blueberr(?:y|ies)|raspberr(?:y|ies)|blackberr(?:y|ies)|pomegranates?|pineapples?|watermelons?|melons?|papayas?|kiwi|avocados?|lemons?|limes?|coconuts?|dates|potato(?:es|s)?|tomato(?:es|s)?|onions?|carrots?|cucumbers?|capsicums?|bell peppers?|spinach|lettuce|cabbage|cauliflower|broccoli|okra|lady\s*fingers?|aubergines?|eggplants?|brinjals?|zucchini|courgettes?|pumpkins?|gourds?|radish(?:es)?|turnips?|beetroot|sweet\s*corn|peas|green\s*beans|mushrooms?|ginger|garlic|coriander|cilantro|mint|green\s*chill?i(?:es)?|aloo|aalu|pyaz|pyaaz|tamatar|bhindi|palak|baingan|gajar|kheera|karela|tinda|lauki|kaddu|matar|gobhi|gobi|adrak|lehsan|dhaniya|pudina'
 return bool(re.search(r'\b(?:'+names+r')\b',title,re.I))


def chenone_furniture(product):
 """Owner lock: exclude furniture, keep bedding, textiles and other goods."""
 title=str(product.get('title') or product.get('name') or '')
 kind=str(product.get('product_type') or product.get('Category') or '').strip()
 if re.search(r'\b(?:furniture|beds?|chairs?|sofas?|tables?|dressers?|wardrobes?|ottomans?|bookcases?|sideboards?|nightstands?|cabinets?|stools?|benches|recliners?)\b',kind,re.I) and not re.search(r'\b(?:spreads?|sheets?|covers?|linen|runners?|mats?|cloths?|lamps?|protectors?|skirts?)\b',kind,re.I):return True
 if re.search(r'\b(?:bed\s*(?:spreads?|sheets?|covers?|linen|skirts?)|table\s*(?:cloths?|runners?|mats?|linen|lamps?)|(?:cushion|pillow|sofa|chair|duvet|quilt|mattress)\s*(?:covers?|protectors?)|filled\s+cushions?)\b',title,re.I):return False
 return bool(re.search(r'\b(?:furniture|chairs?|sofas?|dressers?|wardrobes?|ottomans?|bookcases?|sideboards?|nightstands?|cabinets?|stools?|benches|recliners?|(?:coffee|dining|breakfast|side|bedside|console|end)\s+tables?)\b',title,re.I) or re.search(r'\bbed$',title,re.I))

# Owner re-enabled Gift4U and Xcessories Hub on 1 November 2026.
# Owner permanently disabled Axis on 5 November 2026.
# Owner disabled Gift4U again on 5 November 2026.
# Owner re-enabled LAAM on 6 November 2026, PKR 2000–7000 products only.
OWNER_PAUSED_STORES={'Khaadi','Bachaa Party','Axis PK','Gift4U'}
OWNER_PAUSED_HOSTS={'khaadi.com','pk.khaadi.com','bachaaparty.com','axispk.shop','gift4u.pk'}

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


def incomplete_product_reasons(product):
 """Cheap preflight before per-product refresh: no invented sparse prose."""
 from html import unescape
 title=str(product.get('title') or product.get('name') or '').strip()
 body=str(product.get('body_html') or product.get('description') or '')
 body=re.sub(r'<(?:script|style)\b[^>]*>.*?</(?:script|style)>',' ',body,flags=re.I|re.S)
 body=unescape(re.sub(r'<[^>]+>',' ',body));body=re.sub(r'\s+',' ',body).strip()
 reasons=[]
 if not title:reasons.append('Missing product name')
 if len(re.findall(r'\b\w+\b',body))<5 or body.rstrip('.').casefold()==title.rstrip('.').casefold():reasons.append('Description lacks enough product-specific content for review')
 if re.search(r'(?i)\b(?:lorem ipsum|description coming soon|no description available)\b',body):reasons.append('Placeholder description')
 return reasons
