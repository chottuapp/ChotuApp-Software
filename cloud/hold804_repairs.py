"""Reviewed, source-bound purpose and prose repairs for the twelve held workbooks."""
import re,json,unicodedata
from pathlib import Path
from functools import lru_cache
from datetime import datetime,timezone
from urllib.parse import urlsplit
SOURCE_TYPES={'SYNCC - Women Sweater':'Sweaters','Women Stitched Sari':'Sarees','Men Peshawari Chappal':'Chappals','Women Trouser':'Trousers','Women Earrings':'Earrings','Women Bracelet':'Bracelets','Women Necklace':'Necklaces','Women Ring':'Rings','Women Eyebrow Kit':'Eyebrow Kits','Infants Stitched 3 Piece':'Stitched Outfit Sets','Men Waistcoat With Kurta Trouser':'Clothing Sets'}
STORES={'Sana Safinaz','Edenrobe','Beechtree','Breakout','Liberty Books','ChenOne','Generation','Saya','Hush Puppies','Habitt','Beyond East','Rios','Mala','Limelight','Alkaram Studio','Prime Ticks','Hilm Chapals','Golden Rose','Zyren','Pyari Walls','Design by DAS','Xcessories Hub','Bachaa Party','Gul Ahmed','Miss Rose','Cool and Cool','Rivaj UK','Computer Zone','Saeed Ghani','Elite Cosmetics','Hemani Herbals','Bonanza Satrangi','Rawayat','Junaid Jamshed','Outfitters','Zellbury','Stylo'}
# Explicit object names. Compatibility targets, ingredients and care text are not classifiers.
NAMED=[
 ('Makeup Sponges',r'\bsilicon(?:e)?\s+(?:makeup\s+)?blender\b'),
 ('Quilt Covers',r'\bquilt\s+cover\b'),
 ('Duvet Covers',r'\bduvet\s+cover\b'),
 ('Peshawari Chappals',r'\bpeshawari\b'),
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
 from review_evidence_cache import read_review_evidence
 for item in read_review_evidence(path).get('products',[]):
  if (item['store'],item['product_id'],item['name'],item['source_url'])!=(store,str(row.get('product_id')),row.get('name'),row.get('source_url')):continue
  if not item.get('image_url','').startswith('https://') or not re.fullmatch('[a-f0-9]{64}',item.get('image_sha256','')):continue
  description=str(row.get('description') or '')
  digest=hashlib.sha256(description.encode()).hexdigest()
  if digest==item['input_description_sha256'] or digest==item.get('cleaned_description_sha256') or description.startswith(item['overview']):return item
 return None

def maali_kind(row,fact=None):
 title=str(row.get('name') or '');body=str(row.get('description') or '')
 proof=bool(fact and (str(fact.get('product_type') or '').upper()=='PLANTS' or fact.get('plant_care_description')))
 proof=proof or ('Live plant care' in body and 'Light:' in body and 'Watering:' in body)
 proof=proof or bool(re.search(r'\bplant\s+with\s+grow\s+bag\b',title,re.I))
 # A source combo explicitly lists multiple plants even when its title says Offer.
 listed_set=bool(re.search(r'\b[2-9]\s+(?:[A-Za-z]+\s+){0,4}plants\b',body,re.I)
                 and re.search(r"what.s included in this combo",body,re.I)
                 and len(re.findall(r'(?m)^.+?\s+[–—-]\s+\S',body))>=2)
 proof=proof or listed_set
 if not proof:return None
 return 'Live Plant Sets' if listed_set or re.search(r'\bbundle\b|\bset\s+of\s+\d+\b',title,re.I) else 'Live Plants'

def explicit_source_service(row,store):
 # Preserve the merchant's TEST qualification; do not imply real service scope.
 name=str(row.get('name') or '').strip()
 return store=='Beyond East' and bool(re.fullmatch(r'(?:TEST[- ]+)?STIT?CHING SERVICE',name,re.I)) and public_facts(row,store) is not None

def fresh_source_category(row,store):
 """Explicit sold objects in held source rows; no price, stock or website inference."""
 name=str(row.get('name') or '');body=str(row.get('description') or '')
 def has(pattern,value):return bool(re.search(pattern,value,re.I))
 label=None
 if store=='Shop Modest' and has(r'\boutfit\b',name) and all(has(r'(?m)^\s*'+field+r'\s*:',body) for field in ('Top','Bottom','Dupatta')):
  label='Clothing Sets'
 if store=='Design by DAS':
  if has(r'\bsunflower\s+charm\b',name) and has(r'\bcrochet\b',body) and has(r'\b(?:keychain|bag charm)\b',body):label='Bag & Key Charms'
  if has(r'\bcrochet\s+flower\s+buttons\b',name) and has(r'\b(?:sewing|garments)\b',body):label='Sewing Buttons'
  if has(r'\bkimono\b',name) and has(r'(?m)^Fabric\s*:',body) and has(r'\bwearing\s+size\b',body):label='Kimonos'
 if store=='Habitt' and not has(r'\b(?:replacement|spare)\b|\b(?:lid|cover|tap|stand|straw)\s+for\b',name):
  objects=[('Oil Dispensers',r'\boil\s+(?:jug|dispenser)\b'),('Strainers & Colanders',r'\bmilk\s+straner\b'),('Beverage Dispensers',r'\b(?:juice|beverage)\s+dispenser\b'),('Grain Dispensers',r'\brice\s+dispenser\b'),('Serving Bowls',r'\bstainless\s+steel\b.*\bbowl\b'),('Sipper Cups',r'\bsipper\s+cup\b'),('Snack Serving Trays',r'\brotating\s+snack\s+tray\b')]
  for candidate,pattern in objects:
   if has(pattern,name):label=candidate;break
 if store=='Generation' and has(r'\bbow\s+tie\b',name) and has(r'\bbow\s+charm\b',body) and has(r'\bbag\s+tie\b',body) and has(r'\bhair\s+accessory\b',body):label='Bag & Hair Charms'
 if store=='Rios':
  if has(r'\blip\s*colou?r\b',name) and has(r'\b(?:lips|lipcolor)\b',body):label='Lip Colours'
  if has(r'\bmakeup\s+fixer\s+spray\b',name):label='Makeup Setting Sprays'
  if has(r'\bface\s+sponge\b',name) and has(r'\bcleansing\s+and\s+exfoliation\b',body):label='Facial Cleansing Sponges'
  if has(r'\bfloss\b',name):label='Dental Floss'
 if store=='Rawayat' and has(r'\bear[ -]cuff\b',name):label='Ear Cuffs'
 if store=='Limelight' and has(r'\b2\s+piece\b.*\bsaree\b',name) and has(r'(?m)^\s*Blouse\s*$',body) and has(r'(?m)^\s*Saree\s*$',body):label='Saree & Blouse Sets'
 if label:return label,'reviewed_source_sold_object','Exact source title and supplied product details: '+name
 return None

def category(row,store):
 from catalogue_object_rules import classify
 recovered=classify(row,store)
 if recovered and visual_review(row,store) is None:return recovered
 name=str(row.get('name') or '');body=str(row.get('description') or '')
 if re.search(r'\b(?:quilt|duvet)\s+cover\b',name,re.I) and re.search(r'\b[12]\s+pillow\s*cases?\b',body,re.I):return 'Duvet Cover Sets','reviewed_source_contents','Explicit cover and pillowcases supplied; no duvet filling inferred.'
 visual=visual_review(row,store)
 if visual:return visual['category'],'reviewed_primary_product_image',visual['overview']+' Image: '+visual['image_url']+' SHA256: '+visual['image_sha256']
 if explicit_source_service(row,store):return 'Stitching Services','reviewed_exact_public_service_name','Exact identity-matched source service title; test qualification retained: '+name
 explicit=fresh_source_category(row,store)
 if explicit:return explicit
 if store=='Rios':
  strong_names=[('Lipsticks', '\\blipstick\\b'), ('Hair Brushes', '\\bhair\\s*brush\\b'), ('Hair Combs', '\\bcomb\\b'), ('Toothbrushes', '\\btooth\\s*brush\\b'), ('Face Serums', '\\bface\\s+serum\\b'), ('Face Scrubs & Exfoliators', '\\bfacial\\s+scrub\\b'), ('Face Wash', '\\bface\\s+wash\\b'), ('Sunscreen Sticks', '\\bsun\\s+stick\\b'), ('Makeup Primers', '\\bprimer\\b'), ('Highlighters', '\\b(?:strobe\\s+cream|ill+uminator)\\b'), ('Eyeshadow Palettes', '\\beyeshadow\\s+palette\\b'), ('Makeup Palettes', '\\b(?:face\\s+palette|3\\s+in\\s+1\\s+palette)\\b'), ('Eyebrow Pencils', '\\bbrow\\s+pencil\\b'), ('Eyebrow Pomades', '\\b(?:brow\\s+pomade|pomade\\s+brow)\\b'), ('Cosmetic Mirrors', '\\bcosmetic\\s+mirror\\b'), ('Foot Files', '\\bfoot\\s+filer\\b'), ('Cuticle Scissors', '\\bcuticle\\s+scissor\\b'), ('Makeup Puffs', '\\b(?:makeup\\s+puff|large\\s+puff|touch\\s+me\\s+puff)\\b'), ('Bath Brushes', '\\bbath\\s+brush\\b'), ('Scissors', '\\bscissor\\b'), ('Shaving Foams', '\\bshaving\\s+foam\\b'), ('Panty Liners', '\\bpanty\\s+liners\\b'), ('Sanitary Pads', '\\b(?:Kotex|Always)\\b.*\\bpads\\b'), ('Baby Skin Creams', '\\bbaby\\s+moisturizing\\s+cream\\b'), ('Travel Bottle Sets', '\\btravel\\s+bottle\\s*\\d+\\s*pc\\b'), ('Skin Soothing Gels', '\\bskin\\s+repairing\\b.*\\bsoothing\\s+gel\\b'), ('Stretch Mark Creams', '\\bstretch\\s+marks\\s+cream\\b'), ('Hair Removal Waxes', '\\b(?:sugar\\s+wax|hard\\s+wax\\s+beads)\\b'), ('Blemish Treatments', '\\bblemish\\s+control\\s+gel\\b')]
  for label,pattern in strong_names:
   if re.search(pattern,name,re.I):return label,'reviewed_primary_sold_object','Explicit primary source product name: '+name
 if store=='ChenOne':
  if re.search(r'\bbed\s+with\s+side\s+tables\b',name+' '+body,re.I) or re.search(r'\bpackage\b',name,re.I) and re.search(r'\bbed\b',body,re.I) and re.search(r'\bdressing\s+table\b',body,re.I):return 'Bedroom Furniture Sets','reviewed_source_contents','Explicit source bed with associated furniture; no unlisted items inferred.'
  if re.search(r'\bpackage\b',name,re.I) and re.search(r'\btable\b.*\bchairs\b',body,re.I):return 'Dining Sets','reviewed_source_contents','Source package explicitly includes table and chairs.'
  if re.search(r'\bpackage\b.*\bcoffee\s+table\b',name,re.I) and re.search(r'TABLE-A.*TABLE-B',body,re.I|re.S):return 'Coffee Table Sets','reviewed_source_contents','Source separately specifies table A and table B.'
  if re.search(r'\bduvet\b',name,re.I) and not re.search(r'\bcover\b',name,re.I):return 'Duvets','reviewed_source_object','Explicit duvet title with source filling and warmth details retained.'
  if re.search(r'\bpillow\b',name,re.I) and not re.search(r'\bcover\b',name,re.I):return 'Pillows','reviewed_source_object','Explicit pillow title; source filling specifications retained.'
 if store=='Edenrobe':
  for label,pattern in [('Lapel Pins',r'\blapel\s+pin\b'),('Cufflinks',r'\bcufflinks?\b'),('Bow Ties',r'\bbow\s+tie\b'),('Pocket Squares',r'\bpocket\s+square\b'),('Collar Bars',r'\bcollar\s+bar\b'),('Lehenga Sets',r'\blehenga\s+suit\b'),('Maxi Dresses',r'\bmaxi\b'),('Formal Suits',r'\b(?:tuxedo|formal)\s+suit\b')]:
   if re.search(pattern,name,re.I):return label,'reviewed_source_object','Explicit source sold object: '+name
  if re.search(r'\bsuit\b',name,re.I) and re.search(r'\d+(?:\.\d+)?\s*M(?:eters?|etres?|tr)?\b',body,re.I) and re.search(r'\b(?:trouser|dupatta)\b',body,re.I) and not re.search(r'\bFit Type\b',body,re.I):return 'Unstitched Suits','reviewed_source_fabric_contents','Source measured fabric panels and suit components; no stitched garments inferred.'
  if re.search(r'\bsuit\b.*-3P\b',name,re.I):return 'Clothing Sets','reviewed_source_object','Source suit title explicitly identifies a three-piece article.'
 if re.search(r'\bsatchel\b',name,re.I):return 'Satchel Bags','reviewed_source_object','Source explicitly names a satchel bag.'
 reviewed_named=[]
 if store=='ChenOne' and re.search(r'\bpackage\b',name,re.I) and re.search(r'\bbed\s+with\s+side\s+tables\b',body,re.I):return 'Bedroom Furniture Sets','reviewed_source_contents','Source package explicitly includes bed and side tables; additional supplied pieces retained.'
 if store in {'ChenOne','Alkaram Studio','Sana Safinaz'}:reviewed_named+=[('Bath Mats', '\\bbath\\s+mat\\b'), ('Mattress Protectors', '\\bmattress\\s+protector\\b'), ('Rugs', '\\brug\\b'), ('Duvet Cover Sets', '\\b(?:\\d+\\s*pcs?\\s+duvet\\s+cover|duvet\\s+cover\\s+set)\\b'), ('Duvet Covers', '\\bduvet\\s+cover(?:\\s+sheet)?\\b'), ('Quilt Covers', '\\bquilt\\s+cover\\b'), ('Cushion Covers', '\\bcushion\\s+covers?\\b'), ('Pillow Covers', '\\bpillow\\s+covers?\\b'), ('Filled Cushions', '\\bfilled\\s+cushion\\b'), ('Cushions', '\\bcushion\\b'), ('Fitted Sheets', '\\bfitted\\s+sheet\\b'), ('Placemats', '\\bplace\\s*mat\\b'), ('Table Runners', '\\btable\\s+runner\\b'), ('Sofa Beds', '\\bsofa\\s+cum\\s+bed\\b'), ('Coffee Table Sets', '\\bcoffee\\s+table\\s+set\\b'), ('Coffee Tables', '\\bcoffee\\s+table\\b'), ('Dressers', '\\bdresser\\b'), ('Trinket Trays', '\\btrinket\\s+tray\\b'), ('Tissue Boxes', '\\btissue\\s+box\\b'), ('Wrapping Papers', '\\bwrapping\\s+(?:paper|sheet)\\b')]
 if store=='Habitt':reviewed_named+=[('Basting Brushes', '\\bsilicone\\s+broom\\b'), ('Snack & Drink Cups', '\\bsnack\\s+tub\\s+with\\s+straw\\b'), ('Snack Storage Boxes', '\\bdry\\s+fruit\\s*&\\s*snack\\s+box\\b'), ('Karahis', '\\bkarahi\\b'), ('Straw & Spoon Sets', '\\bstraw\\s*&\\s*spoon\\s+set\\b'), ('Cutlery & Napkin Holders', '\\bcutlery\\s*&\\s*napkin\\s+holder\\b'), ('Milk Cups', '\\bmilk\\s+cup\\b'), ('Salt Shakers', '\\bsalt\\s+sprayer\\b'), ('Storage Containers', '\\bacrylic\\s+push\\s+box\\s+with\\s+lid\\b'), ('Salt & Pepper Sets', '\\bsalt\\s*&\\s*pepper\\s+set\\b'), ('Milk & Sugar Pot Sets', '\\bmilk\\s+pot\\s*&\\s*sugar\\s+pot\\s+set\\b'), ('Coffee Pots', '\\bcoffee\\s+pot\\b'), ('Oil Pots', '\\boil\\s+pot\\b'), ('Glass Holders', '\\bglass\\s+holder\\b'), ('Strainers & Colanders', '\\bstainer\\b'), ('Storage Racks', '\\bstorage\\s+rack\\b'), ('Oil Bottles', '\\boil\\s+bottle\\b'), ('Dinner Knife Sets', '\\b\\d+\\s*pcs?\\s+dinner\\s+knife\\b'), ('Casseroles', '\\bcasserole\\s*\\d*cm?\\b')]
 if store=='Breakout':reviewed_named+=[('Hoodies', '\\bhooded\\s+top\\b'), ('Tank Tops', '\\btank\\s+top\\b'), ('Tops', '\\btop\\b'), ('Jackets', '\\bjacket\\b'), ('Sweaters', '\\bsweaters?\\b'), ('Gloves', '\\bgloves\\b'), ('Shorts', '\\bshort\\b'), ('Bodysuits', '\\bbody\\s*suit\\b'), ('Glasses', '\\bglasses\\b'), ('High-Neck Tops', '\\bhighneck\\b')]
 if store=='Rios':reviewed_named+=[('Body Shapers', '\\bg[ui]rdle\\b'), ('Hair Colour Developers', '\\bdeveloper\\b'), ('Hair Removal Waxes', '\\bliposoluble\\s+wax\\b'), ('Perfumes & Fragrances', '\\beau\\s+de\\s+(?:toilette|parfum)\\b'), ('Lip Liners', '\\blip\\s*liner\\b'), ('Lip Powders', '\\blip\\s+powder\\b'), ('Eyebrow Kits', '\\beye\\s*brow\\s+designer\\s+kit\\b'), ('Highlighters', '\\billuminator\\b'), ('Makeup Remover Wipes', '\\bmakeup\\s+wet\\s+wipes\\b'), ('Face Powders', '\\bfit\\s*me\\b.*\\bpowder\\b'), ('Cleansing Gels', '\\bcleansing\\s+gel\\b')]
 for label,pattern in reviewed_named:
  if re.search(pattern,name,re.I) and not (store=='ChenOne' and re.search(r'\bpackage\b',name,re.I)):return label,'reviewed_named_sold_object','Explicit source sold object: '+name
 from reviewed_source_types import matched
 source_fact=public_facts(row,store);source_kind=matched(source_fact,store)
 if source_kind and not (store=='ChenOne' and re.search(r'\b(?:package|bed\s+with\s+side\s+tables)\b',name,re.I)):return source_kind[0],'reviewed_public_product_type','Exact identity-matched merchant type: '+source_fact['product_type']+'; '+source_fact['source_url']
 apparel={'Sana Safinaz','Edenrobe','Beechtree','Generation','Saya','Beyond East','Limelight','Mala','Alkaram Studio'}
 if store in apparel:
  from ftfy import fix_text
  clean=fix_text(body)
  if store=='Sana Safinaz':
   if re.search(r'Component Details\s*\(3 Piece\)',clean,re.I) and len(re.findall(r'\d+(?:\.\d+)?\s*meters?\b',clean,re.I))>=2 and re.search(r'\btrouser\b',clean,re.I):return 'Unstitched Suits','reviewed_source_component_cutting','Source explicitly lists measured unstitched front/back/sleeve panels, dupatta and trouser fabric.'
   positive_trouser=re.search(r'(?im)^Trouser(?: Fabric)?[ \t]*:[ \t]*(?![ \t]*(?:Not\b|None\b|N/A\b))(?![^\n]*\bnot\s+included\b)[^\n]+',clean)
   if positive_trouser and re.search(r'(?im)^(?:Shirt Fabric|Shirt Cut|Cut)\s*:',clean):return 'Clothing Sets','reviewed_source_component_fields','Source provides garment-specific upper and trouser specifications; explicit not-included fields excluded.'
   if re.match(r'(?:SS\d+FOR|[BRDP]-)',name,re.I) and re.search(r'\b(?:shirt|kurta)\b.*\bpaired\s+with\b.*\b(?:trousers?|shalwar)\b',clean,re.I|re.S):return 'Clothing Sets','reviewed_source_paired_components','Source formal article description explicitly pairs named upper and lower garments.'
   for label,pattern in [('Tea Cup & Saucer Sets',r'\btea\s+cup\s+and\s+saucer\b'),('Robes',r'\brobe\b'),('Mugs',r'\bmug\b'),('Decorative Books',r'\bdummy\s+book\b'),('Serving Plates',r'\bplate\b'),('Bowls',r'\bbowl\b'),('Candy Jars',r'\bcandy\s+jar\b')]:
    if re.search(pattern,name,re.I):return label,'reviewed_source_object','Source explicitly names the sold object: '+name
  if store=='Limelight':
   primary=clean.lstrip().splitlines()[0].strip().casefold() if clean.strip() else ''
   if primary=='earrings':return 'Earrings','reviewed_primary_source_heading','Primary product description explicitly identifies earrings; chain/tassel are design details.'
   if primary=='necklace':return 'Necklaces','reviewed_primary_source_heading','Primary product description explicitly identifies a necklace.'
   if primary=='rings' and re.search(r'\bearrings\b',clean[:300],re.I):return 'Jewellery Sets','reviewed_source_pack_contents','Source pack lists both rings and earrings; no component-only classification.'
   if re.search(r'\bcatcher\b',name,re.I) and re.search(r'\bclaw\s+clip\b',clean,re.I):return 'Hair Claws','reviewed_source_object','Primary description explicitly identifies a claw clip.'
   for label,pattern in [('Espadrilles',r'\bespadrille\b'),('Flip-Flops',r'\bfilp\s+flops?\b'),('Woven Shoes',r'^Woven Shoes$')]:
    if re.search(pattern,name,re.I):return label,'reviewed_source_object','Explicit source footwear object: '+name
   if re.search(r'\bco[ -]?ord\b',name,re.I) and re.search(r'\b(?:trousers?|shalwar|pants)\b',clean,re.I):return 'Clothing Sets','reviewed_source_contents','Source co-ord names coordinated upper and lower garments.'
   if re.search(r'\bset\b',name,re.I) and re.search(r'\b(?:top|shirt|blazer)\b',clean,re.I) and re.search(r'\b(?:trouser|bottom|shalwar)\b',clean,re.I):return 'Clothing Sets','reviewed_source_contents','Source set supplies labelled upper and lower garments.'
   if re.search(r'\b2\s*Piece\b.*\bKaftan\b',name,re.I):return 'Kaftan Sets','reviewed_source_object','Explicit source two-piece kaftan article; all supplied components retained.'
   for label,pattern in [('Palazzo Trousers',r'\bplazzo\b'),('Pishwas Dresses',r'\bpishwas\b'),('Headbands',r'\bhair\s+band\b'),('Heels',r'\bheels\b'),('Slingback Shoes',r'\bslingback\b'),('Loafers',r'\bloafers\b'),('Boots',r'\bboots\b')]:
    if re.search(pattern,name,re.I):return label,'reviewed_source_object','Source explicitly names the sold object: '+name
   if re.search(r'\b(?:hair\s+catcher|bow\s+catcher)\b',name,re.I) and re.search(r'\bclaw\s+clip\b',clean,re.I):return 'Hair Claws','reviewed_source_object','Source explicitly identifies claw clips, not hair ties.'
  if re.search(r'\bsuit\b',name,re.I) and len(re.findall(r'\d+(?:\.\d+)?\s*M(?:eters?|etres?|tr)?\b',clean,re.I))>=2 and re.search(r'\b(?:front|back|sleeves)\b',clean,re.I) and re.search(r'\b(?:trouser|dupatta)\b',clean,re.I) and not re.search(r'\bFit Type\b',clean,re.I):return 'Unstitched Suits','reviewed_source_cut_panels','Source supplies multiple measured fabric cuts and named suit components.'
  if re.search(r'\bset\b',name,re.I) and re.search(r'\bpaired\s+with\b',clean,re.I) and re.search(r'\b(?:shirt|kurta|kameez)\b',clean,re.I) and re.search(r'\b(?:trousers?|shalwar|culottes|lower|dupatta)\b',clean,re.I):return 'Clothing Sets','reviewed_source_paired_components','Source set explicitly pairs named garments; all included components retained.'
  if store=='Generation':
   for label,pattern in [('Potli Bags',r'\bpotli\b'),('Reading Kits',r'\breading\s+kit\b'),('Sarees',r'\bsaree\b'),('Tops',r'\btop\b'),('Gharara Trousers',r'\bgharara\b'),('Ear Cuffs',r'\bear\s+cuff\b')]:
    if re.search(pattern,name,re.I):return label,'reviewed_source_object','Explicit source sold object: '+name
  if store=='Beyond East' and re.search(r'^1 Piece .*Suit$',name,re.I) and re.search(r'\btunic\b',clean,re.I):return 'Tunics','reviewed_source_description','Source explicitly describes a single tunic, not a multi-piece suit.'
  if re.search(r'\bco[ -]?ords?\s+set\b',name,re.I):return 'Clothing Sets','reviewed_source_object','Source explicitly names a coordinated clothing set.'
  if store in {'Beechtree','Saya'} and re.search(r'\btops?\b',name,re.I):return 'Tops','reviewed_source_object','Source explicitly names the sold top; separate matching bottoms and measurements do not imply inclusion.'
  if re.search(r'\b(?:co[ -]?ords?\s+set|duo[ -]set)\b',name,re.I) and re.search(r'\b(?:shirt|top|kurta|kameez)\b',clean,re.I) and re.search(r'\b(?:trouser|pants?|shalwar|lower)\b',clean,re.I):return 'Clothing Sets','reviewed_source_components','Source explicitly lists coordinated upper and lower garments; all contents retained.'
  if store=='Saya' and re.search(r'\bstitched\b',name,re.I) and re.search(r'\b2\s*Pcs\b.*\bS\+T\b',clean,re.I):return 'Clothing Sets','reviewed_source_components','Source two-piece S+T article configuration; Mom/Kid are variant choices, not extra included outfits.'
  if store=='Sana Safinaz' and all(re.search(r'(?im)^'+x+r'[ \t]*:[ \t]*(?![ \t]*(?:Not\b|None\b|N/A\b))(?![^\n]*\bnot\s+included\b)[^\n]+\bIncluded\b',clean) for x in ('Dupatta','Trouser')):return 'Clothing Sets','reviewed_source_included_garments','Source explicitly marks both dupatta and trouser included; no extra garment or piece count inferred.'
  if re.search(r'\bsuit\b',name,re.I) and re.search(r'\b(?:shirt|frock)\b',clean,re.I) and re.search(r'\b(?:trouser|shalwar|gharara|pants?)\b',clean,re.I):
   if re.search(r'\bun[ -]?stitched\b|\b(?:shirt|trouser|dupatta)[^\n]{0,50}\b\d+(?:\.\d+)?\s*(?:meters?|metres?|mtr)\b',clean,re.I):return 'Unstitched Suits','reviewed_source_fabric_contents','Source supplies named suit components as measured fabric cuts.'
   if re.search(r'\b(?:fit\s+type|ready\s+to\s+wear|stitched|paired\s+with)\b|\b3P\b',clean+' '+name,re.I):return 'Clothing Sets','reviewed_source_components','Source names complete suit components and garment fit; no component-only category.'
  if store=='Beechtree' and re.search(r'\benvelopes?\b',clean,re.I):return 'Gift Envelopes','reviewed_source_object','Source explicitly names an envelope; fabric option 0 is not a garment.'
 if store=='ChenOne' and re.search(r'\bready\s+to\s+stitch\b',name,re.I) and re.search(r'\b\d+(?:\.\d+)?\s*meters?\b',body,re.I):return 'Unstitched Fabric','reviewed_source_measured_fabric','Source explicitly sells a ready-to-stitch measured fabric length.'
 if store=='Mala' and re.search(r'\bniqab\b',name,re.I) and not re.search(r'\b(?:khimar|abaya)\b',name,re.I):return 'Niqabs','reviewed_source_object','Niqab explicitly named as the sold object.'
 if store=='Mala' and re.search(r'\bkhimar\b',name,re.I):return 'Khimar Sets' if re.search(r'\bwith\s+niqab\b',name,re.I) else 'Khimars','reviewed_source_contents','Named khimar with only explicitly included niqab retained.'
 if store=='Mala' and re.search(r'\bkids\b',name,re.I) and re.search(r'\bkids\s+abaya\b',body,re.I):return 'Kids Abayas','reviewed_source_object','Source explicitly names a hoodie-style kids abaya.'
 if store=='Alkaram Studio':
  if re.search(r'\bbedsheet(?:\s+set)?\b',name,re.I) and re.search(r'\b\d+\s*x\s*pillow\s+cases?\b',body,re.I):return 'Bed Sheet Sets','reviewed_source_contents','Source explicitly lists sheet and pillow case quantities and measurements.'
 if store=='Tawakkal Fabrics':
  if re.search(r'\bslipper\b',name,re.I):return 'Slippers','reviewed_source_object','Explicit slipper title and footwear specifications: '+body[:250]
  if re.search(r'\bheel\b',name,re.I) and re.search(r'\bheel\s+sandals\b',body,re.I):return 'Heeled Sandals','reviewed_source_object','Source explicitly describes high heel sandals: '+body[:250]
  if name=='Born For Victory' and all(re.search(p,body,re.I) for p in [r'Fragrance Notes',r'Top Notes',r'Base Notes']):return 'Perfumes & Fragrances','reviewed_source_notes','Explicit source fragrance type and top/middle/base notes retained.'
 if store=='Mala':
  if re.search(r'\babaya\b.*\b4\s*pieces?\b',name,re.I) and all(re.search(r'\b'+x+r'\b',body,re.I) for x in ['gown','inner','hijab','niqab']):return 'Abaya Sets','reviewed_source_contents','Four source-listed components: gown, inner, hijab and niqab.'
  if re.search(r'\bjilbab\b',name,re.I):return 'Jilbabs','reviewed_source_object','Source names a full-length jilbab.'
  if re.search(r'\bchaddar\b',name,re.I):return 'Prayer Chaddars','reviewed_source_object','Source names chaddar with full coverage and prayer use.'
  if name=='HerBag' and re.search(r'\bEveryday Handbag\b',body,re.I):return 'Handbags','reviewed_source_object','Source explicitly identifies the everyday handbag.'
 if store=='Generation' and re.search(r'\b(?:ensemble|duo\s+set|co.ord\s+set)\b',name,re.I) and re.search(r'\bpaired\s+with\b',body,re.I):return 'Clothing Sets','reviewed_source_contents','Source describes coordinated garments paired together; complete contents retained.'
 if store=='Breakout' and re.search(r'\b(?:fit|leg)\s+denim\b',name,re.I) and re.search(r'\bsize\s*:',body,re.I):return 'Jeans','reviewed_source_object','Source names fitted denim trousers with waist sizes.'
 if store=='Beyond East' and re.search(r'\bco-ords?\s+set\b',name,re.I):return 'Clothing Sets','reviewed_source_object','Source explicitly names coordinated outfit set.'
 # Sold-object names take precedence over incidental compatibility/care terms.
 if store=='Habitt':
  # Kitchen-only source scope is enforced before export; use explicit sold objects.
  kitchen=[('Manual Food Choppers', '\\b(?:manual.*chopper|food\\s+chopper)\\b'), ('Oil Spray Bottles', '\\boil\\s+spray\\s+bottle\\b'), ('Cooking Spatulas', '\\b(?:spatula|slotted\\s+turner)\\b'), ('Fruit Scoops', '\\b(?:fruit\\s+baller|melon.*scoop)\\b'), ('Oil Bottles', '\\bglass\\s+oil\\s+bottle\\b'), ('Vegetable Peelers', '\\bpeeler\\b'), ('Ice Cube Trays & Moulds', '\\bice\\s+(?:cube.*(?:tray|mold|mould)|mold\\s+tray)\\b'), ('Fish Scale Scrapers', '\\bfish\\s+scale\\s+scraper\\b'), ('Disposable Baking Tray Sets', '\\bfoil\\s+tray\\s+set\\b'), ('Dessert Container Sets', '\\b\\d+\\s*pcs\\s+mini\\s+dessert\\s+display\\s+box\\b'), ('Egg Storage Boxes', '\\begg\\s+storage\\s+box\\b'), ('Potato Presses', '\\bpotato\\s+press\\b'), ('Serving Tongs', '\\b(?:serving|salad|silver|pasta)\\s+tongs?\\b'), ('Beverage Dispensers', '\\bwater\\s+dispenser\\b'), ('Air Fryer Liners', '\\bair\\s+fryer\\s+paper\\s+liners\\b'), ('Rechargeable Lighters', '\\brechargeable\\s+lighter\\b'), ('Bottle Cleaning Brushes', '\\bbottle\\s+brush\\b'), ('Portable Blenders', '\\bportable\\s+juicer\\b'), ('Water & Juice Jugs', '\\bflow\\s+jug\\b'), ('Self-Mixing Mugs', '\\bself\\s+mixing.*mug\\b'), ('Vegetable Cutters', '\\b(?:vegetable\\s+cutter|potato\\s+cutter)\\b'), ('Thermal Food Covers', '\\bthermal\\s+food\\s+cover\\b'), ('Chopstick Sets', '\\bchopsticks\\s+set\\b'), ('Ice Buckets', '\\bice\\s+bucket\\b'), ('Serving Karahis', '\\bserving\\s+karahi\\b'), ('Strainers & Colanders', '\\b(?:strainer|drain\\s+basket|fryer\\s+basket)\\b'), ('Manual Ice Crushers', '\\b(?:ice\\s+crusher|ice\\s+shaver)\\b'), ('Condiment Shakers', '\\bsalt\\s*&\\s*pepper\\s+shaker\\b'), ('Serving Bowls', '\\bserving\\s+bowl\\b'), ('Storage Jar Sets', '\\bset\\s+of\\s+\\d+\\s+storage\\s+jars\\b'), ('Reusable Ice Cubes', '\\b(?:stainless\\s+steel\\s+ice\\s+cubes|metal\\s+ice\\s+cubes\\s+set)\\b'), ('Serving Spoons', '\\bpasta\\s+serving\\s+spoon\\b'), ('Refrigerator Organizers', '\\bfridge\\s+basket\\b'), ('Kitchen Canister Sets', '\\b(?:canister\\s+set|metal\\s+storage\\s+box\\s+set)\\b'), ('Baby Feeding Spoons', '\\bbaby\\s+feeding\\s+spoon\\b'), ('Whisks', '\\b(?:egg\\s+beater|whisk)\\b'), ('Cutting Boards', '\\bcutting\\s+board\\b'), ('Milk Frothers', '\\b(?:coffee|milk)\\s+frother\\b'), ('Garlic Graters', '\\bgarlic\\s+grater\\b'), ('Sugar Jars', '\\bsugar\\s+jar\\b'), ('Lunch Boxes', '\\blunch\\s+box\\b'), ('Can Openers', '\\bcan\\s+opener\\b'), ('Cookware Sets', '\\bcookware\\s+set\\b'), ('Frying Pans', '\\b(?:fry\\s*pan|paella\\s+pan)\\b'), ('Casseroles', '\\bcasserole\\b'), ('Cheese Boards', '\\bcheese\\s+board\\b'), ('Ice Lolly Mould Sets', '\\bkulfi\\s+mould\\s+set\\b')]
  for label,pattern in kitchen:
   if re.search(pattern,name,re.I):return label,'reviewed_kitchen_object','Explicit source kitchen object: '+name
 if store=='Computer Zone':
  if re.search(r'\bUSB-C\s+(?:Travel\s+)?Dock\b',name,re.I) and re.search(r'\bDP\s+Alt.Mode\b',body,re.I):return 'USB Docking Stations','reviewed_source_object','Source names USB-C dock and DP Alt-Mode; laptop is the compatibility target.'
  if re.search(r'\bChassis\b',name,re.I) and re.search(r'\b(?:M-ATX|ITX|motherboard)\b',body,re.I):return 'Computer Cases','reviewed_source_object','Source names computer chassis with motherboard support; radiator is a supported component.'
 if store in STORES:
  explicit=[('Shrugs',r'\bshrug\b'),('Hoodies',r'\bzipper\s+hood\b'),('Jumpers',r'\bjumper\b'),('Shorts',r'\bknit\s+short\b'),('Niqabs',r'^niqab\b'),('Hijab Pins',r'\bhijab\s+pins\b'),('Hair Accessories',r'\bparanda\b')]
  for label,pattern in explicit:
   if re.search(pattern,name,re.I):return label,'reviewed_source_object','Explicit sold object in source title: '+name
  if re.search(r'\bbed\s*sheet\b',name,re.I) and re.search(r'\b(?:package\s+includes|set\s+includes)\b',body,re.I) and re.search(r'\bpillow\s*(?:covers?|cases?)\b',body,re.I):return 'Bed Sheet Sets','reviewed_source_contents','Source explicitly includes bed sheet and pillow covers; package contents retained.'
 if store=='Xcessories Hub':
  from xcessories_purpose_support import classify
  found=classify(row)
  if found:return found
 if store=='Design by DAS':
  if re.search(r'(?i)\bcrochet\b.*\b(?:tulip|rose)\b',name) and re.search(r'(?i)\byarn\b',body):return 'Crochet Flowers','reviewed_source_material_and_name','Named crochet flower, source explicitly states yarn; not a live plant.'
  if name=='Fruit-Themed Glasses Cover' and re.search(r'(?i)\beyewear\b',body):return 'Eyeglass Cases','reviewed_source_purpose','Source explicitly describes crochet cases for sunglasses and reading glasses.'
 if store=='Sapphire' and re.search(r'\bzip.up\s+jumper\b',name,re.I) and re.search(r'\bjumper\b',body,re.I):return 'Jumpers','reviewed_source_garment','Explicit source jumper; fibre composition and zipper details retained.'
 if store=='Prime Ticks' and re.search(r'\b(?:watch|dial|movement|quartz)\b',name+' '+body,re.I):return 'Wrist Watches','reviewed_source_specifications','Named watch or watch movement/dial specifications; no gender inferred from navigation.'
 if store=='Hilm Chapals' and re.search(r'\b(?:chapals?|chapal|chappals?|norozi)\b',name+' '+body,re.I):return 'Chappals','reviewed_source_footwear','Source explicitly names regional chapal footwear; no material added.'
 if store=='Zyren':
  if re.search(r'(?i)\bsling.?backs?\b',body):return 'Slingback Shoes','reviewed_source_upper_design','Source explicitly describes slingback footwear; original colour and fit details retained.'
  evidence=re.split(r'(?i)\bFit\s*:',body[:1000],maxsplit=1)[0]
  for pattern,label in [(r'\bmules?\b','Mules'),(r'\bmary\s+jane\b','Mary Jane Shoes'),(r'\bslides?\b','Slides'),(r'\bloafers?\b','Loafers'),(r'\bsandals?\b','Sandals'),(r'\bsneakers?\b','Sneakers'),(r'\bpumps?\b','Pumps'),(r'\bballet\b','Ballet Flats'),(r'\bheels?\b','Heels')]:
   if re.search(pattern,evidence,re.I):return label,'reviewed_source_upper_design','Product-specific source upper/fit description: '+evidence[:600]
  if re.search(r'(?i)\bupper\b',body) and re.search(r'(?i)\b(?:sole|footbed|shoe|footwear)\b',body):return 'Shoes','reviewed_source_footwear','Source upper and sole/footbed specifications identify footwear; narrower silhouette not assumed.'
 if store=='Golden Rose':
  for pattern,label in [(r'\blip\s+marker\b','Lip Tints'),(r'\bbrush\s+cleanser\b','Makeup Brush Cleansers'),(r'\b(?:powder|bronzer)\b.*\bbrush\b','Powder Brushes'),(r'\b(?:highlighter|concealer|contour)\b.*\bbrush\b','Face Makeup Brushes'),(r'\bfacial\s+cleansing\s+brush\b','Facial Cleansing Brushes'),(r'\beyelash\s+adhesive\b','Eyelash Adhesives'),(r'\beyelashes\b','False Eyelashes'),(r'\bmakeup\s+bag\b','Makeup Bags'),(r'\bnail\s+lacquer\b','Nail Polishes'),(r'\bbrowliner\b','Eyebrow Liners'),(r'\b(?:blender|sponge)\b','Makeup Sponges'),(r'\bterracotta\s+powder\b','Face Powders'),(r'\bpowder\s+puff\b','Makeup Puffs'),(r'\bbrow\s+styling\s+gel\b','Eyebrow Gels'),(r'\bhighlighter.*eyeshadow\b','Liquid Eyeshadows'),(r'\bmicellar\s+cleansing\s+water\b','Micellar Cleansing Waters'),(r'\bpurifying\s+tonic\b','Facial Toners'),(r'\bmake.up\s+remover\b','Makeup Removers')]:
   if re.search(pattern,name,re.I):return label,'reviewed_source_product_name','Explicit sold cosmetic/tool named by source: '+name
 if store=='Pyari Walls':
  for pattern,label in [(r'(?i)\bgreeting\s+sign\b','Decorative Signs'),(r'(?i)\bphoto\s+frames\b|FAMILY FRAMES','Picture Frame Sets'),(r'(?i)\bneon\s+light\b','Neon Signs'),(r'(?i)\bbutterflies.*bundle','Wall Art Sets'),(r'(?i)\bwalls\s+decor\b','Wall Art')]:
   if re.search(pattern,name):return label,'reviewed_source_product_name','Explicit source-named decorative object: '+name
  if name=='Possible Impossible Inspiring Office Decor (ip01)':return 'Decorative Signs','reviewed_product_name','Explicit inspiring office decoration title; physical details not invented.'
  if re.search(r'(?i)\b(?:Premium Acrylic (?:MashAllah|Kalma|Fabi Ayyi|Bismiallah)|Kalima-e-Tauheed|Asma.ul.Husna Frame|Tasbeeh E Fatima|Darood o Salam|Ramadan Mubarak|Bismillah Elegance|World Map 3D|Motivational|Think Big Bulb|Work Smart Not Hard|Possible Impossible Inspiring Office)\b',name) and re.search(r'(?i)\b(?:acrylic|wood|MDF|frame|wall|lasani)\b',name+' '+body):return 'Wall Art Sets' if re.search(r'(?i)\bset of|frames',body[:100]) else 'Wall Art','reviewed_source_material_and_name','Named decorative artwork plus source wall/frame/wood/acrylic details; all useful facts retained.'
  for label,pattern in [('Serving Tray Sets', '\\bset\\s+of\\s+\\d+.*\\btrays\\b'), ('Serving Trays', '\\btray\\b'), ('Night Lights', '\\bnight\\s+lamp\\b'), ('Table Lamps', '\\b(?:table|bedside)\\s+lamp\\b'), ('Floor Lamps', '\\bstanding\\s+corner.*\\blamp\\b'), ('Decorative Sculptures', '\\bsculpture\\b'), ('Decorative Ashtrays', '\\bash\\s+tray\\b'), ('Planner Boards', '\\bplanner\\s+board\\b'), ('Planter Sets', '\\bplanters\\b'), ('Decorative Planters', '\\bplanter\\b'), ('Switch Stickers', '\\bswitch\\s+stickers\\b'), ('Picture Frames', '\\b(?:picture|fridge)\\s+frames?\\b'), ('Mirrors', '\\bmirror\\b'), ('Phone Holders', '\\bmobile\\s+phone.*\\bholder\\b'), ('Coaster Sets', '\\bcoaster\\b'), ('LED Strip Lights', '\\bled\\s+(?:neon\\s+light|strip)\\b'), ('Decorative Shelf Sets', '\\bshelves\\b'), ('Decorative Border Strips', '\\bborder\\s+strips\\b'), ('Money Gift Envelopes', '\\b(?:eidi|wedding\\s+gift).*\\benvelopes?\\b'), ('Date Serving Holder Sets', '\\bkh?j?ha?joor.*\\bholder\\s+set\\b'), ('LED Candles', '\\bled\\s+candles\\b'), ('Wall Mounting Clips', '\\bwall\\s+clips\\b'), ('Display Stands', '^Transparent Acrylic Stand$'), ('Adhesive Tape', '\\bdouble\\s+sided\\s+tape\\b'), ('Clock Nuts', '^clock Nut$'), ('Acrylic Sheets', '\\bacrylic\\s+sheet\\b'), ('Prayer Stands', '\\bprayer\\s+stand\\b'), ('Decorative Plant Sets', '\\bset\\s+of\\s+\\d+.*\\bplants\\b'), ('Neon Signs', '\\bneons?\\s+signs?\\b|\\bled\\s+sign\\b'), ('Decorative Wall Signs', '\\bwall\\s+sign|\\bwall\\s+decorations?\\b|\\broom\\s+sign\\b'), ('Tabletop Art', '\\btabletop\\s+art\\b'), ('Dining Decorations', '\\bdining\\s+decor\\b'), ('Decorative Name Sets', '\\bset\\s+of.*\\bdecor\\s+names\\b|\\bAllah.*Names\\b'), ('Wall Art Sets', '\\bset\\s+of\\s+\\d+.*\\bwall\\s+sceneries\\b|\\bframes.*decor\\b'), ('Wall Art', '\\bwall.*\\bart\\s+decor\\b|\\bwall\\s+scener|\\bwall\\s+decor\\b|\\bcalligraphies\\b'), ('Ramadan Decor Bundles', '\\bramadan\\s+bundle\\b')]:
   if re.search(pattern,name,re.I):return label,'reviewed_source_product_name','Explicit source object name: '+name
  if re.search(r'(?i)\b(?:wall art|calligraphy|wall hanging|wall decor)\b',body[:600]):return 'Wall Art Sets' if re.search(r'(?i)\bset\b|\bframes\b',name) else 'Wall Art','reviewed_source_description','Source explicitly describes wall artwork; original dimensions and materials retained.'
  if re.search(r'(?i)\bDIY kit\b',body[:300]):return 'Decorative DIY Kits','reviewed_source_description','Source explicitly names a decorative DIY kit.'
  if name=='Quartz' and 'Continuous machine' in body:return 'Clock Movements','reviewed_source_description','Source continuous movement and clock-hand size choices retained.'
  for pattern,label in [(r'\bnesting\b.*\btables?\b','Nesting Table Sets'),(r'\bside\s+tables\b','Side Table Sets'),(r'\btable\s+lamp\b','Table Lamps'),(r'\bserving\s+trolley\b','Serving Trolleys'),(r'\bwall\s+clock\s+set\b|\bclock\s+set\b','Wall Clock Sets'),(r'\bwall\s+clocks?\b|\bclocks?\b','Wall Clocks'),(r'\bkey\s*(?:chain|holder)|\bkey\s+chain\s+holder\b','Key Holders & Racks'),(r'\bwall\s+mirrors?\b','Wall Mirrors'),(r'\b(?:calligraphy|wall\s+art|wall\s+decor|wall\s+hanging)\b','Wall Art'),(r'\bmagic\s+practice\s+book\b','Practice Book Sets'),(r'\b(?:drawing|coloring)\s+book\b','Colouring Book Sets'),(r'\bpuzzles\b.*\bset|\bset\s+of\b.*\bpuzzles\b','Puzzle Sets'),(r'\bpuzzle\b','Educational Puzzles'),(r'\blearn\s+to\s+tie\s+shoe','Lacing Learning Boards'),(r'\bmontessori.*board\b','Montessori Learning Boards'),(r'\blearning\s+bundle\b','Learning Toy Sets')]:
   if re.search(pattern,name,re.I):
    if label=='Wall Art' and re.search(r'\bset\b|\b[2345]\s*piece',name,re.I):label='Wall Art Sets'
    return label,'reviewed_source_product_name','Explicit sold object and set contents retained: '+name
 if store=='Rivaj UK' and re.fullmatch(r'Facial Capsules',name,re.I) and re.search(r'\bserum\b.*\bface\b',body,re.I):return 'Face Serums','reviewed_source_purpose','Primary source explicitly describes a serum for face and neck; capsules are not oral supplements.'
 if store=='Stylo' and re.search(r'\bcanvas\s+slip[ -]?ons?\b',name,re.I) and re.search(r'\bmule[ -]style\s+sneaker\b',body,re.I):return 'Sneaker Mules','reviewed_source_purpose','Primary source explicitly describes a mule-style sneaker with slip-on closure; all materials and care retained.'
 if store=='Outfitters':
  if re.fullmatch(r'Pack Of 2 Hair Bands',name,re.I):return 'Headbands','reviewed_product_name','Source explicitly names a two-pack of hair bands.'
  if re.fullmatch(r'Pack Of 3 Floral Clips',name,re.I):return 'Hair Clips & Pins','reviewed_source_photo','Identity-matched source photo shows three floral hair clips; source care retained.'
 if store=='Zellbury' and re.search(r'^Co-Ord Set Pant\s*[-–]',name,re.I):return 'Trousers','reviewed_product_name','Pant is the sold component; co-ord set is the style name, not included contents.'
 if store=='Hello Maali':
  fact=public_facts(row,store);kind=maali_kind(row,fact)
  if kind:return kind,'reviewed_product_plant_identity','Identity-matched source plant type/care panels: '+str(row.get('source_url'))
 if store=='Junaid Jamshed':
  fact=public_facts(row,store)
  if fact and str(fact.get('product_type') or '').casefold()=='shalwar':return 'Shalwars','reviewed_public_product_type','Exact matching primary source product type: Shalwar; '+str(fact['source_url'])
 if store=='Gul Ahmed':
  if re.search(r'\bjeans\b',name,re.I):return 'Jeans','reviewed_product_name','Named sold garment: '+name
  if re.search(r'\btank\s+tops?\b',name,re.I):return 'Tank Tops','reviewed_product_name','Named sold garment, not styling companion trousers: '+name
  if re.search(r'\bmattress\s+topper\b',name,re.I):return 'Mattress Toppers','reviewed_product_name',name
  if re.search(r'\bbed\s*spread\b',name,re.I) and re.search(r'\b(?:pillow\s+cases|cushion\s+(?:cases|covers))\b',body,re.I):return 'Bedspread Sets','reviewed_source_contents','Source names bedspread and companion pillow/cushion cases: '+body[:850]
  if re.search(r'\bterry\s+turban\b',name,re.I) and re.search(r'\bwrap\s+the\s+hair\b',body,re.I):return 'Hair Towels','reviewed_source_purpose','Source terry turban wraps hair after washing: '+body[:400]
  if re.search(r'\bquilted\s+mat\b',name,re.I) and re.search(r'\b(?:padded|cushion|exercise|play\s+mat)\b',body,re.I):return 'Quilted Multipurpose Mats','reviewed_source_purpose',name+'; '+body[:600]
  if re.search(r'\bembellished\s+inner\b',name,re.I) and re.search(r'\blayers?\s+well\s+under\s+abayas\b',body,re.I):return 'Abaya Inners','reviewed_source_purpose','Source identifies a layering inner worn under abayas: '+body[:550]
 if store=='Astore Bags':
  if re.search(r'\bmini\s+pouch(?:es)?\b',name,re.I):return 'Mini Pouches','reviewed_product_name',name
  if re.search(r'\bwallets?\b',name,re.I):return 'Wallets','reviewed_product_name',name
  if re.search(r'\b(?:bags?|handbags?|totes?|backpacks?|clutches|purses?)\b',name,re.I):return ('Bag Sets' if re.search(r'\bset\s+of\s+\d+',name,re.I) else 'Bags'),'reviewed_product_name',name
 if store in {'Servis','Ndure'}:
  for pattern,label in [(r'\bslides?\b','Slides'),(r'\boxford\s+shoes\b','Oxford Shoes'),(r'\bheels?\b','Heels'),(r'\bkola\s*puri\b|\bkolhapuri\b','Kolhapuri Sandals'),(r'\bpeshawari\b','Peshawari Chappals'),(r'\bmocs\b','Moccasins'),(r'\bpeep[ -]?toes\b','Peep-Toe Shoes'),(r'\bbags\b','Bags'),(r'\bshoe\s+brush\b','Shoe Brushes'),(r'\b(?:shoe\s+wax|shoe\s+shiner|shoe\s+freshner|shoecare|sole\s+cleaner|foam\s+shiner|self\s+shiner|nubuck\s+renovator)\b','Shoe Care Products'),(r'\bshoes\b','Shoes')]:
   if re.search(pattern,name,re.I):return label,'reviewed_product_name','Named sold object: '+name
  for pattern,label in [(r'\bshoe\s+care\s+kit\b','Shoe Care Kits'),(r'\bshoe\s+care\b','Shoe Care Products'),(r'\binsoles?\b','Shoe Insoles'),(r'\b(?:liquid|wax|bee)\b.*\bpolish\b','Shoe Polishes'),(r'\bformals?\b','Formal Shoes'),(r'\bcanvas\b','Canvas Shoes'),(r'\bballerinas?\b','Ballet Flats'),(r'\bwedges?\b','Wedge Shoes'),(r'\b(?:closed?|easy[ -]?fit|contrast\s+sole|laser[ -]?cut|buckle)\s+shoes\b','Shoes'),(r'\bsports?\s+shoes\b','Sports Shoes'),(r'\b(?:runners?)\b','Running Shoes'),(r'\bsliders?\b','Slides'),(r'\bpumps?\b','Pumps'),(r'\b(?:infant)\s+shoes\b','Baby Shoes')]:
   if re.search(pattern,name,re.I):return label,'reviewed_product_name','Explicit named footwear object or care product: '+name
  for pattern,label in [(r'\bsneakers?\b','Sneakers & Trainers'),(r'\b(?:slip[ -]?ons?)\b','Slip-On Shoes'),(r'\bcasual\s+shoes\b','Casual Shoes'),(r'\bformal\s+shoes\b','Formal Shoes'),(r'\b(?:mules?)\b','Mules'),(r'\b(?:moccs|moccasins?)\b','Moccasins'),(r'\b(?:loafers?)\b','Loafers'),(r'\bsling[ -]?backs?\b','Slingback Shoes'),(r'\bschool\s+shoes\b','School Shoes'),(r'\bslides?\b','Slides'),(r'\bflip[ -]?flops?\b','Flip-Flops')]:
   if re.search(pattern,name,re.I):return label,'reviewed_product_name','Explicit sold footwear type: '+name
 if store=='Zero Lifestyle' and row.get('name')=='Open Zbuds' and re.search(r'(?i)ear.?clip.*Bluetooth|Bluetooth.*ear.?clip',str(row.get('description') or ''),re.S):return 'Earphones/Earbuds','reviewed_source_description','Source explicitly describes open-ear wireless earbuds with Bluetooth and charging case.'
 name=str(row.get('name') or '');body=str(row.get('description') or '')
 if store=='Junaid Jamshed' and re.search(r'\bbrow\b.*\bshaping\s+gel\b',name,re.I) and re.search(r'\b(?:brow|eyebrow)\s+shape\b',body,re.I):return 'Eyebrow Gels','reviewed_source_description','Source explicitly identifies brow tinting and shaping gel: '+body[:700]
 if store=='Gul Ahmed' and re.search(r'\bapron\b',name,re.I) and re.search(r'\bcooking\b',body,re.I):return 'Kitchen Aprons','reviewed_source_description','Source identifies a cooking apron; finish and full measurements retained: '+body[:700]
 visual=visual_review(row,store)
 if visual:return visual['category'],'reviewed_primary_product_image',visual['overview']+' Image: '+visual['image_url']+' SHA256: '+visual['image_sha256']
 if store=='Sapphire' and re.fullmatch(r'(?i)Knit Cape Jumper',str(row.get('name') or '').strip()) and re.search(r'(?i)\bknit\s+cape\s+jumper\b',str(row.get('description') or '')):return 'Ponchos & Capes','reviewed_source_description','Source explicitly names a knit cape jumper; fabric percentages and measurements unchanged.'
 if store not in STORES and store not in {'Aerosoft Studio','Bata','Servis','Ndure','Zero Lifestyle','Astore Bags'}:return None
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
  if store=='Bata' and source.get('reviewed_tag_category') and source.get('reviewed_type_tag'):
   return source['reviewed_tag_category'],'reviewed_public_product_tag','Exact public merchant product tag: '+source['reviewed_type_tag']+'; '+source['source_url']
  if store=='Aerosoft Studio':
   footwear={'slippers':'Slippers','slipper':'Slippers','sandals':'Sandals','running sneakers':'Sneakers & Trainers','walking sneakers':'Sneakers & Trainers','shoes':'Shoes'}
   label=footwear.get(str(source.get('product_type') or '').strip().casefold())
   if label:return label,'reviewed_public_product_type','Exact public product type: '+source['product_type']+'; '+source['source_url']
  if store=='Hush Puppies':
   label={'casual':'Casual Shoes','semi formals':'Semi-Formal Shoes','formals':'Formal Shoes','slipper':'Slippers','slippers':'Slippers','sandals':'Sandals','sandal':'Sandals','school shoes':'School Shoes','slides':'Slides','pumps':'Heels & Pumps','sneakers':'Sneakers & Trainers','sneaker':'Sneakers & Trainers','belt':'Belts','insole':'Insoles','mule shoes':'Mules'}.get(str(source.get('product_type') or '').strip().casefold())
   if label:return label,'reviewed_public_product_type','Exact identity-matched merchant product type: '+source['product_type']+'; '+source['source_url']
  bundle=source.get('reviewed_bundle',{})
  if store=='Bonanza Satrangi' and bundle.get('status')=='active' and bundle.get('category') in ('Fragrance Bundles','Makeup Bundles') and bundle.get('configuration_sha256') and bundle.get('products'):return bundle['category'],'reviewed_public_bundle_configuration',source['description']+'; '+bundle['configuration_source_url']
  types={'earring':'Earrings','earrings':'Earrings','earstuds':'Stud Earrings','jhumka':'Jhumka Earrings','karay':'Bangles & Karas','bangles':'Bangles & Karas','necklace':'Necklaces','necklaces':'Necklaces','bracelets':'Bracelets','anklet':'Anklets','anklets':'Anklets','ring':'Rings','rings':'Rings','pendent':'Pendants & Lockets','nath':'Nose Jewellery','bindiya kanta':'Forehead Jewellery','choker set':'Jewellery Sets','mala set':'Jewellery Sets','locket set':'Jewellery Sets','bridal set':'Jewellery Sets','jeans':'Jeans'}
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
 if store=='Sana Safinaz':
  fact=public_facts(row,store)
  if fact and fact.get('reviewed_type_tag') in fact.get('published_tags',[]) and fact.get('reviewed_tag_category') in {'Bridal Outfits','Couture Outfits','Wrapping Papers','Ashtrays','Serving Platters','Sarees','Kaftans','Cushions & Covers'}:return fact['reviewed_tag_category'],'reviewed_exact_public_taxonomy','Exact identity-matched public merchant tag: '+fact['reviewed_type_tag']+'; '+fact['source_url']
 return None

def description(row,store):
 from catalogue_object_rules import overview
 recovered,why=overview(row,store)
 if why and visual_review(row,store) is None:return recovered,why
 original=str(row.get('description') or '');name=str(row.get('name') or '');body=original.strip()
 if explicit_source_service(row,store) and body.casefold()==name.casefold():
  text='A test listing for a stitching service.' if re.match(r'TEST[- ]',name,re.I) else 'A listing for a stitching service.'
  return text,'Expressed only the exact source-named service and retained its test qualification; no garment, fabric, duration or fulfilment facts inferred.'
 if store=='Rawayat' and re.search(r'\bear[ -]cuff\b',name,re.I) and body.rstrip('.')==name.rstrip('.'):
  return name+' is an ear-cuff jewellery design.','Expressed the exact source-named ear cuff; no pair count, material or stone authenticity inferred.'
 if store in {'Zellbury','Gul Ahmed','Xcessories Hub'}:
  named_types=[(r'\bbath\s+sheet\b','a bath sheet'),(r'\bbath\s+towel\b','a bath towel'),(r'\bshoulder\s+bag\b','a shoulder bag'),(r'\bsecurity\b.*\bcamera\b','a home security camera'),(r'\busb\s+bluetooth\s+adapter\b','a USB Bluetooth adapter'),(r'\bglass\s+protector\b','a glass screen protector')]
  for pattern,kind in named_types:
   sparse=re.sub(r'(?im)^.*(?:Exclusively at|Weight: N/A|Dimensions: N/A).*$', '',body).strip()
   if re.search(pattern,name,re.I) and (sparse.split('Product Options:')[0].strip().rstrip('.') in {'',name.rstrip('.')} or store=='Zellbury' and re.fullmatch(r'(?:LUXURY|SIGNATURE)\s*-\s*\d+x\d+cm\s*-\s*Bath (?:Sheet|Towel)',body,re.I)):
    lead=name+' is '+kind+'.'
    return lead+('\n\n'+original if body else ''),'Expressed exact named sold object; retained original product identity and every supplied option/specification.'
 visual=visual_review(row,store)
 if visual and not body.startswith(visual['overview']):
  useful=original if body not in ('',name,'Rawayat','dsasd') else ''
  if visual.get('replace_wrong_product_body'):useful=''
  if visual.get('correct_leading_copy'):
   old,new=visual['correct_leading_copy']
   if useful.startswith(old):useful=new+useful[len(old):]
  return visual['overview']+('\n\n'+useful if useful else '\n\nListing: '+name),'Added reviewed primary-image object types and contents; source composition not guessed and all supplied facts retained.'
 if store=='Rios' and (body.split('\n\nProduct Options:')[0].strip() in ('',name) or len(re.findall(r'\w+',body))<5):
  chosen=category(row,store)
  kinds={'Hair Brushes':'a hairbrush','Makeup Brushes':'a makeup brush','Shaving Foams':'a shaving foam','Panty Liners':'a pack of panty liners','Face Scrubs & Exfoliators':'a facial scrub','Hair Removal Waxes':'a hair-removal wax','Skin Soothing Gels':'a skin-soothing gel','Lip Balms & Treatments':'a lip balm','Makeup Puffs':'a makeup puff','Travel Bottle Sets':'a travel bottle set','Toothbrushes':'a toothbrush','Dental Floss':'dental floss','Makeup Setting Sprays':'a makeup-setting spray'}
  if chosen and chosen[0] in kinds:
   lead=name+' is '+kinds[chosen[0]]+'.';tail=original[len(name):] if body.startswith(name) else '\n\n'+original
   return lead+tail,'Rewrote explicit named object only; original pack quantities and options retained.'
 from reviewed_source_types import matched
 fact=public_facts(row,store);kind=matched(fact,store)
 if kind:
  chosen=category(row,store)
  lead=name+' is '+kind[1]+'.'
  if chosen and chosen[0]==kind[0] and not body.startswith(lead):return lead+'\n\n'+original,'Added exact identity-matched public merchant object type; all original details retained.'
 if store=='Sana Safinaz' and fact and fact.get('reviewed_tag_overview'):
  chosen=category(row,store);lead=fact['reviewed_tag_overview']
  if chosen and chosen[0]==fact.get('reviewed_tag_category') and not body.startswith(lead):return lead+'\n\n'+original,'Added exact published product-family evidence; no unstated contents, fabric or piece count inferred.'
 if store=='Mala' and re.fullmatch(r'circle hijab pins',name,re.I) and body.casefold()==name.casefold():return 'Circular pins for securing a hijab.','Rewrote explicitly named circular hijab pins; no quantity, material or size invented.'
 if store=='Design by DAS' and name=='Fruit-Themed Glasses Cover' and body.lstrip('\ufeff ').startswith('.product-card-container {'):
  marker='Handmade Crochet Fruit-Themed Glasses Cover'
  if marker in body:return body[body.index(marker):],'Removed only accidental source CSS prefix; all product text, dimensions, options and care retained.'
 if store=='Pyari Walls' and (len(re.findall(r'\w+',body))<5 or body==name):
  if name=='clock Nut':return 'A clock nut supplied as a clock component.','Rewrote explicitly named clock part; size and material not assumed.'
  if re.search(r'(?i)\b(?:lamp|wall|clock|office decor|room sign)\b',name):return name+' is a decorative item for the named setting.'+('\n\n'+original if body and body!=name else ''),'Rewrote source-named decorative object only; no new material, contents or performance claims.'
 if store=='Prime Ticks' and re.search(r'(?i)\bwatch\b',name) and (len(re.findall(r'\w+',body))<5 or body==name):return name+' is a wrist watch.'+('\n\n'+original if body else ''),'Rewrote source-named watch identity; no specifications invented.'

 if store=='Hello Maali':
  fact=public_facts(row,store);kind=maali_kind(row,fact)
  if kind:
   lead=name+(' is a set of live plants.' if kind=='Live Plant Sets' else ' is a live plant.')
   care=str((fact or {}).get('plant_care_description') or '')
   result=original if body.startswith(lead) else lead+'\n\n'+original
   if care and care not in result:result+='\n\n'+care
   return result,'Retained all saved details and added identity-verified source plant care; no care or pet-safety claims inferred.'
 if store=='Elite Cosmetics' and body==name and re.search(r'(?i)\broll.on\s+deodorant',name):return name+' is a roll-on deodorant.','Rewrote exact named deodorant identity; scent, audience, duration label and volume retained.'
 if store=='Rawayat' and name=='Gift Box' and body=='Add Gift Box & Bag':return 'Gift packaging comprising a gift box and bag.','Rewrote both explicitly offered packaging items; no size or material invented.'
 if store not in STORES and store not in {'Aerosoft Studio','Bata','Servis','Ndure','Zero Lifestyle','Astore Bags'}:return original,None
 if (str(row.get('website_category_status') or '') in ('verified_navigation_membership','verified_product_breadcrumb')
     and str(row.get('website_category_path') or '').split(' > ')[0].casefold()=='fragrances'
     and row.get('website_category_source_url') and row.get('website_category_checked_at')
     and (urlsplit(str(row['website_category_source_url'])).hostname or '').removeprefix('www.')==(urlsplit(str(row.get('source_url') or '')).hostname or '').removeprefix('www.')
     and not re.search(r'(?i)\b(?:body\s+(?:lotion|wash)|shampoo|cream|soap|hand\s+wash)\b',name)):
  path=str(row['website_category_path']);leaf=path.split(' > ')[-1]
  lead=name+' is a fragrance'+(' in the '+leaf+' range.' if leaf.casefold()!='fragrances' else '.')
  if not body.startswith(lead):return lead+('\n\n'+original if body and body!=name else ''),'Added the verified source fragrance family/range; all supplied product details retained, no notes or benefits invented.'
 source=public_facts(row,store)
 if source and store=='Hush Puppies':
  kind=str(source.get('product_type') or '').strip().casefold()
  allowed={'casual':'casual shoes','semi formals':'semi-formal shoes','formals':'formal shoes','slipper':'slippers','slippers':'slippers','sandals':'sandals','sandal':'sandals','school shoes':'school shoes','slides':'slides','pumps':'pumps','sneakers':'sneakers','sneaker':'sneakers','belt':'a belt','insole':'insoles','mule shoes':'mules'}
  if kind in allowed:
   lead=name+' is listed by the source as '+allowed[kind]+'.'
   if not body.startswith(lead):return lead+'\n\n'+original,'Added exact source product type; all supplied specifications retained.'
 if source and store=='Junaid Jamshed' and str(source.get('product_type') or '').casefold()=='shalwar' and not body.startswith(name+' is a shalwar garment.'):
  return name+' is a shalwar garment.\n\n'+original,'Added exact matching primary source product type; preserved every supplied size and option.'
 if source and store=='Bata' and source.get('reviewed_tag_overview'):
  lead=source['reviewed_tag_overview']
  if not body.startswith(lead):return lead+'\n\n'+original,'Added exact primary product-tag object type; original article code and options preserved.'
 if source and store=='Aerosoft Studio':
  kind=str(source.get('product_type') or '').strip().casefold()
  types={'slippers':'slippers','slipper':'slippers','sandals':'sandals','running sneakers':'running sneakers','walking sneakers':'walking sneakers','shoes':'shoes'}
  if kind in types:
   lead=name+' is a footwear style listed as '+types[kind]+'.'
   if not body.startswith(lead):return lead+'\n\n'+original,'Added exact public footwear type; original specifications and options retained.'
 if source and store in ('Rawayat','Design by DAS'):
  kind=str(source.get('product_type') or '').strip().casefold()
  overview={'necklace':'a necklace design','earring':'an earring design','earrings':'an earring design','earstuds':'a stud-earring design','nath':'a nose jewellery design','bindiya kanta':'a forehead jewellery design','ring':'a ring design','rings':'a ring design','bracelets':'a bracelet design','anklet':'an anklet design','anklets':'an anklet design','pendent/chain':'a pendant necklace design','pendent/necklace':'a pendant necklace design','choker set':'a jewellery set','mala set':'a jewellery set','locket set':'a jewellery set','bridal set':'a jewellery set'}.get(kind)
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
