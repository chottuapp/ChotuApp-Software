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
 if host=='thepaperworm.com':return paperworm_school_supply(product)
 if host=='hellomaali.com':return product.get('handle') not in MAALI_GIFTBOX_HANDLES
 if host!=ASTORE_HOST:return True
 title=str(product.get('title') or '')
 kind=str(product.get('product_type') or '')
 # Evaluate sold objects, not cross-selling/care prose or unrelated collection tags.
 if re.search(r'\b(?:bag\s+(?:charms?|straps?|covers?|organizers?)|sleeves?|straps?|watches|watch|shoes?|perfumes?|jewellery|jewelry|clothes?|sunglasses|belts?)\b',title,re.I):return False
 return bool(re.search(r'\b(?:bags?|wallets?|handbags?|backpacks?|rucksacks?|totes?|clutches|clutch|purses?|satchels?|briefcases?|duffels?|crossbody|mini\s+pouches|mini\s+pouch)\b',title+' '+kind,re.I))


def paperworm_school_supply(product):
 """Owner lock: school supplies only; uncertain/general gifts stay excluded.

 Use the sold-object title and explicit taxonomy, never marketing descriptions,
 SEO tags or a recommendation mentioning school next to an unrelated product.
 """
 title=str(product.get('title') or product.get('name') or '')
 if re.search(r'\b(?:gift\s+bags?|party|balloons?|bunting|confetti|cake\s+toppers?|home\s+decor|candles?|cushions?|plush|dolls?|action\s+figures?|remote\s+control|board\s+games?|travel\s+bags?|luggage|laptop\s+bags?|baby\s+(?:bottles?|feeding)|printers?|toner|ink\s+cartridges?)\b',title,re.I):return False
 labels=[str(product.get(k) or '') for k in ('product_type','Category','category','source_category','source_product_type')]
 for value in product.get('categories',[]) or []:
  labels.append(str(value.get('name','') if isinstance(value,dict) else value))
 kinds=r'school\s*bags?|backpacks?|rucksacks?|lunch\s*(?:boxes|box|bags?)|bento\s*(?:boxes|box)|water\s*bottles?|pencil\s*(?:cases?|boxes|box|pouches?)|stationery\s*(?:sets?|kits?)|notebooks?|exercise\s*books?|copy\s*books?|drawing\s*books?|sketch\s*(?:books?|pads?)|drawing\s*pads?|pens?|pencils?|erasers?|rubbers?|sharpeners?|rulers?|geometry\s*(?:sets?|boxes|box)|compass(?:es)?|protractors?|crayons?|colou?r\s*pencils?|felt\s*(?:tip\s*)?pens?|markers?|highlighters?|glue\s*sticks?|school\s*glue|scissors|paint\s*brush(?:es)?|water\s*colou?rs?|poster\s*colou?rs?|calculators?'
 return bool(re.search(r'\b(?:'+kinds+r')\b',title,re.I) or any(re.fullmatch(r'\s*(?:school\s*(?:supplies|stationery|bags)|stationery|art\s*(?:and|&)\s*craft\s*supplies)\s*',v,re.I) for v in labels) or any(re.search(r'\b(?:'+kinds+r')\b',v,re.I) for v in labels))


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
OWNER_PAUSED_STORES={'Khaadi','Bachaa Party','Axis PK','Gift4U','Liberty Books'}
OWNER_PAUSED_HOSTS={'khaadi.com','pk.khaadi.com','bachaaparty.com','axispk.shop','gift4u.pk','libertybooks.com'}

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
 def incompatible(value):
  if isinstance(value,str):return bool(re.search(r'[\x00-\x08\x0b\x0c\x0e-\x1f]',value))
  if isinstance(value,dict):return any(incompatible(v) for v in value.values())
  if isinstance(value,list):return any(incompatible(v) for v in value)
  return False
 if incompatible(product):reasons.append('Source text contains Excel-incompatible control characters; original source retained without altering SKU or variant facts')
 if not title:reasons.append('Missing product name')
 from product_description_support import completeness_issues
 if completeness_issues(body,title):reasons.append('Description lacks enough product-specific content for review')
 if re.search(r'(?i)\b(?:lorem ipsum|description coming soon|no description available)\b',body):reasons.append('Placeholder description')
 return reasons


def record_incomplete_product(product,base,name,engine_file,reasons):
 """Keep the public source receipt outside disposable export staging."""
 import csv,json
 from pathlib import Path
 safe=re.sub(r'[^\w .-]','',name).strip() or 'Shopify'
 folder=Path(engine_file).resolve().parent/'audit_reports'/safe
 folder.mkdir(parents=True,exist_ok=True);target=folder/(safe+' - INCOMPLETE PRODUCTS.csv')
 first=not target.exists()
 with target.open('a',encoding='utf-8-sig',newline='') as stream:
  writer=csv.writer(stream)
  if first:writer.writerow(['product_id','name','source_url','skip_reasons','original_source_product_json'])
  writer.writerow([product.get('id'),product.get('title') or product.get('name'),product.get('_source_url') or base+'/products/'+str(product.get('handle') or ''),'; '.join(reasons),json.dumps(product,ensure_ascii=False,default=str)])
 return target
