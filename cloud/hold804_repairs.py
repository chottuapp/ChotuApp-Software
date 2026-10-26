"""Reviewed, source-bound purpose and prose repairs for the twelve held workbooks."""
import re,json,unicodedata
from pathlib import Path
from functools import lru_cache
from datetime import datetime,timezone
from urllib.parse import urlsplit
SOURCE_TYPES={'SYNCC - Women Sweater':'Sweaters','Women Stitched Sari':'Sarees','Men Peshawari Chappal':'Chappals','Women Trouser':'Trousers','Women Earrings':'Earrings','Women Bracelet':'Bracelets','Women Necklace':'Necklaces','Women Ring':'Rings','Women Eyebrow Kit':'Eyebrow Kits','Infants Stitched 3 Piece':'Stitched Outfit Sets','Men Waistcoat With Kurta Trouser':'Clothing Sets'}
STORES={'Gul Ahmed','Miss Rose','Cool and Cool','Rivaj UK','Computer Zone','Saeed Ghani','Elite Cosmetics','Hemani Herbals','Bonanza Satrangi','Rawayat','Junaid Jamshed','Outfitters','Zellbury','Stylo'}
# Explicit object names. Compatibility targets, ingredients and care text are not classifiers.
NAMED=[
 ('Hand & Foot Creams','\\b(?:hand\\s*&\\s*feet|foot\\s+hand)\\b.*\\bcream\\b'),
 ('Face & Body Creams','\\bface\\s*&\\s*body\\b.*\\bcream\\b'),
 ('Face & Body Emulsions','\\bemulsion\\b.*\\bface\\s*&\\s*body\\b'),
 ('Facial Bleach Kits','\\b(?:skin\\s+bleach\\s+kit|bleach\\s+powder\\s*&\\s*activator)\\b'),
 ('Blusher Palettes','\\bblusher\\s+palette\\b'),
 ('Talcum Powders','\\b(?:talcum\\s+powder|perfumed\\s+talc)\\b'),
 ('Books','\\btasawwuf\\s+book\\b'),
 ('Herbal Oils','^roghan\\s+'),
 ('Baby Skin Jellies','\\bbaby\\s+jelly\\b'),
 ('Colognes','\\bcologne\\b'),
 ('Baby Shampoos','\\bbaby\\b.*\\bshampoo\\b'),
 ('Hair Styling Gels','\\bgel\\s+for\\s+hair\\b'),
 ('Hair Styling Waxes','\\bhair\\s+wax\\b'),
 ('Hair Growth Sprays','\\bhair\\s+growth\\s+spray\\b'),
 ('Kitchen Scales','\\bkitchen\\s+scale\\b'),
 ('Cosmetic Cream Additives','\\bcapsules\\s+for\\s+creams\\b'),
 ('Puzzle Cubes','\\b(?:magic\\s+cube\\s+puzzle|puzzle\\s+cube)\\b'),
 ('Furniture Polishes','\\bfurniture\\s+shiner\\b'),
 ('pH Test Papers','\\bph\\s+papers\\b'),
 ('Laundry Detergents','\\blaundry\\s+detergent\\b'),
 ('Dishwashing Liquids','\\bdish\\s+wash\\s*[-–]'),
 ('Limescale Removers','\\bdescalar\\b'),
 ('Floor Cleaners','\\bfloor\\s+cleaner\\b'),
 ('Waterless Car Washes','\\bcar\\s+waterless\\s+wash\\b'),
 ('Car Interior Dressings','\\bcar\\s+interior\\s+dressing\\b'),
 ('Car Cleaners','\\bcar\\s+all\\s+purpose\\s+cleaner\\b'),
 ('IPL Hair Removal Devices','\\bipl\\s+laser\\s+hair\\s+removal\\b'),
 ('Nail Photography Lamps','\\bnail\\s+photography\\s+lamp\\b'),
 ('Foot Scrubbers','\\bfoot\\s+scrubber\\b'),
 ('Pedicure Sets','\\bpedicure\\s+tool\\s+kit\\b'),
 ('Hair Building Fibres','\\bhair\\s+support\\s+fibers\\b'),
 ('Drain Cleaners','\\bdrain\\s+opener\\b'),
 ('Hair Combs','\\bmodeling\\s+comb\\b'),
 ('Antiseptic Skin Creams','\\bskin\\s+antiseptic\\s+cream\\b'),
 ('Lip & Cheek Colour','\\bliquid\\s+blush\\s*&\\s*lip\\s+tint\\b'),
 ('Facial Cleansing Powders','\\b(?:melafadin|gentle)\\s+cleansing\\s+powder\\b'),
 ('Facial Tonics','\\bmicellar\\s+skin\\s+tonic\\b'),
 ('Facial Night Treatments','\\bbrightening\\s+night\\s+care\\b'),
 ('Facial Treatment Ampoules','\\bmelafadin\\s+fluid\\b'),
 ('Hair Threading Tools','\\bsildne\\s+(?:face|hair)\\s+threading\\b'),

 ('Perfumes & Fragrances',r'^perfume\s*[-–:]'),
 ('Fragrance Gift Sets',r'\bethereal\s+desires\s+gift\s+box\b'),
 ('Sugar Substitutes',r'\bksylitol\b'),
 ('Sleep & Relaxation Sets',r'\bsleep\s+well\s+package\s+combo\b'),
 ('Wellness Supplement Sets',r'\bpure\s+bloom\b.*\boverall\s+health\s+package\b'),
 ('Instant Tea Mixes',r'\b(?:chai\s+(?:latte\s+)?|kehwa\s+)instant\s+premix\b'),
 ('Hair Conditioners',r'\b(?:yogurt|yoghurt)\b.*\bconditioner\b'),
 ('Hair Conditioning Treatments',r'\bhair\s+mayonnaise\b'),
 ('BB & CC Creams',r'\bbb\s+cream\b'),
 ('Makeup Setting Sprays',r'\b(?:makeup\s+)?fixing\s+spray\b'),
 ('Lipsticks',r'\blipstick\b'),
 ('Facial Cleansing Cloths',r'\bfacial\s+cleansing\s+(?:whitening\s+)?cloths\b'),
 ('Eyeshadow Applicators',r'\beye\s+shade\s+applicator\b'),
 ('Skin & Hair Care Sets',r'\bskin\s+and\s+hair\b.*\bset\b'),
 ('Scented Candles','\\b(?:(?:scented|aromatherapy|solid)\\s+)?candle\\b'),
 ('Herbal Capsules','\\b(?:herbalist\\b.*\\bcapsules?|herbal\\s+oil\\s+capsule)\\b'),
 ('Food Flavourings','\\bfood\\s+essence\\b'),
 ('Olive Cooking Oils','\\b(?:extra\\s+virgin|pomace)\\s+olive\\s+oil\\b'),
 ('Dental Gels','\\bdental\\s+gel\\b'),
 ('Intimate Washes','\\bintimate\\s+wash\\b'),
 ('Hand Cleansers','\\bhand\\s+cleanser\\b'),
 ('Foot Sprays','\\bfoot\\s+spray\\b'),
 ('Soap Bars','^soap\\s+with\\b'),
 ('Miswak Sticks','\\bmiswak\\b'),
 ('Herbal Nasal Drops','\\bherbal\\s+nasal\\s+drops\\b'),
 ('Herbal Nasal Oils','\\bherbal\\s+nasal\\s+oil\\b'),
 ('Herbal Relief Oils','\\b(?:herbal\\s+relief\\s+oil|sinu[ -]drain\\s+oil)\\b'),
 ('Massage Gels','\\bicy\\s+hot\\b.*\\bgel\\b'),
 ('Magnesium Sprays','\\bmagnesium\\s+spray\\b'),
 ('Massage Creams','\\b(?:massage\\s+cream|relief\\s+cream\\s*[-–]\\s*himomed)\\b'),
 ('Shilajit Supplements','\\bshilajit\\b'),
 ('Garden Cress Seeds','\\bgarden\\s+cress\\s+seeds\\b'),
 ('Psyllium Husk Supplements','\\b(?:ispaghol|psyllium\\s+husk)\\b'),
 ('Herbal Powders','\\b(?:moringa|berberine)\\s+powder\\b'),
 ('Face Mask Powders','\\bherbal\\s+beauty\\s+mask\\s+powder\\b'),
 ('Disinfectant Sprays','\\bdisinfectant\\s+spray\\b'),
 ('Sanitiser Sprays','\\bsanitizer\\s+spray\\b'),
 ('Facial Gels','\\bface\\s+gel\\b'),
 ('Hair Tonics','\\bhair\\s+tonic\\b'),

 ('Household Batteries','\\b(?:AA|AAA)\\s+size\\s+cell\\s+batteries\\b'),
 ('Eyelash Adhesives','\\beyelash\\s+glue\\b'),
 ('Insecticide Sprays','\\b(?:insecticide\\s+spray|insect\\s+killer\\s+spray)\\b'),
 ('Mosquito Coils','\\bmosquito\\s+coil\\b'),
 ('Mosquito Repellent Devices','\\bmosquito\\s+killer\\s+machine\\b'),
 ('Mouth Fresheners','\\bmouth\\s+spray\\b'),
 ('Facial Bleaches','\\b(?:creme\\s+bleach|cream\\s+bleach|bleach\\s+sachet|facial\\s+bleach)\\b'),
 ('Sanitary Pads','\\bpads\\b.{0,80}\\b(?:heavy\\s+flow|leak\\s+protection)\\b'),
 ('Facial Tissues','\\b(?:pop[ -]?up\\s+)?tissues\\b'),
 ('Packaging Stretch Wrap','\\bstretch\\s+wrap\\b.{0,40}\\bpackaging\\b'),
 ('Food Cling Film','\\bcling\\s+film\\b.{0,40}\\bfood\\b'),
 ('Baby Rash Creams','\\b(?:nappy|diaper)\\s+rash\\b'),
 ('Water Filter Cartridges','\\b(?:water\\s+carbon\\s+filter|carbon\\s+filter\\b.*\\bhousehold|micron\\s+filter|PPF\\s+5\\s+micron)\\b'),
 ('Lice Removal Combs','\\b(?:anti[ -]?lice|lice\\s+removal)\\b.*\\bcomb\\b'),
 ('Facial Steamers','\\bfacial\\s+steamer\\b'),
 ('Pest-Control Traps','\\b(?:mouse|rat)\\s+(?:trap|catching)\\b'),
 ('Hand Wash','\\bhand\\s*wash\\b'),
 ('Car Engine Degreasers','\\b(?:engine\\s+degreaser|car\\s+heavy\\s+duty\\s+degreaser)\\b'),
 ('Car Polishes','\\bcar\\s+polish\\b'),
 ('Multipurpose Household Cleaners','\\bmulti[ -]?purpose\\s+cleaner\\b'),
 ('Floor Cleaners','\\bphenyl\\b'),
 ('Dishwashing Liquids','\\b(?:liquid\\s+(?:gel\\s+)?dish\\s*wash|dishwashing\\s+liquid)\\b'),
 ('Toilet & Tile Cleaners','\\btoilet\\s+and\\s+tiles?\\s+cleaner\\b'),
 ('Glass Cleaners','\\bglass\\s+cleaner\\b'),
 ('Laundry Bleaches','\\bbleach\\s+liquid\\s+for\\s+white\\s+clothes\\b'),
 ('Adult Diapers','\\badult\\s+diaper\\b'),
 ('Baby Diapers','\\bcarebaby\\b.*\\bdiapers\\b'),
 ('Hair Removal Waxes','\\b(?:finger\\s+wax|brazilian\\s+.*wax|wax\\b.*\\bhair\\s+removal)\\b'),
 ('Hair Removal Serums','\\bstop\\s+hair\\b.*\\bserum\\b'),
 ('Hair Crimpers','\\bhair\\s+crimple\\b'),
 ('Hair Curlers','\\b(?:hair\\s+curler|curler\\s+pro\\s+soft\\s+curl)\\b'),
 ('Hair Sprays','\\bhair\\s+spray\\b'),
 ('Blackhead Removal Strips','\\bnose\\s+pore\\s+strips\\b'),
 ('Epilators & Trimmers','\\bepilator\\b'),
 ('Lip Masks','\\blip\\s+mask\\b'),
 ('Hair Protein Treatments','\\bhair\\s+protein\\b.*\\btreatment\\b'),

 ('Remote Control Cars','\\bremote\\s+control\\s+car\\b'),
 ('Remote Control Helicopters','\\bremote\\s+control\\s+helicopter\\b'),
 ('Drawing Stencils','\\bstencils?\\b'),
 ('Drawing Paper','\\bdrawing\\s+paper\\b'),
 ('Board Games','\\bboard\\s+game\\b'),
 ('Jigsaw Puzzles','\\bjigsaw\\s+puzzle\\b'),
 ('Puzzle Cubes','\\bpuzzle\\s+cube\\b'),
 ('Educational Puzzles','\\b(?:math|shape)\\b.*\\bpuzzle\\b|\\bpuzzle\\b.*\\b(?:math|shape)\\b'),
 ('Montessori Busy Boards','\\bmontessori\\s+busy\\s+board\\b'),
 ('Body Shapers','\\bbody\\s+shaper\\b'),
 ('Stockings','\\bstockings?\\b'),
 ('Bralettes','\\bbrallete\\b'),
 ('Hand Mirrors','\\bhand\\s+mirror\\b'),
 ('Makeup Puff & Clip Sets','\\bmakeup\\s+puff\\s*&\\s*clip\\s+set\\b'),

 ('Face Wash','\\b(?:face|facial)\\s+wash\\b'),
 ('Foot Scrubs',r'\bfoot\s+scrub\b'),
 ('Multipurpose Skin Creams',r'\bcream\b.*\bface\b.*\bbody\b.*\bhands?\b'),
 ('Lipstick Sets',r'\blipstick\s+bundle\b'),
 ('Face Serums',r'\b(?:face|facial)\s+serum\b'),
 ('Makeup Setting Powders',r'\b(?:illuminating|makeup|beauty)\s+baking\s+powder\b'),
 ('Instant Tea Mixes',r'\bchai\s+instant\s+premix\b'),
 ('Instant Drink Mixes',r'\blimopani\s+instant\s+premix\b'),
 ('Herbal Gummies',r'\b(?:herbalist|ashwagandha)\b.*\bgummies\b'),
 ('Pain Relief Ointments',r'\bpain\s+relief\s+massage\s+ointment\b'),
 ('Vapor Rubs',r'\bvapor\s+rub\b'),
 ('Pain Relief Sprays',r'\b(?:quick|pain)\s+relief\s+spray\b'),

 ('Diffuser Oils',r'\bdiffuser\s+oil\b'),
 ('Room Fragrances',r'\breed\s+diffuser\b'),
 ('Eyebrow Kits',r'\bbrow\s+kit\b'),
 ('Eyeliners',r'\bdipliner\b'),
 ('Face Powders',r'\bmineral\s+powder\b'),
 ('Makeup Removers',r'\bmake[ -]?up\s+remover\b'),
 ('Cardigans',r'\bcardigan\b'),
 ('Moccasins',r'\bmocass?ins?\b'),
 ('Monk Shoes',r'\bmonk\b.{0,30}\bshoes\b'),

 ('Kurta & Pyjama Sets',r'\bkurta\s+p[ay]jama\b'),
 ('Kameez Shalwar Sets',r'\bkameez\s+shalwar\b'),
 ('Sherwanis',r'\bsherwanis?\b'),
 ('Denim Shorts',r'\bjorts\b'),
 ('Bomber Jackets',r'\bbomber\b'),
 ('Flats',r'\bflats\b'),
 ('Pullovers',r'\bpull[ -]?over\b'),
 ('Tops',r'\btop\b(?!\s*(?:note|coat|load|4|four|10))'),

 ('Bed Sheets',r'\bbed\s+sheet\b'),
 ('School Shoes',r'\bschool\s+shoes?\b'),
 ('Stoles',r'\bstoles?\b'),
 ('Bralettes',r'\bbralettes?\b'),
 ('Loungewear Sets',r'\blounge\s*wear\s+set\b'),
 ('Nail Care Kits',r'\bnail\s+care\s+kit\b'),
 ('Stationery Sets',r'\bstationery\s+set\b'),
 ('Boots',r'\bboots?\b'),
 ('Belts',r'\bbelts?\b'),
 ('Hair Crowns & Tiaras',r'\b(?:crown|tiara)\b'),

 ('Compressed Towels',r'\bcompressed\s+towels?\b'),
 ('Massage Devices',r'\b(?:massager|massage\s+gun|fascia\s+gun)\b'),
 ('Skin Toning Solutions',r'\btoning\s+solution\b'),
 ('Body Scrubs',r'\b(?:body|shower)\s+scrub\b'),
 ('Hair Colour Developers',r'\bdeveloper\b.{0,15}\b(?:volume|vol)\b'),
 ('Nightdresses',r'\bnight(?:y|ie|ies|dress)\b'),
 ('Panties',r'\bpantie\b'),
 ('Pyjama Sets',r'\bp[ay]jama\s+set\b'),
 ('Cardholders',r'\bcard[ -]?holders?\b'),
 ('Jewellery Chains',r'\b(?:gold|silver|plated)\s+chain\b'),
 ('Hair Ties & Scrunchies',r'\bponytail\b'),
 ('Forehead Jewellery',r'\bjhoom(?:er|ar)\b'),
 ('Necklaces',r'\bmala\b(?!\s+set)'),
 ('Earrings',r'\bbaliyan\b'),
 ('Hair Accessory Sets',r'\bhair\s+accessor(?:y|ies)\s+(?:combo\s+)?set\b'),
 ('Artificial Nails',r'\b(?:artificial|false|press[ -]?on)\s+nails?\b'),

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
 ('Jhumka Earrings','\\bjhumk(?:ay|a|i|y)\\b'),
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
 ('Pouches',r'\bpouch(?:es)?\b'),('Bowling Bags',r'\bbowling\s+bag\b'),
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
 reviewed=json.loads(path.read_text()).get('products',[]) if path.exists() else []
 records=[]
 automatic=path.with_name('audit804-auto-source.json')
 if automatic.exists():records+=json.loads(automatic.read_text()).get('products',[])
 # Explicitly reviewed source facts outrank an automatic empty/generic refresh.
 records+=reviewed
 return {(f['store'],str(f['product_id']),f['source_url']):f for f in records}
def public_facts(row,store):
 fact=public_index().get((store,str(row.get('product_id')),row.get('source_url')))
 if fact:
  norm=lambda text:re.sub(r'[^a-z0-9]+','',unicodedata.normalize('NFKC',str(text)).casefold())
  if norm(fact['public_title'])==norm(row.get('name')):return fact
 return None

def visual_review(row,store):
 import hashlib
 path=Path(__file__).with_name('audit804-image-reviews.json')
 if not path.exists():return None
 for item in json.loads(path.read_text()).get('products',[]):
  if (item['store'],item['product_id'],item['name'],item['source_url'])!=(store,str(row.get('product_id')),row.get('name'),row.get('source_url')):continue
  if not item.get('image_url','').startswith('https://') or not re.fullmatch('[a-f0-9]{64}',item.get('image_sha256','')):continue
  description=str(row.get('description') or '')
  if hashlib.sha256(description.encode()).hexdigest()==item['input_description_sha256'] or description.startswith(item['overview']):return item
 return None

def category(row,store):
 name=str(row.get('name') or '');body=str(row.get('description') or '')
 if store=='Junaid Jamshed' and re.search(r'\bbrow\b.*\bshaping\s+gel\b',name,re.I) and re.search(r'\b(?:brow|eyebrow)\s+shape\b',body,re.I):return 'Eyebrow Gels','reviewed_source_description','Source explicitly identifies brow tinting and shaping gel: '+body[:700]
 if store=='Gul Ahmed' and re.search(r'\bapron\b',name,re.I) and re.search(r'\bcooking\b',body,re.I):return 'Kitchen Aprons','reviewed_source_description','Source identifies a cooking apron; finish and full measurements retained: '+body[:700]
 visual=visual_review(row,store)
 if visual:return visual['category'],'reviewed_primary_product_image',visual['overview']+' Image: '+visual['image_url']+' SHA256: '+visual['image_sha256']
 if store=='Sapphire' and re.fullmatch(r'(?i)Knit Cape Jumper',str(row.get('name') or '').strip()) and re.search(r'(?i)\bknit\s+cape\s+jumper\b',str(row.get('description') or '')):return 'Ponchos & Capes','reviewed_source_description','Source explicitly names a knit cape jumper; fabric percentages and measurements unchanged.'
 if store not in STORES:return None
 name=str(row.get('name') or '');body=str(row.get('description') or '')
 if store=='Stylo':
  for pattern,label in [
   (r'\bfishing\s+gogo\s+for\s+kids\b','Fishing Games'),
   (r'\bbuilding\s+blocks\s+for\s+kids\b','Building Block Sets'),
   (r'\bsalah\s+box\s+for\s+kids\b','Prayer Gift Sets'),
   (r'\bono\s+for\s+kids\b','Card Games'),
   (r'\bremote\s+control\s+pickup\s+truck\b','Remote Control Trucks'),
   (r'\bremote\s+control\s+aeroplane\b','Remote Control Aircraft')]:
   if re.search(pattern,name,re.I):return label,'reviewed_source_product_purpose','Named source product and complete contents retained: '+name+'; '+body[:450]
  for pattern,label in [
   (r'\btank\s+top\b','Tank Tops'),
   (r'\bsofty\b','Casual Footwear'),
   (r'\b(?:liquid|wax)\s+polish\b|\bshoe\s+shiner\b','Shoe Polishes'),
   (r'\b(?:gel\s+(?:pressure\s+point\s+)?pad|gel\s+insole)\b','Shoe Cushioning Pads'),
   (r'\bschools?\s+shoes\b','School Shoes'),
   (r'\blong\s+shoes\b','Boots & High-Top Shoes'),
   (r'\bsnearker\b','Sneakers'),
   (r'\bshrug\b','Shrugs'),
   (r'\bdupp?atta\b|\bduppata\b','Dupattas'),
   (r'\b(?:dinky|dinkies|toy\s+car|truck\s+set)\b','Toy Vehicles'),
   (r'\blcd\s+panel\s+for\s+kids\b','LCD Writing Tablets'),
   (r'\bmind\s+sharpening\s+game\b','Educational Games'),
   (r'\bmontessori\s+mind\s+creative\s+sticks\b','Educational Construction Toys'),
   (r'\b(?:alphabet\s+spelling|wooden\s+scrabble)\b','Spelling Games'),
   (r'\bnail\s+board\s+lacing\b','Lacing & Threading Toys'),
   (r'\bkitchen\s+set\s+for\s+kids\b','Toy Kitchen Sets'),
   (r'\banimal\s+figures\s+for\s+kids\b','Toy Animal Figures'),
   (r'\bdoctor\s+set\s+for\s+kids\b','Toy Doctor Sets'),
   (r'\bclay\s+(?:dough|sets?)\s+for\s+kids\b','Modelling Dough Sets'),
   (r'\barrow\s+shooter\s+for\s+kids\b','Toy Archery Sets'),
   (r'\bdrawing\s+board\s+for\s+kids\b','Drawing Boards'),
   (r'\bshooting\s+gun\s+for\s+kids\b','Foam Dart Toys'),
  ]:
   if re.search(pattern,name,re.I):return label,'reviewed_source_product_purpose','Named sold object; supplied source specifications and contents retained: '+name+'; '+body[:350]
  if re.search(r'\bgift\s+pack\s+for\s+men\b',name,re.I) and re.search(r'\bwallet\b',body,re.I) and re.search(r'\b(?:belt|keychain|key\s+case|card\s+holder|cufflinks|pen)\b',body,re.I):return 'Mens Accessory Gift Sets','reviewed_source_description','Source explicitly names wallet and companion items in the complete accessory set: '+body[:500]
  if re.search(r'\bfashion\s+set\s+for\s+kids\b',name,re.I):
   if re.search(r'\bbeading\s+kit\b',body,re.I):return 'Jewellery Making Kits','reviewed_source_description','Source explicitly names a beading kit: '+body[:450]
   if re.search(r'\b(?:princess|dress\s+up)\b',body,re.I):return 'Dress-Up Accessory Sets','reviewed_source_description','Source explicitly identifies pretend dress-up accessories: '+body[:450]
  if re.search(r'\bcasual\s+shoes\b',name,re.I) and re.search(r'\bboat\s+shoes\b',body,re.I):return 'Boat Shoes','reviewed_source_description','Source explicitly identifies boat shoes: '+body[:350]
 if store=='Gul Ahmed':
  if re.search(r'\bplacemat\b.*\brunner\b.*\bset\b',name,re.I):return 'Table Linen Sets','reviewed_product_name','Source explicitly names the complete placemat and runner set: '+name
  if re.search(r'\bbed\s*spread\s+set\b',name,re.I):return 'Bedspread Sets','reviewed_product_name','Source names a bedspread set: '+name
  if re.search(r'\bcomplete\s+bed\s+set\b',name,re.I):return 'Bedding Sets','reviewed_product_name','Source explicitly names a complete bed set: '+name
  if re.search(r'\bfleece\b',name,re.I) and re.search(r'\bfleece\s+throw\b',body,re.I):return 'Throws & Blankets','reviewed_source_description','Source explicitly names a fleece throw: '+body[:350]
  if re.search(r'\bregular\s+fit\b.*\bsuits\b',name,re.I) and not re.search(r'\bunstitched\b|\b\d+(?:\.\d+)?\s*(?:meters?|metres?|mtr)\b',body,re.I):return 'Ready-to-Wear Suits','reviewed_product_name','Source explicitly names regular-fit suits: '+name
  for pattern,label in [
   (r'\bplace\s+mat','Placemats'),
   (r'\bpillow\s+covers\b|\bpillow\s+pack\b','Pillowcase Sets'),
   (r'\b(?:bed\s*sheet|sheet)\s+set\b','Bed Sheet Sets'),
   (r'\bquilt\s*cover\s+set\b','Duvet Cover Sets'),
   (r'\bnapkin\s+set\b','Table Napkin Sets'),
   (r'\b(?:fish|steak)\s+platter\b','Serving Platters'),
   (r'\btrinket\s+tray\b','Trinket Trays'),
   (r'\bash\s*tray\b','Ashtrays'),
   (r'\bcake\s+dish\b','Cake Dishes'),
   (r'\b(?:collar|dinner)\s+plate\b','Dinner Plates'),
   (r'\bhooded\s+zipper\b','Zip-Up Hoodies'),
   (r'\b(?:earrings|earings)\b','Earrings'),
   (r'\bco-ord\s+top\b','Tops')]:
   if re.search(pattern,name,re.I):return label,'reviewed_product_name','Exact sold item named in source: '+name
  if re.search(r'\bkolhapuri\b',name,re.I) and not re.search(r'\b(?:fabric|shirt|suit|kurta)\b',name,re.I):return 'Kolhapuri Sandals','reviewed_regional_product_name','Named Kolhapuri footwear design: '+name
  if re.search(r'\brunner\b',name,re.I) and re.search(r'\btable\s+runner\b',body,re.I):return 'Table Runners','reviewed_source_description','Source explicitly identifies a table runner: '+body[:350]
  if re.search(r'\bzero\s+twist\b.*\bset\b',name,re.I) and re.search(r'\btowels?\b',body,re.I):return 'Towel Sets','reviewed_source_description','Source zero twist towels supplied as a set: '+body[:350]
  if re.search(r'\bratan\s+basket\b',name,re.I) and re.search(r'\brattan\s+basket\b',body,re.I):return 'Storage Baskets','reviewed_source_description','Source explicitly names a rattan storage basket: '+body[:350]
  if re.search(r'\bmulti\s+purpose\s+mat\b',name,re.I) and re.search(r'\bquilted\s+mat\b',body,re.I):return 'Quilted Multipurpose Mats','reviewed_source_description','Source explicitly names a quilted multipurpose mat: '+body[:350]
  if name=='Black' and row.get('website_category_status') in ('verified_product_breadcrumb','verified_navigation_membership') and 'trousers' in str(row.get('website_category_path','')).casefold():return 'Trousers','verified_source_category_path',str(row['website_category_path'])
  for pattern,label in [
   (r'\bunstitched\b.*\bfabric\b','Unstitched Fabric'),
   (r'\bplacemat\b.*\brunner\b.*\bset\b','Table Linen Sets'),
   (r'\bplacemat','Placemats'),
   (r'\bpillow\s+cover\s+set\b','Pillowcase Sets'),
   (r'\bpillow\s+cover\b','Pillowcases'),
   (r'\bquilt\s+cover\s+set\b','Duvet Cover Sets'),
   (r'\bcomforter\s+set\b','Comforter Sets'),
   (r'\bfitted\s+sheet\s+set\b','Fitted Sheet Sets'),
   (r'\bfitted\s+sheet\b','Fitted Sheets'),
   (r'\btowel\b.*\bset\b','Towel Sets'),
   (r'\btowel\b','Towels'),
   (r'\bbath\s*robe','Bathrobes'),
   (r'\bbath\s+mat\b','Bath Mats'),
   (r'\b(?:throw|blanket)\b','Throws & Blankets'),
   (r'\bcurtain','Curtains'),
   (r'\btable\s+cover\b','Tablecloths'),
   (r'\bprayer\s+mat\b','Prayer Mats'),
   (r'\bportable\s+mattress','Portable Mattresses'),
   (r'\bover[ -]?shirt\b','Overshirts'),
   (r'\b(?:girl|boys?)\b.*\bshorts?\b','Shorts'),
   (r'\b(?:co-ord|knit|printed)\s+bottom\b|^bottom$','Trousers'),
   (r'\bdenim\s+jacket','Denim Jackets'),
   (r'\bjump\s*suit','Jumpsuits')]:
   if re.search(pattern,name,re.I):return label,'reviewed_product_name','Explicit primary sold item: '+name
  if re.search(r'\bpeshawari\b',name,re.I) and re.search(r'\b(?:sandals?|chappal|sole|footwear)\b',body,re.I):return 'Peshawari Chappals','reviewed_source_description','Peshawari footwear named in source: '+body[:350]
  if re.search(r'\bkolhapuri\b',name,re.I) and re.search(r'\b(?:sole|footwear|sandals?)\b',body,re.I):return 'Kolhapuri Sandals','reviewed_source_description','Kolhapuri footwear source: '+body[:350]
  if re.search(r'\bsuits?\b',name,re.I) and re.search(r'\b(?:regular\s+fit|relaxed\s+fit|model\s+(?:size|specs)|wearing\s+size)\b',body,re.I) and not re.search(r'\bunstitched\b|\b\d+(?:\.\d+)?\s*(?:meters?|metres?|mtr)\b',body,re.I):return 'Ready-to-Wear Suits','reviewed_source_description','Named suit with source garment fit and worn-size evidence: '+body[:400]
  if re.search(r'\bknitted\s+zipper\b',name,re.I) and re.search(r'\b(?:winter|warmth|layering)\b',body,re.I):return 'Zip-Up Knitwear','reviewed_source_description','Named winter knitted zipper: '+body[:350]
  if re.search(r'\bdeo\b',name,re.I) and re.search(r'\bdeo\s+spray\b',body,re.I):return 'Deodorant Sprays','reviewed_source_description','Explicit source Type: Deo Spray. '+body[:350]
  if re.search(r'\bdiscovery\s+set\b',name,re.I) and re.search(r'\bfragrance\b',body,re.I):return 'Fragrance Sets','reviewed_source_description','Named fragrance set and full source bottle count: '+body[:500]
  if name=='Memory Foam' and re.search(r'\b(?:memory|contour)\s+pillow\b',body,re.I):return 'Pillows','reviewed_source_description','Source explicitly identifies a memory foam pillow: '+body[:350]
  if re.search(r'\bmultipurpose\s+mat\b',name,re.I) and re.search(r'\bquilted\s+mat\b',body,re.I):return 'Quilted Multipurpose Mats','reviewed_source_description','Source quilted exercise/play mat with measurements retained: '+body[:500]
  if re.search(r'\bskecher\b',name,re.I) and re.search(r'\bsneakers\b',body,re.I):return 'Sneakers','reviewed_source_description','Source explicitly identifies footwear as sneakers: '+body[:350]
 if store=='Rawayat':
  for pattern,label in [
   (r'\bhair\s+poni\b|\b(?:organza|beaded)\s+pony\b','Hair Ties & Scrunchies'),
   (r'\bhair\s+catcher','Hair Claws'),
   (r'\bmathapatti','Forehead Jewellery'),
   (r'\bhair\s+vine','Hair Jewellery'),
   (r'\b(?:double|dot)\s+chain\b','Jewellery Chains'),
   (r'\bhair\s+accessor(?:y|ies)\b.*\b(?:sunglesses|sunglasses)\b','Hair Accessories & Sunglasses Sets'),
   (r'\bbag\s+hair\s+accessory\s+box','Hair Accessory Sets'),
   (r'\bstuds\s+earrings\b.*\bbindiya\b.*\bring\b','Jewellery Sets'),
   (r'\biraqi\s+coin\b','Commemorative Coins'),
   (r'\bcoin\s+card\b','Commemorative Coin Cards')]:
   if re.search(pattern,name,re.I):return label,'reviewed_product_name','Explicit named object and accessories: '+name
 if store=='Elite Cosmetics':
  if re.search(r'\bcelimax\s+retinal\s+shot\s+tightening\s+booster\b',name,re.I) and re.search(r'\bconcentrated\b.*\btreatment\b',body,re.I) and re.search(r'\bfirm\s+skin\b',body,re.I):return 'Facial Treatments','reviewed_source_description','Primary retailer explicitly describes a concentrated skin-firming treatment; concentrations retained: '+body[:700]
  if re.search(r'\burgent\s+facial\b',name,re.I) and not re.search(r'\b(?:hand|feet|foot)\b',name,re.I) and re.search(r'\bface\b',body,re.I):return 'Facial Treatments','reviewed_source_description','Source names a facial treatment and face application: '+body[:500]
  for pattern,label in [
   (r'\bexfoliating\b.*\bgel\b','Skin Scrubs & Exfoliators'),
   (r'\b(?:facial\s+whitening\s+powder\s+mask|blackhead\s+nose\s+mask|derma\s+fleece\s+collagen\s+sheet|rejuvenating\s+mask|bioaqua\b.*\bmask|essence\s+mask)\b','Skin Masks'),
   (r'\beye\s+mask\b','Eye Masks'),
   (r'\bhair\s+band\b','Headbands'),
   (r'\bhair\s+catcher','Hair Claws'),
   (r'\bhair\s+ponies','Hair Ties & Scrunchies'),
   (r'\bfacial\s+wipes','Facial Cleansing Wipes'),
   (r'\bdouble\s+sided\s+mirror','Personal Mirrors'),
   (r'\b(?:pure\s+skin\s+anti\s+acne\s+cleanser|deep\s+clean\s+gel\s+wash)\b','Face Cleansers')]:
   if re.search(pattern,name,re.I):return label,'reviewed_source_description','Named product purpose supported by supplied source description: '+name+'; '+body[:350]
  if re.search(r'\b3dx\s+bleach\b',name,re.I) and re.search(r'\bfacial\s+and\s+body\s+hair\b',body,re.I):return 'Facial & Body Hair Bleaches','reviewed_source_description','Source explicitly states facial and body hair bleaching: '+body[:400]
  if re.search(r'\bmud\s+plus\s+lavender\b',name,re.I) and re.search(r'\bapply\b.*\bface\s+and\s+neck\b',body,re.I):return 'Skin Masks','reviewed_source_description','Source instructs paste application to face and neck: '+body[:400]
  if re.search(r'\blactic\s+acid\s+5%',name,re.I) and re.search(r'exfoliat',body,re.I):return 'Facial Exfoliating Treatments','reviewed_source_description','Named lactic acid with source exfoliation purpose: '+body[:500]
  if re.search(r'\bcaffeine\s+solution',name,re.I) and re.search(r'eye\s+contour',body,re.I):return 'Eye Treatments','reviewed_source_description','Source directs use on eye contour: '+body[:500]
  if re.search(r'\bhyaluronic\s+acid\s+2%',name,re.I) and re.search(r'face',body,re.I):return 'Face Serums','reviewed_source_description','Named hydrating solution applied to face: '+body[:500]
  if re.search(r'\b(?:face\s+guard\s+advanced|brightening\s+day\s+protection)\b',name,re.I) and re.search(r'\bSPF\s*\d+',body,re.I):return 'Facial Sun Protection','reviewed_source_description','Source explicitly states facial sun protection SPF: '+body[:600]
 if store=='Stylo' and row.get('brand')=='Teenage' and re.search(r'(?i)\bbeede\b',name) and re.search(r'(?i)\bgirls\b',name):return 'Girls Training Bras','reviewed_regional_product_name','Reviewed source Padded BD/Non Padded BD naming and actual product images; no fabric composition inferred: '+name
 if store=='Junaid Jamshed' and row.get('brand') in SOURCE_TYPES:return SOURCE_TYPES[row['brand']],'reviewed_source_product_type','Explicit source product_type: '+row['brand']
 if re.search(r'(?i)\bcompact\b',name) and re.search(r'(?i)\bpowder\b',body) and re.search(r'(?i)\bface\b',body):return 'Face Powders','reviewed_source_description','Source describes a face compact powder; fragrance is a formulation attribute: '+name+'; '+body[:300]
 if store=='Hemani Herbals' and row.get('website_category_path')=='Body Spray' and row.get('website_category_status') in ('verified_navigation_membership','verified_product_breadcrumb') and re.search(r'(?i)\b(?:spray|fragrance)\b',body):return 'Body Sprays','reviewed_source_breadcrumb','Verified source Body Spray breadcrumb and application directions: '+name
 source=public_facts(row,store)
 if source:
  bundle=source.get('reviewed_bundle',{})
  if store=='Bonanza Satrangi' and bundle.get('status')=='active' and bundle.get('category') in ('Fragrance Bundles','Makeup Bundles') and bundle.get('configuration_sha256') and bundle.get('products'):return bundle['category'],'reviewed_public_bundle_configuration',source['description']+'; '+bundle['configuration_source_url']
  types={'earring':'Earrings','earrings':'Earrings','earstuds':'Stud Earrings','jhumka':'Jhumka Earrings','karay':'Bangles & Karas','bangles':'Bangles & Karas','necklace':'Necklaces','necklaces':'Necklaces','bracelets':'Bracelets','anklet':'Anklets','anklets':'Anklets','ring':'Rings','pendent':'Pendants & Lockets','nath':'Nose Jewellery','bindiya kanta':'Forehead Jewellery','choker set':'Jewellery Sets','mala set':'Jewellery Sets','locket set':'Jewellery Sets','bridal set':'Jewellery Sets','jeans':'Jeans'}
  if source.get('reviewed_visual_type')=='Jeans' and source.get('reviewed_visual_evidence',{}).get('sha256'):return 'Jeans','reviewed_product_image','Actual product image reviewed: '+source['reviewed_visual_evidence']['source_url']
  if str(source.get('product_type') or '').casefold()=='luxury unstitch' and re.search(r'(?i)\bshirt\s+shalwar\s+dupatta\b',name):return 'Unstitched Suits','reviewed_public_product_type','Source-listed Luxury Unstitch and named shirt, shalwar, dupatta; '+source['source_url']
  if str(source.get('product_type') or '').strip().casefold()=='necklace' and re.search(r'(?i)\bset\b',name):return 'Jewellery Sets','reviewed_public_product_type','Source necklace family and explicit set name: '+name+'; '+source['source_url']
  label=types.get(str(source.get('product_type') or '').strip().casefold())
  if label:return label,'reviewed_public_product_type','Public product_type: '+source['product_type']+'; evidence run '+source['evidence_run']+'; '+source['source_url']

 for label,pattern in NAMED:
  if label=='Scented Candles' and re.search(r'(?i)\b(?:holder|snuffer|trimmer)\b',name):continue
  if label=='Shilajit Supplements' and re.search(r'(?i)\bgummies\b',name):continue
  if label=='Tops' and (not re.search(r'(?i)\b(?:knit|sleeve|capelet|ribbed|jersey|cotton)\b',name+' '+body[:300]) or store in {'Computer Zone','Elite Cosmetics','Hemani Herbals','Rivaj UK','Cool and Cool','Saeed Ghani'} or re.search(r'(?i)\b(?:makeup|cosmetic|lipstick|cream|serum|bundle)\b',name)):continue
  if label=='Cooling Fans' and re.search(r'(?i)\b(?:hub|controller|cable|adapter)\b',name.split(',')[0]):continue
  if label=='Rings' and re.search(r'(?i)\bearrings?\b.*\bbindiya\b',name):return 'Jewellery Sets','reviewed_product_name','All source-named items: '+name
  if label=='Rings' and store=='Computer Zone':continue
  if label=='Rings' and re.search(r'(?i)\b(?:key|curtain|napkin|phone|holder|case|light|binder)\b',name):continue
  if label=='False Eyelashes' and re.search(r'(?i)\b(?:serum|growth|glue|adhesive|mascara|oil)\b',name):continue
  if re.search(pattern,name,re.I):return label,'reviewed_product_name','Explicit sold-object wording: '+name
 if re.search(r'(?i)\b(?:apply perfume|fragrance notes)\b',body) and re.search(r'(?i)\b(?:top|base|mid|dry)\s+note',body) and not re.search(r'(?i)\b(?:hand cream|body lotion|soap|wash)\b',name):return 'Perfumes & Fragrances','reviewed_source_description','Explicit fragrance use and note tiers: '+name+'; '+body[:500]
 if store=='Stylo' and re.search(r'(?i)\bsofty\b',name) and (re.search(r'(?i)\b(?:feet|footbed|strap|footwear|shoes)\b',body+' '+str(row.get('website_category_path') or ''))):return 'Casual Footwear','reviewed_source_description','Named Softy with explicit source footwear/foot context: '+name+'; '+body[:300]
 if store=='Stylo' and re.search(r'(?i)\bcasual\s+canvas\b',name) and re.search(r'(?i)\b(?:heel|footbed|sole|shoes)\b',body):return 'Canvas Shoes','reviewed_source_description','Canvas shoe source describes heel/sole: '+name+'; '+body[:300]
 if store=='Rawayat' and re.search(r'(?i)\bchain\b',name) and not re.search(r'(?i)\b(?:bag|bike|motor|engine)\b',name):return 'Jewellery Chains','reviewed_product_name','Named jewellery chain: '+name
 if re.search(r'(?i)\b(?:crossbody|cross[ -]body)\s*bag\b',name):return 'Cross-Body Bags','reviewed_product_name',name
 if re.search(r'(?i)\bshoulder\s*bag\b',name):return 'Shoulder Bags','reviewed_product_name',name
 if re.search(r'(?i)\btote\s*bag\b',name):return 'Tote Bags','reviewed_product_name',name
 if re.search(r'(?i)\bhand\s*bag\b',name):return 'Handbags','reviewed_product_name',name
 if re.search(r'(?i)\bbag\b',name):return 'Bags','reviewed_product_name','Product explicitly named a bag: '+name
 if re.search(r'(?i)\b(?:palette)\b',name) and re.search(r'(?i)\b(?:eyes?|eyeshadow|eye\s*makeup)\b',body):return 'Eyeshadow Palettes','reviewed_source_description','Source identifies eye makeup palette: '+name+'; '+body[:500]
 if re.search(r'(?i)\b(?:skin|face)\s+polish',name):return 'Skin Polishes','reviewed_product_name','Explicit skin polish: '+name
 if re.search(r'(?i)\bface\b',str(row.get('website_category_path') or '')) and re.search(r'(?i)\btoner\b',str(row.get('website_category_path') or '')) and re.search(r'(?i)\bmist\b',name):return 'Face Mists & Toners','verified_navigation_membership',str(row['website_category_path'])+'; '+name
 if re.search(r'(?i)\bscrub\b',name) and (re.search(r'(?i)\b(?:facial|face)\b',str(row.get('website_category_path') or '')) or re.search(r'(?i)\b(?:face|facial)\b',body)):return 'Face Scrubs & Exfoliators','reviewed_source_description','Facial scrub source context: '+name+'; '+str(row.get('website_category_path'))
 if re.search(r'(?i)\b(?:black|charcoal)\s+(?:peel.off\s+)?mask\b',name) and re.search(r'(?i)\bskin\b',body):return 'Skin Masks','reviewed_source_description','Skin mask source: '+name+'; '+body[:500]
 if re.search(r'(?i)\b(?:skin|body)\b',body) and re.search(r'(?i)\bscrub\b',name):return 'Skin Scrubs & Exfoliators','reviewed_source_description','Scrub with source skin application: '+name+'; '+body[:300]
 if re.search(r'(?i)\bbuy\b.*\bget\b.*\bfree\b',name) and re.search(r'(?i)\b(?:lotion|rose\s+water)\b',name):return 'Skin Care Bundles','reviewed_source_description','Named paid and complimentary skin-care items: '+name+'; '+body
 if re.search(r'(?i)\bbundle\b',name) and re.search(r'(?i)\bsunscreen\b',body):return 'Sun Care Bundles','reviewed_source_description','Source names sunscreen combo pack: '+name+'; '+body
 if re.search(r'(?i)\bfoundation\b',name) and not re.search(r'(?i)\b(?:brush|sponge|applicator|concealer|contour)\b',name):return 'Foundations','reviewed_product_name','Foundation is the sold product; oil-free is a formulation attribute: '+name
 if re.search(r'(?i)\blotion\b',name) and re.search(r'(?i)\bbody\s+lotion\b',body):return 'Body Lotions','reviewed_source_description','Explicit source body lotion: '+name+'; '+body[:300]
 if re.search(r'(?i)\blotion\b',name) and not re.search(r'(?i)\b(?:hair|baby|lip|foot|hand)\b',name):return 'Skin Lotions','reviewed_product_name','Named skin lotion: '+name
 if re.search(r'(?i)\b(?:moisturizing|moisturising)\s+(?:water\s+)?gel\b',name) and re.search(r'(?i)\bskin\b',body):return 'Skin Moisturising Gels','reviewed_source_description','Named moisturising gel with skin context: '+name+'; '+body[:500]
 if re.search(r'(?i)\boil\b',name) and re.search(r'(?i)\bbaby\b',name):return 'Baby Oils','reviewed_product_name','Explicit baby oil: '+name
 if re.search(r'(?i)\bhand\s+elixir\b',name) and re.search(r'(?i)\bhydrat|moisturi',body):return 'Hand Moisturisers','reviewed_source_description','Source hand hydration purpose: '+name+'; '+body[:400]
 if re.search(r'(?i)\boil\b',name) and not re.search(r'(?i)\b(?:perfume|attar|ittar|fragrance|wash|serum|cream|soap|gel|shampoo|conditioner|spray|mask|scrub|foundation)\b',name):
  hair=bool(re.search(r'(?i)\bhair\b',body));skin=bool(re.search(r'(?i)\bskin\b',body))
  if hair and skin:return 'Hair & Skin Oils','reviewed_source_description','Source lists both hair and skin uses: '+name+'; '+body[:600]
  if hair:return 'Hair Oils','reviewed_source_description','Source hair application: '+name+'; '+body[:600]
  if skin:return 'Skin Oils','reviewed_source_description','Source skin application: '+name+'; '+body[:600]
 if re.search(r'(?i)\boil\b',name) and re.search(r'(?i)\b(?:easy.to.consume|this supplement|daily nutritional care)\b',body) and not re.search(r'(?i)\b(?:hair|shampoo|cream|soap|fragrance)\b',name):return 'Dietary Supplement Oils','reviewed_source_description','Source explicitly describes consumption/nutritional supplementation; no dose or health claim invented: '+name+'; '+body[:500]
 if re.search(r'(?i)\bherbal\s+oil\b',name):return 'Herbal Oils','reviewed_product_name','Source explicitly names herbal oil; no ingestion/topical use inferred: '+name
 if re.fullmatch(r'(?i)Gift Basket',name.strip()) and re.search(r'(?i)\byou can fill\b',body):return 'Gift Baskets','reviewed_source_description','Empty customizable basket; source says buyer fills it: '+body
 if re.search(r'(?i)\b(?:bundle|trio|basket|gift\s*box|self.care\s+set)\b',name):
  if re.search(r'(?i)\b(?:skincare|skin|face\s+wash|cream|lotion)\b',body):
   label='Personal Care Bundles' if re.search(r'(?i)\b(?:haircare|fragrance|beard)\b',body) else 'Skin Care Bundles'
   return label,'reviewed_source_description','Source gift/bundle purpose and contents: '+name+'; '+body[:800]
 if re.search(r'(?i)\bbb\s+skin\s+editor\b',name) and re.search(r'(?i)\b(?:spf|matte|skin)\b',body):return 'BB Face Makeup','reviewed_source_description','Named BB makeup with supplied skin finish and SPF facts: '+name+'; '+body[:350]
 if store=='Rawayat' and re.search(r'(?i)\bset\b',name+' '+body[:150]) and re.search(r'(?i)jewel(?:lery|ry)\s+care',body) and not re.search(r'(?i)\b(?:chain|ponytail|hair|nails?)\b',name):return 'Jewellery Sets','reviewed_source_description','Named/source-listed jewellery set and jewellery-care context: '+name+'; '+body[:200]
 if re.search(r'(?i)\b(?:fancy|short|bridal|choker|necklace|traditional|pendent|pendant)\b.*\bset\b',name) and re.search(r'(?i)jewel(?:lery|ry)\s+care|gold\s+plat',body):return 'Jewellery Sets','reviewed_source_description','Named jewellery set and source jewellery-care context: '+name+'; '+body[:200]
 return None

def description(row,store):
 original=str(row.get('description') or '');name=str(row.get('name') or '');body=original.strip()
 if store=='Elite Cosmetics' and body==name and re.search(r'(?i)\broll.on\s+deodorant',name):return name+' is a roll-on deodorant.','Rewrote exact named deodorant identity; scent, audience, duration label and volume retained.'
 if store=='Rawayat' and name=='Gift Box' and body=='Add Gift Box & Bag':return 'Gift packaging comprising a gift box and bag.','Rewrote both explicitly offered packaging items; no size or material invented.'
 visual=visual_review(row,store)
 if visual and not body.startswith(visual['overview']):
  useful=original if body not in ('',name,'Rawayat','dsasd') else ''
  if visual.get('replace_wrong_product_body'):useful=''
  if visual.get('correct_leading_copy'):
   old,new=visual['correct_leading_copy']
   if useful.startswith(old):useful=new+useful[len(old):]
  return visual['overview']+('\n\n'+useful if useful else '\n\nListing: '+name),'Added reviewed primary-image object types and contents; source composition not guessed and all supplied facts retained.'
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
 if source and store=='Rawayat':
  kind=str(source.get('product_type') or '').strip().casefold()
  overview={'necklace':'a necklace design','earring':'an earring design','earrings':'an earring design','earstuds':'a stud-earring design','nath':'a nose jewellery design','bindiya kanta':'a forehead jewellery design','ring':'a ring design','bracelets':'a bracelet design','anklet':'an anklet design','anklets':'an anklet design','pendent/chain':'a pendant necklace design','pendent/necklace':'a pendant necklace design','choker set':'a jewellery set','mala set':'a jewellery set','locket set':'a jewellery set','bridal set':'a jewellery set'}.get(kind)
  if overview and re.search(r'(?i)\bset\b',name) and kind in ('necklace','choker set','mala set','locket set','bridal set'):overview='a jewellery set'
  if overview:
   lead=name+' is '+overview+'.'
   if not body.startswith(lead):return lead+('\n\n'+original if body and body!=name else ''),'Added exact matching public product_type as a factual overview; all existing product/care details retained.'
 if store=='Junaid Jamshed' and body.split('\n\nProduct Options:')[0].strip()==name:
  kind={'Women Stitched Sari':'a stitched saree','Men Special Kurta':'a special kurta for men','Men Kurta':'a kurta for men','Women Powder':'a makeup powder','Women Eyebrow Kit':'an eyebrow makeup kit'}.get(row.get('brand'))
  if kind:return name+' is '+kind+'.'+original[len(name):],'Rewrote exact source product_type; existing options preserved.'
 if source and body in ('0','','None') and str(source.get('product_type') or '').casefold()=='luxury unstitch' and re.search(r'(?i)\bshirt\s+shalwar\s+dupatta\b',name):return name+' is an unstitched outfit with a shirt, shalwar and dupatta.','Rewrote explicit source product_type and all three named components; no fabric, embroidery technique or quantities inferred.'
 if source and body in (name,'','0','None') and source.get('description') and source['description'].strip()!=name:
  return name+'.\n\n'+source['description'],'Restored exact matching primary public product description; listing identity retained.'
 if source and (str(source.get('product_type')).casefold()=='jeans' or source.get('reviewed_visual_type')=='Jeans') and not body.startswith(name+' is a denim jeans style.'):
  return name+' is a denim jeans style.'+('\n\n'+original if not body.startswith(name) else original[len(name):]),'Added the public product_type Jeans; every saved option retained.'
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
  phrases={'Unstitched Fabric':'unstitched fabric','Scarves':'a scarf','Hair Jewellery':'a hair jewellery design','Personal Mirrors':'a personal grooming mirror','Skin Masks':'a skin mask','Commemorative Coin Cards':'a commemorative coin card','Hair Accessories & Sunglasses Sets':'a set of hair accessories and sunglasses','Hoop Earrings':'a hoop-earring design','Hand Harnesses':'a hand-jewellery harness','Belts':'a belt','Commemorative Coins':'a commemorative coin','Gift Boxes':'a gift box','Hand Mirrors':'a handheld mirror','Makeup Puff & Clip Sets':'a makeup puff and clip set','Hair Accessory Sets':'a hair accessory set','Hair Crowns & Tiaras':'a hair crown or tiara design','Hair Combs':'a hair comb','Nail Care Kits':'a nail care kit','Stationery Sets':'a stationery set','Artificial Nails':'an artificial nail design','Watches':'a watch','Jewellery Chains':'a jewellery chain design','Pendant Necklaces':'a pendant necklace design','Nose Jewellery':'a nose jewellery design','Forehead Jewellery':'a forehead jewellery design','Hair Claws':'a hair claw design','Hair Brushes & Combs':'a hair-styling brush','Lip Balms':'a lip balm','Earrings':'an earring design','Stud Earrings':'a stud-earring design','Jhumka Earrings':'a jhumka-earring design','Rings':'a ring design','Bracelets':'a bracelet design','Necklaces':'a necklace design','Anklets':'an anklet design','Pendants & Lockets':'a locket design' if 'locket' in name.casefold() else 'a pendant design','Hair Clips & Pins':'a hair pin design' if 'pin' in name.casefold() else 'a hair clip design','Headbands':'a headband','Jewellery Sets':'a jewellery set','Hair Ties & Scrunchies':'a hair-tie design','Bangles & Karas':'a bangle or kara design','Brooches':'a brooch design'}
  if result and result[0] in phrases:return name+' is '+phrases[result[0]]+'.','Rewrote the supplied listing name as a factual product-specific overview; no missing material, quantity, benefit or stock invented.'
 return original,None
