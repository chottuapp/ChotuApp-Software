"""Reviewed, source-bound purpose and prose repairs for the twelve held workbooks."""
import re,json,unicodedata
from pathlib import Path
from functools import lru_cache
from datetime import datetime,timezone
from urllib.parse import urlsplit
STORES={'Cool and Cool','Rivaj UK','Computer Zone','Saeed Ghani','Elite Cosmetics','Hemani Herbals','Bonanza Satrangi','Rawayat','Junaid Jamshed','Outfitters','Zellbury','Stylo'}
# Explicit object names. Compatibility targets, ingredients and care text are not classifiers.
NAMED=[
 ('Sunscreens',r'\b(?:sunscreen|sunblock|sun\s+protect)\b'),
 ('Hair Brushes & Combs',r'\b(?:hair|blower?|blore)\s+brush(?:es)?\b'),
 ('Hair Brushes & Combs','\\b(?:hair\\s+brush|blore\\s+brush|blower?\\s+brush)\\b'),
 ('Lip Balms','\\blip\\s+(?:balm|butter)\\b'),
 ('Foot Lotions','\\bfoot\\s+lotion\\b'),
 ('Foot Creams','\\b(?:foot|heel)\\s+(?:care\\s+)?cream\\b'),
 ('Hand Creams','\\bhand\\s+cream\\b'),
 ('Hand Gels','\\bhand\\s+gel\\b'),
 ('Body Lotions','\\bbody\\s+(?:milk|lotion)\\b'),
 ('Breast Firming Creams','\\bbreast\\b.{0,40}\\bcream\\b'),
 ('Foundation Sticks','\\b(?:foundation\\s+stick|professional\\s+paint\\s+stick)\\b'),
 ('Hair Bleaching Powders','\\b(?:hair|keratin)\\s+bleaching\\s+powder\\b'),
 ('Air Fresheners','\\b(?:automatic\\s+)?air\\s+freshener\\b'),
 ('Room Fragrances','\\b(?:room|home)\\s+(?:fragrance|spray|freshener)\\b'),
 ('Henna Cones','\\bcone\\s+(?:mehndi|henna)\\b'),
 ('Orange Peel Powders','\\borange\\s+peel\\s+powder\\b'),
 ('Cardholders','\\bcard\\s+holder\\b'),
 ('Pyjamas','\\bp[ay]jama\\b'),
 ('Face Polishes','\\bface\\s+polish\\b'),
 ('Peel-Off Masks','\\bpeel[ -]?off\\s+mask\\b'),
 ('Hair Clips & Pins','\\bhair\\s+pins?\\b'),
 ('Bangles & Karas','\\b(?:bangles?|karas?|karay|kada)\\b'),
 ('Nose Jewellery','\\b(?:nath|nose\\s+pin|nose\\s+ring)\\b'),
 ('Anklets','\\banklets?\\b'),
 ('Rings','\\brings?\\b'),
 ('Brooches','\\bbrooch(?:es)?\\b'),
 ('Stud Earrings','\\bear\\s*studs?\\b'),
 ('Jhumka Earrings','\\bjhumk[ai]\\b'),
 ('Pendants & Lockets','\\b(?:pendant|pendent|locket)s?\\b'),
 ('Headbands','\\b(?:head[ -]?band|hairband)s?\\b'),
 ('Hair Claws','\\bhair\\s+claw\\b'),
 ('Hair Combs','\\b(?:hair\\s+)?trimming\\s+comb\\b'),
 ('CPU Contact Frames',r'\b(?:cpu\s+)?contact\s+frame\b'),
 ('CPU Coolers',r'\bcpu\b.{0,30}\b(?:water\s+)?cooler\b'),
 ('Cooling Fans',r'\b(?:cpu|case|argb)\s+fan\b|\buni\s+fan\b'),
 ('Fan & Lighting Controllers',r'\b(?:argb\s+and\s+fan\s+hub|fan\s+(?:hub|controller)|argb\s+controller)\b'),
 ('Internal USB Hubs',r'\binternal\s+usb\b.{0,20}\bhub\b'),
 ('Computer Status Displays',r'\btrofeo\s+vision\b.*\b(?:lcd|screen|display)\b'),
 ('Racing Wheels',r'\b(?:racing|steering)\s+(?:steering\s+)?wheel\b'),
 ('Smart Glasses',r'\bsmart\s+glasses\b'),('Fitness Bands',r'\bsmart\s+band\b'),
 ('Tablet Stylus Pens',r'\bapple\s+pencil\b|\btablet\s+stylus\b'),
 ('MicroSD Memory Cards',r'\bmicro\s*sd(?:xc)?\b.{0,10}\bcard\b'),
 ('Network Switches',r'\b(?:gigabit|ethernet|network)\b.{0,65}\bswitch\b'),
 ('Monitors',r'\b(?:gaming|computer|lcd|ips)\s+monitor\b'),
 ('Laptops',r'\b(?:ideapad|macbook|chromebook)\b'),
 ('Keyboards',r'\b(?:gaming|mechanical|wireless)\s+keyboard\b'),
 ('Selfie Sticks & Tripods',r'\bselfie\s+stick\b'),
 ('Phone Holders & Mounts',r'\b(?:phone\s+(?:stand|holder)|car\s+mount)\b'),
 ('Khussa Shoes',r'\bkhus[as]+\b'),('Chappals',r'\bchappals?\b'),('Slippers',r'\bslippers?\b'),
 ('Clogs',r'\b(?:clogs?|crocs)\b'),('Baby Booties',r'\bbooties\b'),
 ('Mary Jane Shoes',r'\bmary\s+janes?\b'),('Derby Shoes',r'\bderby\s+shoes?\b'),
 ('Formal Shoes',r'\bformal\s+shoes?\b'),('Slingback Shoes',r'\bsling[ -]?backs?\b'),
 ('Loafers',r'\bloafers?\b'),('Ballet Flats',r'\bballet\s+flats?\b'),
 ('Bras',r'\bbras?\b'),('Camisoles',r'\bcamisoles?\b'),('Panties',r'\bpant(?:y|ies)\b'),
 ('Vests & Gilets',r'\b(?:vest|gilet|sando)s?\b'),('Thermal Underwear',r'\bthermal\s+(?:wear|underwear|inner)\b'),
 ('Mufflers',r'\bmufflers?\b'),('Watches',r'\bwatch(?:es)?\b'),
 ('Pouches',r'\bpouches?\b'),('Bowling Bags',r'\bbowling\s+bag\b'),
 ('Backpacks',r'\bback[ -]?packs?\b'),('Pencil Cases',r'\bpencil\s+case\b'),
 ('Hair Clips & Pins',r'\b(?:claw|bow|heart|hair)\s+clips?\b|\bbobby\s+pins?\b'),
 ('Hair Ties & Scrunchies',r'\bscrunch(?:ie|ies|y)\b|\bhair\s+ties?\b'),
 ('Lip Oils',r'\blip\s+(?:glow\s+)?oil\b'),('Lip Plumpers',r'\b(?:volumizing\s+)?lip\s+booster\b'),
 ('Makeup Removers',r'\b(?:two\s+phase\s+)?makeup\s+cleanser\b'),
 ('Makeup Primers',r'\b(?:prime\s+base|primer\s+makeup\s+base)\b'),
 ('Sunscreens',r'\bsun\s+protect\b.*\bspf\b'),
 ('Eyeliners',r'\b(?:smokey\s+eyes?\s+pencil|eye\s+pencil)\b'),
 ('Makeup Powders',r'\b(?:wet\s*(?:&|and)\s*dry|terracotta)\s+powder\b'),
 ('Multipurpose Complexion Makeup',r'\b3\s+in\s+1\b.*\bconcealer\b.*\bcontour\b.*\bfoundation\b'),
 ('Makeup Sponges',r'\b(?:sponge\s+puff|foundation\s+sponge)\b'),
 ('Tweezers',r'\btweezers?\b'),('Blackhead Removal Tools',r'\bblack\s*head\s+pin\b'),
 ('Pedicure Sets',r'\bpedicure\s+kit\b'),('Eyelash Curlers',r'\blash\s+turner\b'),
 ('Skin Scrubs & Exfoliators',r'\bskin\s+polisher\b'),
 ('Facial Bleach Creams',r'\bbleach\s+cream\b'),
 ('Bleach Applicator Brushes',r'\bbleach\s+brush\b'),
 ('False Eyelashes',r'\b(?:angel\s+)?eyelashes\b'),
]
@lru_cache(maxsize=1)
def public_index():
 path=Path(__file__).with_name('audit804-reviewed-source.json')
 return {(f['store'],str(f['product_id']),f['source_url']):f for f in json.loads(path.read_text()).get('products',[])} if path.exists() else {}
def public_facts(row,store):
 fact=public_index().get((store,str(row.get('product_id')),row.get('source_url')))
 if fact:
  norm=lambda text:re.sub(r'[^a-z0-9]+','',unicodedata.normalize('NFKC',str(text)).casefold())
  if norm(fact['public_title'])==norm(row.get('name')):return fact
 return None

def category(row,store):
 if store not in STORES:return None
 name=str(row.get('name') or '');body=str(row.get('description') or '')
 source=public_facts(row,store)
 if source:
  types={'earring':'Earrings','earrings':'Earrings','earstuds':'Stud Earrings','jhumka':'Jhumka Earrings','karay':'Bangles & Karas','bangles':'Bangles & Karas','necklace':'Necklaces','necklaces':'Necklaces','bracelets':'Bracelets','anklet':'Anklets','anklets':'Anklets','ring':'Rings','pendent':'Pendants & Lockets','pendent/chain':'Pendant Necklaces','pendent/necklace':'Pendant Necklaces','nath':'Nose Jewellery','bindiya kanta':'Forehead Jewellery','choker set':'Jewellery Sets','mala set':'Jewellery Sets','locket set':'Jewellery Sets','bridal set':'Jewellery Sets','jeans':'Jeans'}
  label=types.get(str(source.get('product_type') or '').strip().casefold())
  if label:return label,'reviewed_public_product_type','Public product_type: '+source['product_type']+'; evidence run '+source['evidence_run']+'; '+source['source_url']

 for label,pattern in NAMED:
  if label=='Cooling Fans' and re.search(r'(?i)\b(?:hub|controller|cable|adapter)\b',name.split(',')[0]):continue
  if label=='Rings' and store=='Computer Zone':continue
  if label=='Rings' and re.search(r'(?i)\b(?:key|curtain|napkin|phone|holder|case|light|binder)\b',name):continue
  if label=='False Eyelashes' and re.search(r'(?i)\b(?:serum|growth|glue|adhesive|mascara|oil)\b',name):continue
  if re.search(pattern,name,re.I):return label,'reviewed_product_name','Explicit sold-object wording: '+name
 if re.search(r'(?i)\b(?:bowling|crossbody|cross[ -]body|shoulder|tote|hand)\s*bag\b',name):return None
 if re.search(r'(?i)\bbag\b',name):return 'Bags','reviewed_product_name','Product explicitly named a bag: '+name
 if re.search(r'(?i)\b(?:palette)\b',name) and re.search(r'(?i)\b(?:eyes?|eyeshadow|eye\s*makeup)\b',body):return 'Eyeshadow Palettes','reviewed_source_description','Source identifies eye makeup palette: '+name+'; '+body[:500]
 if re.search(r'(?i)\b(?:skin|face)\s+polish',name):return 'Skin Polishes','reviewed_product_name','Explicit skin polish: '+name
 if re.search(r'(?i)\bface\b',str(row.get('website_category_path') or '')) and re.search(r'(?i)\btoner\b',str(row.get('website_category_path') or '')) and re.search(r'(?i)\bmist\b',name):return 'Face Mists & Toners','verified_navigation_membership',str(row['website_category_path'])+'; '+name
 if re.search(r'(?i)\bscrub\b',name) and (re.search(r'(?i)\b(?:facial|face)\b',str(row.get('website_category_path') or '')) or re.search(r'(?i)\b(?:face|facial)\b',body)):return 'Face Scrubs & Exfoliators','reviewed_source_description','Facial scrub source context: '+name+'; '+str(row.get('website_category_path'))
 if re.search(r'(?i)\b(?:black|charcoal)\s+(?:peel.off\s+)?mask\b',name) and re.search(r'(?i)\bskin\b',body):return 'Skin Masks','reviewed_source_description','Skin mask source: '+name+'; '+body[:500]
 if re.search(r'(?i)\blotion\b',name) and re.search(r'(?i)\bbody\s+lotion\b',body):return 'Body Lotions','reviewed_source_description','Explicit source body lotion: '+name+'; '+body[:300]
 if re.search(r'(?i)\blotion\b',name) and not re.search(r'(?i)\b(?:hair|baby|lip|foot|hand)\b',name):return 'Skin Lotions','reviewed_product_name','Named skin lotion: '+name
 if re.search(r'(?i)\b(?:moisturizing|moisturising)\s+(?:water\s+)?gel\b',name) and re.search(r'(?i)\bskin\b',body):return 'Skin Moisturising Gels','reviewed_source_description','Named moisturising gel with skin context: '+name+'; '+body[:500]
 if re.search(r'(?i)\boil\b',name) and re.search(r'(?i)\bbaby\b',name):return 'Baby Oils','reviewed_product_name','Explicit baby oil: '+name
 if re.search(r'(?i)\bhand\s+elixir\b',name) and re.search(r'(?i)\bhydrat|moisturi',body):return 'Hand Moisturisers','reviewed_source_description','Source hand hydration purpose: '+name+'; '+body[:400]
 if re.search(r'(?i)\boil\b',name) and not re.search(r'(?i)\b(?:perfume|attar|ittar|fragrance)\b',name):
  hair=bool(re.search(r'(?i)\bhair\b',body));skin=bool(re.search(r'(?i)\bskin\b',body))
  if hair and skin:return 'Hair & Skin Oils','reviewed_source_description','Source lists both hair and skin uses: '+name+'; '+body[:600]
  if hair:return 'Hair Oils','reviewed_source_description','Source hair application: '+name+'; '+body[:600]
  if skin:return 'Skin Oils','reviewed_source_description','Source skin application: '+name+'; '+body[:600]
 if re.search(r'(?i)\b(?:bundle|trio|basket|gift\s*box|self.care\s+set)\b',name):
  if re.search(r'(?i)\b(?:skincare|skin|face\s+wash|cream|lotion)\b',body):
   label='Personal Care Bundles' if re.search(r'(?i)\b(?:haircare|fragrance|beard)\b',body) else 'Skin Care Bundles'
   return label,'reviewed_source_description','Source gift/bundle purpose and contents: '+name+'; '+body[:800]
 if re.search(r'(?i)\bbb\s+skin\s+editor\b',name) and re.search(r'(?i)\b(?:spf|matte|skin)\b',body):return 'BB Face Makeup','reviewed_source_description','Named BB makeup with supplied skin finish and SPF facts: '+name+'; '+body[:350]
 if re.search(r'(?i)\b(?:fancy|short|bridal|choker|necklace|traditional|pendent|pendant)\b.*\bset\b',name) and re.search(r'(?i)jewell?ery\s+care|gold\s+plat',body):return 'Jewellery Sets','reviewed_source_description','Named jewellery set and source jewellery-care context: '+name+'; '+body[:200]
 return None

def description(row,store):
 original=str(row.get('description') or '');name=str(row.get('name') or '');body=original.strip()
 if store not in STORES:return original,None
 if (str(row.get('website_category_status') or '') in ('verified_navigation_membership','verified_product_breadcrumb')
     and str(row.get('website_category_path') or '').split(' > ')[0].casefold()=='fragrances'
     and row.get('website_category_source_url') and row.get('website_category_checked_at')
     and (urlsplit(str(row['website_category_source_url'])).hostname or '').removeprefix('www.')==(urlsplit(str(row.get('source_url') or '')).hostname or '').removeprefix('www.')
     and not re.search(r'(?i)\b(?:body\s+(?:lotion|wash)|shampoo|cream|soap|hand\s+wash)\b',name)):
  path=str(row['website_category_path']);leaf=path.split(' > ')[-1]
  lead=name+' is a fragrance'+(' in the '+leaf+' range.' if leaf.casefold()!='fragrances' else '.')
  if not body.startswith(lead):return lead+('\n\n'+original if body and body!=name else ''),'Added the verified source fragrance family/range; all supplied product details retained, no notes or benefits invented.'
 source=public_facts(row,store)
 if source and body==name and source.get('description') and source['description'].strip()!=name:
  return name+'.\n\n'+source['description'],'Restored exact matching primary public product description; listing identity retained.'
 if source and str(source.get('product_type')).casefold()=='jeans' and body.startswith(name):
  return name+' is a denim jeans style.'+original[len(name):],'Added the public product_type Jeans; every saved option retained.'
 promo=re.fullmatch(r'(?is)Buy\s+(.+?)\s*(?:&|and)\s*Get\s+(.+?)\s+Free',name)
 if promo and body==name:
  return promo[1].strip()+'. Includes '+promo[2].strip()+' as a complimentary item.','Rewrote the explicitly named paid product and complimentary gift; all names and quantities retained.'
 # Product names can themselves supply the complete known pack/reference/colour facts.
 if body==name and store=='Rawayat':
  pack=re.fullmatch(r'(?is)(.+?)[-_](\d+)\s*\(Pack of (\d+)\)',name)
  if pack and re.search(r'(?i)\bhair\s+ties\b',pack[1]):
   return 'A pack of '+pack[3]+' '+pack[1].strip().lower()+'. Listing reference: '+pack[2]+'.','Rewrote source-listed pack quantity, product type and listing reference; no material or stock claims added.'
  colour=re.fullmatch(r'(?is)(Fancy Earring)[- ]+(\d+)\s*\(([^)]+)\)',name)
  if colour:return 'A '+colour[3].strip().lower()+' fancy earring design. Listing reference: '+colour[2]+'.','Rewrote explicit earring colour and listing reference; no composition invented.'
 if body==name:
  from subcategory_inference_support import infer
  result=category(row,store) or infer(name,'')
  phrases={'Hair Brushes & Combs':'a hair-styling brush','Lip Balms':'a lip balm','Earrings':'an earring design','Stud Earrings':'a stud-earring design','Jhumka Earrings':'a jhumka-earring design','Rings':'a ring design','Bracelets':'a bracelet design','Necklaces':'a necklace design','Anklets':'an anklet design','Pendants & Lockets':'a locket design' if 'locket' in name.casefold() else 'a pendant design','Hair Clips & Pins':'a hair pin design' if 'pin' in name.casefold() else 'a hair clip design','Headbands':'a headband','Jewellery Sets':'a jewellery set','Hair Ties & Scrunchies':'a hair-tie design','Bangles & Karas':'a bangle or kara design','Brooches':'a brooch design'}
  if result and result[0] in phrases:return name+' is '+phrases[result[0]]+'.','Rewrote the supplied listing name as a factual product-specific overview; no missing material, quantity, benefit or stock invented.'
 return original,None
