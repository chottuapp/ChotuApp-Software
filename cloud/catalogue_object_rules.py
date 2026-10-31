"""Source-word object recovery for new grocery, hardware and craft catalogues."""
import re
from urllib.parse import urlsplit

# Specific sold accessories/forms precede their materials, ingredients and tools.
TOOLS = r'''
Tool Sets|\b(?:tools?\s*set|combination tools|combo kit|electrical test kit|multi garden tools)\b
Drill Bits|\b(?:drill bits?|drills bits|auger bits|masonry drill|hss drill|countersink|step drill|flat wood drill|twist drill)\b
Screwdriver Bits & Holders|\b(?:screwdriver bits?|bit holder|bits? set)\b
Saw Blades & Chains|\b(?:saw blades?|saw chain|multi tool blade|diamond disc|cutting disc|grinding disc|abrasive disc|saw teeth)\b
Sockets & Socket Sets|\b(?:sockets? set|bit socket|impact socket|hexagon(?:al)?\s+socket|extension socket|socket adaptor|socket adapter)\b
Wrenches & Spanners|\b(?:wrench|spanners?)\b
Pliers|\b(?:pliers?|plier set|locking plier|pinching plier)\b
Screwdrivers|\bscrewdrivers?\b
Cutting Tools|\b(?:folding knife|cutter|scissors?|shears?|lopper|snips|cable knife|utility knife|blade knife|dismantling knife|bolt cut|cut off machine)\b
Hammers & Mallets|\b(?:hammer|mallet)\b
Chisels|\bchisels?\b
Files & Rasps|\b(?:wood file|steel file|rasp|files set)\b
Clamps & Vices|\b(?:clamps?|vise|vice)\b
Drills & Drivers|\b(?:drill|impact driver|drive ratchet)\b
Saws|\b(?:saw|hacksaw)\b
Sanders & Polishers|\b(?:sander|polisher)\b
Sandpaper & Sanding Accessories|\b(?:sanding|sandpaper|abrasive paper|polishing pad|polishing sponge|polishing bonnet)\b
Grinders|\bgrinder\b
Welding Equipment|\b(?:welding|electrode holder)\b
Pumps|\b(?:pump|pump control)\b
Generators|\bgenerator\b
Air Compressors|\bair compressor\b
Air Tools|\b(?:air blow gun|spray gun|foam producer|grease gun|caulking gun)\b
Staplers & Nailers|\b(?:stapler|staple gun|nailer|nail gun)\b
Nails & Staples|\b(?:nail|staples?)\b
Garden Power Tools|\b(?:mower|trimmer|brush cutter|bush cutter|tiller|earth auger|hedge shear)\b
Cleaning Equipment|\b(?:vacuum|sweeper|blower|washer|cleaner|mop|toilet brush)\b
Power Tool Batteries & Chargers|\b(?:battery pack|battery charger|charger|batteries)\b
Power Cables & Accessories|\b(?:cables?|cable ties|extension cord|power cord|adaptor|adapter|extension bar|extension pole|power strip|plug)\b
Protective Clothing|\b(?:rain coat|rain suit|jacket|vest|apron|knee pads?)\b
Safety Footwear|\bboots?\b
Protective Gloves|\bgloves?\b
Safety Equipment|\b(?:goggles|helmet|earmuff|respirator|mask|safety glasses|ear plugs|face shield|safety harness)\b
Storage & Tool Bags|\b(?:tools? bag|tool pouch|cabinet|storage shelves|tool box|toolbox|tool chest|organizer|parts box)\b
Lifting & Handling Equipment|\b(?:stacker|truck|trolley|hoist|crane|jack|pallet|shop press|car creeper|creeper seat|body repair set)\b
Measuring Tools|\b(?:scale|caliper|measuring|gauge|laser level|spirit level|distance detector|multimeter|clamp meter|voltage detector|test pencil|cable tracker|tester|square|ruler|level|micrometer)\b
Construction Tools|\b(?:trowel|concrete mixer|plate compactor|tile vibration|demolition breaker|rammer|concrete vibrator|mixer|putty knife|taping kni)\b
Ladders|\bladders?\b
Hoses & Reels|\b(?:hose|reel)\b
Brushes|\bbrush\b
Pens & Markers|\b(?:gel pen|marker|pencil)\b
Locks|\b(?:padlock|door lock)\b
Lighting|\b(?:lamp|light|torch|flashlight)\b
Sealers|\bsealer\b
Riveting Tools|\brivet\b
Painting Tools|\b(?:paint tray|paint roller|roller brush)\b
Fasteners|\b(?:screws?|bolts?|nuts?|washers?|anchors?)\b
Work Benches|\bwork bench\b
'''
FOOD = r'''
Soap & Body Wash|\b(?:soap|body wash|shower gel)\b
Shampoos|\bshampoo\b
Cooking Oils|\b(?:olive|canola|sunflower|cooking|vegetable|coconut) oil\b
Nut Butters & Spreads|\b(?:almond butter|peanut butter|nut butter|chocolate spread|biscoff spread|hazelnut spread)\b
Cheese|\b(?:cheese|cheddar|mozzarella|parmesan|feta|labneh|labne|gouda|halloumi|burrata|mascarpone|ricotta|paneer|parmesano)\b
Yoghurt|\b(?:yog[hu]urt|yogurt|curd|raita|laban)\b
Sauces & Condiments|\b(?:sauce|ketchup|mayonnaise|mustard|dressing|hummus|humus|chutney|salsa|guacamole|sambal|kimchi|pickle|pickled|chilli crisp)\b
Jams & Preserves|\b(?:jam|marm[ae]lade|preserve)\b
Vinegar|\b(?:vinegar|balsamic vingar)\b
Syrups|\bsyrup\b
Ice Cream|\bice\s*cream\b
Juices & Drinks|\b(?:juice|drink|lemonade|tonic water|coconut water|kefir|kombucha|kambucha|smoothie|nectar|soda|beverage)\b
Milk & Cream|\b(?:milk|cream|creamer)\b
Butter & Ghee|\b(?:butter|ghee|margarine)\b
Chocolate & Confectionery|\b(?:chocolate|candy|candies|toffee|toffees|gummies|lollipop|marshmallow|ferrero|raffaello|kit\s*kat|kinder|bounty|snickers?|twix|m&m|mentos|skittles|jelly beans|chewing gum|turkish delight|mithai|halwa)\b
Cakes & Desserts|\b(?:cake|brownie|muffin|cupcake)\b
Biscuits & Crackers|\b(?:biscuits?|cookies?|crackers?|pretzels?|shortbread|rusk|wafer|waffles?|crostini|croutons)\b
Snack Foods|\b(?:chips|crisps|puffs|popcorn|nachos|tortilla chips|snack|makhana)\b
Cakes & Desserts|\b(?:cake|brownie|muffin|croissant|donut|doughnut|pudding|dessert|tart|cupcake|custard)\b
Pasta & Noodles|\b(?:pasta|noodles?|ramen|spaghetti|sphagettini|fettuccine|fusilli|penne|lasagn[ae]|macaroni|vermicelli|farfalle|linguine|tagliatelle)\b
Bread & Wraps|\b(?:bread|tortillas?|wraps?|pizza base|bun|buns|bagel|pita|paratha|chapati|roti|naan)\b
Flour & Grains|\b(?:flour|atta|rice|oats?|quinoa|barley|porridge|bulgur|couscous|semolina|polenta)\b
Breakfast Cereals|\b(?:granola|muesli|cereal|cornflakes|weetabix)\b
Meat & Poultry|\b(?:chicken|beef|mutton|lamb|sausage|salami|mortadell[ao]|meat|pepperoni|seekh|kabab|kebab|nuggets|schnitzel)\b
Seafood|\b(?:fish|salmon|tuna|prawns?|shrimp|sardines|mackerel|anchov)\b
Eggs|\beggs?\b
Honey|\bhoney\b
Tea & Coffee|\b(?:tea|coffee|matcha|espresso|cappuccino|kehwa|kahwa|chai)\b
Spices & Seasonings|\b(?:spice|seasoning|masala|pepper whole|pepper powder|cinnamon|turmeric|cumin|zaatar|oregano|paprika|cardamom|cloves|saffron|coriander powder|nutmeg|garlic powder|onion powder|chilli powder|salt)\b
Nuts & Seeds|\b(?:nuts?|almonds?|cashew|pistachio|hazelnut|walnut|peanuts?|pecans?|macadamia|seeds?|pine nuts|chilgoza)\b
Fruit|\b(?:grapes?|guava|amrood|mosambi|apples?|pomegranate|anaar|melon|malta|papaya|banana|kela|avocado|pear|mango|blueberr(?:y|ies)|strawberr(?:y|ies)|raspberr(?:y|ies)|blackberr(?:y|ies)|pineapple|plum|apricot|peach|nectarine|persimmon|amlok|amla|chickoo?|dates?|ajwa|kiwi|figs?|anjeer|coconut|cherr(?:y|ies)|orange|mandarin|citrus|fruit)\b
Vegetables & Herbs|\b(?:vegetables?|zucchini|kadoo|peas|matar|cilantro|dhanya|mushrooms?|bell pepper|capsicum|shimla|rocket leaves|lemon grass|lime leaves|onions?|pyaz|chill?i|jalapeno|tomato|sprouts?|garlic|okra|bhindi|spinach|karela|gourd|potato|corn|arvi|turnip|shaljam|celery|cauliflower|gobi|brocc?ol?li|cucumber|carrot|cabbage|lettuce|beetroot|brinjal|eggplant|radish|ginger|adrak|lemon|lime|basil|mint|podina|parsley|rosemary|thyme|dill|leek|asparagus|artichoke|pumpkin|squash|beans?|lentils?|daal|dal|chana|chickpeas)\b
Broths|\bbone broth\b
Prepared Beans|\bfoul medammas\b
Syrups|\bglucose syrp\b
Sugar & Baking Ingredients|\b(?:sugar|sweetener|baking|cocoa|yeast|gelatin|gelatine|corn starch|cornstarch|icing|vanilla essence)\b
'''


EXTRA_TOOLS=r"""
Drills & Drivers|\b(?:hammer drill|rotary hammer|impact drill|drill driver)\b
Saw Frames|\bhacksaw frame\b
Extension Poles|\bextension pole\b
Tool Adapters|\b(?:adapter|adaptor)\b
Hex & Torx Keys|\b(?:hex key|torx key)\b
Planers|\b(?:planer|block plane)\b
Pullers & Removal Tools|\b(?:puller|remov(?:al|er))\b
Knife Blades|\bknife blades\b
Putty & Taping Knives|\b(?:taping knives|putty knife)\b
Ratchets|\bratchet\b
Drill Chucks|\bchuck\b
Air Filters|\bhepa\b
Sprayers|\bsprayer\b
Crimping Tools|\bcrimping\b
Oil Drains & Lubricators|\b(?:oil drain|lubricator)\b
Heat Guns|\bheat gun\b
Multi-Tools|\b(?:multi-tool|multi.function tools)\b
Tap & Die Sets|\btap\s*&\s*die\b
Axes|\baxe\b
Storage Equipment|\b(?:storage tower|tool cart)\b
Laser Levels|\bline laser\b
Wall Chasers|\bwall chaser\b
Electrical Switches & Sockets|\b(?:switch|blank slip|mounting plate)\b|^(?:(?:USB|TV|Computer|Telephone|Universal)\s+)?socket\b
Pry Bars|\bwrecking bar\b
Tool Accessories|\baccessories set\b
Gas & Environmental Meters|\b(?:gas indicators|anemometer|temperature.*meter|measure mate)\b
Socket Handles|\bflexible handle\b
Grout Floats|\bgrout float\b
Tin Snips|\btin snip\b
Riveters|\briveter\b
Engines|\bgasoline engine\b
Nibblers|\bnibbler\b
Blenders|\bblender\b
Wire Strippers|\bstripper\b
Suction Lifters|\bsucker\b
Soldering Equipment|\bsoldering\b
Hand Tool Sets|\bhandtools set\b
Diamond Drilling Machines|\bdrilling machine\b
Tripods|\btripods?\b
Glue Guns|\bglue gun\b
Fans|\bfan\b
Safes|\bsafe\b
Punch Sets|\bpunch set\b
Pipe Threading Tools|\bpipe threading\b
Garden Hand Tools|\b(?:hoe|weeder|sprinkler|metal trigger)\b
Air Tool Sets|\bair tools\b
Pressure Cookers|\bpressure cooker\b
Oral Irrigators|\boral irrigator\b
Shavers|\bshaver\b
Hair Curlers|\bcurling tong\b
Waffle & Sandwich Makers|\b(?:waffle maker|sandwich maker)\b
Kettles|\bkettle\b
"""
EXTRA_FOOD=r"""
Fruit|\b(?:strawberr(?:y|ies)|blueberr(?:y|ies)|raspberr(?:y|ies)|blackberr(?:y|ies)|cranberr(?:y|ies)|berr(?:y|ies)|raisins?|munaka|chuwara|kinnow|tamarind)\b
Vegetables & Herbs|\b(?:mushrooms?|mashrooms?|tomatoes|olives?|gherkins?|jalepeno|chillies|pepper|bamboo shoots|veggies|beanz|zoodels)\b
Spices & Seasonings|\b(?:herbs?|peppercorn|sumac|ajwain|zaffran|haldi|elaichi|kalonji|saunf|kala namak)\b
Sugar & Sweeteners|\b(?:stevia|sweetn?er|sweetener|gur|shakkar|sugar)\b
Nuts & Seeds|\b(?:almonds?|peanuts?|pecans?|till|malanga|maghaz|channa)\b
Milk Drinks|\blassi\b
Bread & Rolls|\b(?:ciabatta|panini|baguette|dinner roll|focaccia|brioche|sourdough|multigrain loaf|breadsticks|pain au chocolat)\b
Cooking Fats & Oils|\b(?:tallow|sesame oil|sarson oil|pomace oil|extra vig(?:r)?in oil|extra virgin oil)\b
Cheese|\b(?:parmigiano|brie|camembert|emmental|edam|grana padano|pepperjack|pepper jack)\b
Dips & Cooking Pastes|\b(?:dip|relish|curry paste|tom yum|tahina|tahini)\b
Water & Malt Drinks|\b(?:water|malt flavour)\b
Flour Mixes|\b(?:batter mix|pancake mix|pizza crust mix)\b
Potato Fries|\bfries\b
Traditional Foods|\b(?:panjiri|panjeeri|talbina|chicki|maroonda)\b
Sausages|\bfrankfurter\b
Food Supplements|\b(?:moringa.*powder|maca root powder|salajeet)\b
Cosmetic Oils|\b(?:castor oil|argan oil|kalonji oil)\b
Baskets|\bbasket\b
Gift Cards|\bgift cards?\b
Dumplings|\b(?:dumpling|momos)\b
"""

def rules(table):
 return [(label,re.compile(pattern,re.I)) for label,pattern in (line.split('|',1) for line in table.strip().splitlines())]
TOOLS_RULES=rules(EXTRA_TOOLS)+rules(TOOLS)
FOOD_PRIORITY=r"""
Cakes & Desserts|\b(?:cake|brownie|muffin|cupcake)\b
Biscuits & Crackers|\b(?:biscuits?|cookies?|crackers?|pretzels?|shortbread|rusk|wafers?)\b
Chocolate & Confectionery|\bmilk chocolate\b
Nut & Fruit Mixes|\b(?:trail mix|cocktail.*(?:salted|unsalted)|exotic cocktail mix)\b
Spices & Seasonings|\b(?:garlic powder|onion powder|ginger powder|shawarma|peppercorns?|curry leaves)\b
"""
FOOD_RULES=rules(FOOD_PRIORITY)+rules(FOOD)+rules(EXTRA_FOOD)


MERCHANT_TYPES={
 'snacks':'Snack Foods','beverages':'Juices & Drinks','kefir & kombucha':'Juices & Drinks','gelato & ice cream':'Ice Cream',
 'crisps and snacks':'Snack Foods','crisps & snacks':'Snack Foods','energy snacks':'Snack Foods',
 'cooking sauces & ingredients':'Sauces & Condiments','cooking sauces':'Sauces & Condiments',
 'dried spices & herbs':'Spices & Seasonings','spices and herbs':'Spices & Seasonings',
 'butter & ghee':'Butter & Ghee','crackers & biscuits':'Biscuits & Crackers','iced tea & coffee':'Tea & Coffee',
 'mix nuts':'Nuts & Seeds','seeds':'Nuts & Seeds','frozen fruits & veges':'Frozen Fruit & Vegetable Mixes',
 'juices':'Juices & Drinks',
 'flatbreads':'Bread & Wraps','nuts':'Nuts & Seeds','chocolates':'Chocolate & Confectionery',
 'tea & coffee':'Tea & Coffee','coffee':'Tea & Coffee','cheese':'Cheese',
}
def merchant_labels(fact):
 labels=[]
 for value in [fact.get('product_type','')]+fact.get('published_tags',[]):
  text=str(value).split('/')[-1].strip()
  mapped=MERCHANT_TYPES.get(text.casefold())
  if mapped:labels.append(mapped);continue
  found=[label for label,pattern in FOOD_RULES if re.fullmatch('(?:'+pattern.pattern+')(?:s)?',text,re.I)]
  if found:labels.append(found[0])
 return set(labels)

def classify(row,store):
 title=str(row.get('name') or '');body=str(row.get('description') or '')
 if store=='House of Tools':
  narrow=[('Switch & Socket Covers',r'^Cover\b',r'\b[123] gang cover\b'),('Tyre Inflators',r'air tire inflating gun',r'inflating|pressure'),('Power Tool Batteries & Chargers',r'battery pack',r'voltage|battery'),('Saw Blades & Chains',r'diamond disc',r'blade width|disc'),('Tool Sets',r'combo kit',r'cordless drill')]
  for label,t,b in narrow:
   if re.search(t,title,re.I) and re.search(b,body,re.I):return label,'inferred_explicit_source_object',title+'; '+body[:250]
 if store in {'Fresh Basket','House of Tools'}:
  for label,pattern in FOOD_RULES if store=='Fresh Basket' else TOOLS_RULES:
   match=pattern.search(title)
   if match:return label,'inferred_explicit_sold_object','Explicit source title: '+title
 if store=='Fresh Basket':
  from hold804_repairs import public_facts
  fact=public_facts(row,store)
  if fact:
   candidates=merchant_labels(fact)
   if len(candidates)==1:return next(iter(candidates)),'verified_public_merchant_type',str(fact['source_url'])+'; exact merchant type/tags retained'
 if store=='Bin Fahad' and re.search(r'\b(?:suit fabric|unstitched)\b',body,re.I):return 'Unstitched Fabric','inferred_measured_source_fabric',body[:350]
 if store=='G7 Leather':
  for label,pattern in [('Wallets',r'\bwallet\b'),('Loafers',r'\bloafers\b')]:
   if re.search(pattern,title+' '+body[:350],re.I):return label,'inferred_primary_source_object',(title+' '+body[:350])
 if store=='The Glossy Quill':
  path=str(row.get('website_category_path') or '')
  if urlsplit(str(row.get('website_category_source_url') or '')).hostname in {'theglossyquill.store','www.theglossyquill.store'} and row.get('website_category_status') in {'verified_product_breadcrumb','verified_navigation_membership'} and row.get('website_category_source_url') and row.get('website_category_checked_at'):
   leaf=path.split(' > ')[-1]
   if leaf in {'Mirror Plaques','Classic Plaques','Premium Plaques','Nikkah Certificates','Rings','Earrings','Wedding Favours'}:return leaf,'verified_source_object_taxonomy',path
  named=[('Pendants & Lockets',r'\bpendant\b'),('Glass Boxes',r'\bglass box\b'),('Stands',r'\bstand\b'),('Decorative Bouquets',r'\bbouquet\b'),('Phone Covers',r'\bphone cover\b'),('Decorative Handles',r'\bhandles?\b'),('Ring Holders',r'\bring holder\b')]
  for label,pattern in named:
   if re.search(pattern,title,re.I):return label,'inferred_explicit_sold_object',title
  primary=body[:800]
  for label,pattern in [('Wedding Plaques',r'\b(?:wedding|nikk?ah|resin|personalised|mirror|classic)\b.{0,40}\bplaque\b'),('Decorative Trays',r'\b(?:nikk?ah|mirror|mirrored|resin)\b.{0,30}\btray\b'),('Decorative Plaques',r'\bplaque\b'),('Resin Rings',r'\bresin ring\b|\bring\b.*\bresin\b'),('Jewellery Sets',r'\bjewel(?:ry|lery) set\b')]:
   if re.search(pattern,title+' '+primary,re.I|re.S):return label,'inferred_primary_source_object',title+' '+primary
 return None

def overview(row,store):
 title=str(row.get('name') or '');body=str(row.get('description') or '').strip()
 chosen=classify(row,store)
 if not chosen:return body,None
 # Expand sparse explicit identity only; keep all original facts, numbers and options.
 if body.rstrip('.')==title.rstrip('.') or len(re.findall(r'\w+',body))<5:
  lead=title+' is listed as '+chosen[0].lower()+'.'
  return lead+('\n\n'+body if body and body!=title else ''),'Expanded only the explicit source-named sold object; no missing specifications inferred.'
 return body,None

# Audit uses original source text and separate object proofs, never classifier output.
AUDIT_PROOFS = {
 'Tool Sets':r'tools?\s*set|combination tools|combo kit|electrical test kit|multi garden tools',
 'Drill Bits':r'bits?|countersink|step drill|flat wood drill|twist drill',
 'Screwdriver Bits & Holders':r'screwdriver bit|bit holder|bits? set',
 'Saw Blades & Chains':r'saw blade|saw chain|multi tool blade|diamond disc|cutting disc|grinding disc|abrasive disc|saw teeth',
 'Sockets & Socket Sets':r'socket', 'Wrenches & Spanners':r'wrench|spanners?', 'Pliers':r'plier',
 'Screwdrivers':r'screwdriver', 'Cutting Tools':r'folding knife|cutter|scissor|shear|lopper|snips|knife|bolt cut|cut off machine',
 'Hammers & Mallets':r'hammer|mallet', 'Chisels':r'chisel','Files & Rasps':r'wood file|steel file|rasp|files set',
 'Clamps & Vices':r'clamp|vise|vice','Drills & Drivers':r'drill|rotary hammer|impact driver|drive ratchet',
 'Saws':r'saw|hacksaw','Sanders & Polishers':r'sander|polisher','Sandpaper & Sanding Accessories':r'sanding|sandpaper|abrasive paper|polishing pad|polishing sponge|polishing bonnet',
 'Grinders':r'grinder','Welding Equipment':r'welding|electrode holder','Pumps':r'pump',
 'Generators':r'generator','Air Compressors':r'air compressor','Air Tools':r'air blow gun|spray gun|foam producer|grease gun|caulking gun',
 'Staplers & Nailers':r'stapler|staple gun|nailer|nail gun','Nails & Staples':r'nail|staple',
 'Garden Power Tools':r'mower|trimmer|brush cutter|bush cutter|tiller|earth auger|hedge shear',
 'Cleaning Equipment':r'vacuum|sweeper|blower|washer|cleaner|mop|toilet brush',
 'Power Tool Batteries & Chargers':r'battery|charger|batteries',
 'Power Cables & Accessories':r'cable|extension cord|power cord|adaptor|adapter|extension bar|extension pole|power strip|plug',
 'Protective Clothing':r'rain coat|rain suit|jacket|vest|apron|knee pad','Safety Footwear':r'boot',
 'Protective Gloves':r'glove','Safety Equipment':r'goggle|helmet|earmuff|respirator|mask|safety glasses|ear plug|face shield|safety harness',
 'Storage & Tool Bags':r'tools? bag|tool pouch|cabinet|storage shelves|tool box|toolbox|tool chest|organizer|parts box',
 'Lifting & Handling Equipment':r'stacker|truck|trolley|hoist|crane|jack|pallet|shop press|car creeper|creeper seat|body repair set',
 'Measuring Tools':r'scale|caliper|measur|gauge|level|distance detector|multimeter|clamp meter|voltage detector|test pencil|cable tracker|tester|square|ruler|micrometer',
 'Construction Tools':r'trowel|concrete mixer|plate compactor|tile vibration|demolition breaker|rammer|concrete vibrator|mixer|putty knife|taping kni',
 'Ladders':r'ladder','Hoses & Reels':r'hose|reel','Brushes':r'brush','Pens & Markers':r'pen|marker|pencil',
 'Locks':r'padlock|door lock','Lighting':r'lamp|light|torch|flashlight','Sealers':r'sealer',
 'Riveting Tools':r'rivet','Painting Tools':r'paint tray|paint roller|roller brush',
 'Fasteners':r'screw|bolt|nut|washer|anchor','Work Benches':r'work bench',
 'Soap & Body Wash':r'soap|body wash|shower gel','Shampoos':r'shampoo',
 'Ice Cream':r'ice\s*cream','Nut & Fruit Mixes':r'trail mix|cocktail.*(?:salted|unsalted)|exotic cocktail mix',
 'Cooking Oils':r'(?:olive|canola|sunflower|cooking|vegetable|coconut) oil',
 'Nut Butters & Spreads':r'almond butter|peanut butter|nut butter|chocolate spread|biscoff spread|hazelnut spread',
 'Cheese':r'cheese|cheddar|mozzarella|parmesan|feta|labneh|labne|gouda|halloumi|burrata|mascarpone|ricotta|paneer|parmesano',
 'Yoghurt':r'yog[hu]urt|yogurt|curd|raita|laban',
 'Sauces & Condiments':r'sauce|ketchup|mayonnaise|mustard|dressing|hummus|humus|chutney|salsa|guacamole|sambal|kimchi|pickle|chilli crisp',
 'Jams & Preserves':r'jam|marm[ae]lade|preserve','Vinegar':r'vinegar|balsamic vingar','Syrups':r'syrup|glucose syrp',
 'Juices & Drinks':r'juice|drink|lemonade|tonic water|coconut water|kefir|kombucha|kambucha|smoothie|nectar|soda|beverage',
 'Milk & Cream':r'milk|cream|creamer','Butter & Ghee':r'butter|ghee|margarine',
 'Chocolate & Confectionery':r'chocolate|candy|candies|toffee|gummies|lollipop|marshmallow|ferrero|raffaello|kit\s*kat|kinder|bounty|snickers?|twix|m&m|mentos|skittles|jelly beans|chewing gum|turkish delight|mithai|halwa',
 'Biscuits & Crackers':r'biscuit|cookie|cracker|pretzel|shortbread|rusk|wafer|waffles?|crostini|crouton',
 'Snack Foods':r'chips|crisps|puffs|popcorn|nachos|tortilla chips|snack|makhana',
 'Cakes & Desserts':r'cake|brownie|muffin|croissant|donut|doughnut|pudding|dessert|tart|cupcake|custard',
 'Pasta & Noodles':r'pasta|noodle|ramen|spaghetti|sphagettini|fettuccine|fusilli|penne|lasagn|macaroni|vermicelli|farfalle|linguine|tagliatelle',
 'Bread & Wraps':r'bread|tortilla|wraps|pizza base|bun|bagel|pita|paratha|chapati|roti|naan',
 'Flour & Grains':r'flour|atta|rice|oats|quinoa|barley|porridge|bulgur|couscous|semolina|polenta',
 'Breakfast Cereals':r'granola|muesli|cereal|cornflakes|weetabix',
 'Meat & Poultry':r'chicken|beef|mutton|lamb|sausage|salami|mortadell|meat|pepperoni|seekh|kabab|kebab|nugget|schnitzel',
 'Seafood':r'fish|salmon|tuna|prawn|shrimp|sardine|mackerel|anchov','Eggs':r'eggs?',
 'Honey':r'honey','Tea & Coffee':r'tea|coffee|matcha|espresso|cappuccino|kehwa|kahwa|chai',
 'Spices & Seasonings':r'spice|seasoning|masala|pepper whole|pepper powder|cinnamon|turmeric|cumin|zaatar|oregano|paprika|cardamom|cloves|saffron|coriander powder|nutmeg|garlic powder|onion powder|chilli powder|salt',
 'Nuts & Seeds':r'nut|almond|cashew|pistachio|hazelnut|walnut|peanuts?|pecans?|macadamia|seed|chilgoza',
 'Fruit':r'grape|guava|amrood|mosambi|apple|pomegranate|anaar|melon|malta|papaya|banana|kela|avocado|pear|mango|berr|pineapple|plum|apricot|peach|nectarine|persimmon|amlok|amla|chick|date|ajwa|kiwi|fig|anjeer|coconut|cherr|orange|mandarin|citrus|fruit',
 'Vegetables & Herbs':r'vegetables?|zucchini|kadoo|peas|matar|cilantro|dhanya|mushrooms?|bell pepper|capsicum|shimla|rocket leaves|lemon grass|lime leaves|onion|pyaz|chill?i|jalapeno|tomato|sprout|garlic|okra|bhindi|spinach|karela|gourd|potato|corn|arvi|turnip|shaljam|celery|cauliflower|gobi|brocc|cucumber|carrot|cabbage|lettuce|beetroot|brinjal|eggplant|radish|ginger|adrak|lemon|lime|basil|mint|podina|parsley|rosemary|thyme|dill|leek|asparagus|artichoke|pumpkin|squash|bean|lentil|daal|dal|chana|chickpea',
 'Broths':r'bone broth',
 'Frozen Fruit & Vegetable Mixes':r'fruit|vegetable|frozen','Prepared Beans':r'foul medammas',
 'Sugar & Baking Ingredients':r'sugar|sweetener|baking|cocoa|yeast|gelatin|gelatine|corn starch|cornstarch|icing|vanilla essence',
}

def audit(row,source):
 if not source:return None
 from urllib.parse import urlsplit
 host=(urlsplit(str(source.get('source_url') or '')).hostname or '').removeprefix('www.')
 title=str(source.get('name') or '');body=str(source.get('description') or '');label=row.get('Category')
 if host=='houseoftools.com.pk':
  checks={'Switch & Socket Covers':(r'^Cover\b',r'\b[123] gang cover\b'),'Tyre Inflators':(r'air tire inflating gun',r'inflating|pressure'),'Power Tool Batteries & Chargers':(r'battery pack',r'voltage|battery'),'Saw Blades & Chains':(r'diamond disc',r'blade width|disc'),'Tool Sets':(r'combo kit',r'cordless drill')}
  if label in checks and re.search(checks[label][0],title,re.I) and re.search(checks[label][1],body,re.I):return []
 if host=='freshbasket.com.pk':
  from hold804_repairs import public_facts
  fact=public_facts(source,'Fresh Basket')
  pattern=AUDIT_PROOFS.get(label)
  if fact and pattern:
   for t in [fact.get('product_type','')]+fact.get('published_tags',[]):
    value=str(t).split('/')[-1].strip()
    if MERCHANT_TYPES.get(value.casefold())==label or re.fullmatch('(?:'+pattern+')(?:s)?',value,re.I):return []
 if host in {'houseoftools.com.pk','freshbasket.com.pk'}:
  pattern=AUDIT_PROOFS.get(label)
  if pattern and re.search(r'\b(?:'+pattern+r')',title,re.I):return []
 if host=='binfahad.pk' and label=='Unstitched Fabric' and re.search(r'\b(?:suit fabric|unstitched)\b',body,re.I):return []
 if host=='gsevenleather.com' and label in {'Wallets','Loafers'} and re.search(r'\b'+('wallet' if label=='Wallets' else 'loafers')+r'\b',title+' '+body[:350],re.I):return []
 if host=='theglossyquill.store':
  path=str(source.get('website_category_path') or '')
  if urlsplit(str(source.get('website_category_source_url') or '')).hostname in {'theglossyquill.store','www.theglossyquill.store'} and source.get('website_category_status') in {'verified_product_breadcrumb','verified_navigation_membership'} and source.get('website_category_source_url') and source.get('website_category_checked_at') and path.split(' > ')[-1]==label and label in {'Mirror Plaques','Classic Plaques','Premium Plaques','Nikkah Certificates','Rings','Earrings','Wedding Favours'}:return []
  named={'Pendants & Lockets':r'\bpendant\b','Glass Boxes':r'\bglass box\b','Stands':r'\bstand\b','Decorative Bouquets':r'\bbouquet\b','Phone Covers':r'\bphone cover\b','Decorative Handles':r'\bhandles?\b','Ring Holders':r'\bring holder\b'}
  if label in named and re.search(named[label],title,re.I):return []
  proofs={'Wedding Plaques':r'\b(?:wedding|nikk?ah|resin|personalised|mirror|classic)\b.{0,40}\bplaque\b','Decorative Trays':r'\b(?:nikk?ah|mirror|mirrored|resin)\b.{0,30}\btray\b','Decorative Plaques':r'\bplaque\b','Resin Rings':r'\bresin ring\b|\bring\b.*\bresin\b','Jewellery Sets':r'\bjewel(?:ry|lery) set\b'}
  if label in proofs and re.search(proofs[label],title+' '+body[:800],re.I|re.S):return []
 return None

AUDIT_EXTRA = {
 'Saw Frames':r'hacksaw frame','Extension Poles':r'extension pole','Tool Adapters':r'adapter|adaptor',
 'Hex & Torx Keys':r'hex key|torx key','Planers':r'planer|block plane','Pullers & Removal Tools':r'puller|remov',
 'Knife Blades':r'knife blade','Putty & Taping Knives':r'taping knives|putty knife','Ratchets':r'ratchet',
 'Drill Chucks':r'chuck','Air Filters':r'hepa','Sprayers':r'sprayer','Crimping Tools':r'crimping',
 'Oil Drains & Lubricators':r'oil drain|lubricator','Heat Guns':r'heat gun','Multi-Tools':r'multi.tool|multi.function tools',
 'Tap & Die Sets':r'tap.*die','Axes':r'axe','Storage Equipment':r'storage tower|tool cart',
 'Laser Levels':r'line laser','Wall Chasers':r'wall chaser','Electrical Switches & Sockets':r'socket|switch|blank slip|mounting plate',
 'Pry Bars':r'wrecking bar','Tool Accessories':r'accessories set','Gas & Environmental Meters':r'gas indicators|anemometer|temperature.*meter|measure mate',
 'Socket Handles':r'flexible handle','Grout Floats':r'grout float','Tin Snips':r'tin snip','Riveters':r'riveter',
 'Engines':r'gasoline engine','Nibblers':r'nibbler','Blenders':r'blender','Wire Strippers':r'stripper',
 'Suction Lifters':r'sucker','Soldering Equipment':r'soldering','Hand Tool Sets':r'handtools set',
 'Diamond Drilling Machines':r'drilling machine','Tripods':r'tripod','Glue Guns':r'glue gun','Fans':r'fan','Safes':r'safe',
 'Punch Sets':r'punch set','Pipe Threading Tools':r'pipe threading','Garden Hand Tools':r'hoe|weeder|sprinkler|metal trigger',
 'Air Tool Sets':r'air tools','Pressure Cookers':r'pressure cooker','Oral Irrigators':r'oral irrigator',
 'Shavers':r'shaver','Hair Curlers':r'curling tong','Waffle & Sandwich Makers':r'waffle maker|sandwich maker','Kettles':r'kettle',
 'Sugar & Sweeteners':r'stevia|sweetn?er|sweetener|gur|shakkar|sugar','Milk Drinks':r'lassi',
 'Bread & Rolls':r'ciabatta|panini|baguette|dinner roll|focaccia|brioche|sourdough|multigrain loaf|breadsticks|pain au chocolat',
 'Cooking Fats & Oils':r'tallow|sesame oil|sarson oil|pomace oil|extra vig(?:r)?in oil|extra virgin oil','Dips & Cooking Pastes':r'dip|relish|curry paste|tom yum|tahina|tahini',
 'Water & Malt Drinks':r'water|malt flavour','Flour Mixes':r'batter mix|pancake mix|pizza crust mix',
 'Potato Fries':r'fries','Traditional Foods':r'panjiri|panjeeri|talbina|chicki|maroonda','Sausages':r'frankfurter',
 'Food Supplements':r'moringa.*powder|maca root powder|salajeet','Cosmetic Oils':r'castor oil|argan oil|kalonji oil',
 'Baskets':r'basket','Gift Cards':r'gift card','Dumplings':r'dumpling|momos',
}
# Extend audit definitions independently, retaining pre-existing accepted source words.
for _label,_pattern in AUDIT_EXTRA.items():
 AUDIT_PROOFS[_label]='(?:'+AUDIT_PROOFS[_label]+')|(?:'+_pattern+')' if _label in AUDIT_PROOFS else _pattern
AUDIT_PROOFS['Fruit']+='|strawberr|blueberr|raspberr|blackberr|cranberr|raisins?|munaka|chuwara|kinnow|tamarind'
AUDIT_PROOFS['Vegetables & Herbs']+='|mushroom|mashroom|tomatoes|olive|gherkins?|jalepeno|chillies|pepper|bamboo shoots|veggies|beanz|zoodels'
AUDIT_PROOFS['Spices & Seasonings']+='|shawarma|curry leaves|garlic powder|onion powder|ginger powder|herbs?|peppercorn|sumac|ajwain|zaffran|haldi|elaichi|kalonji|saunf|kala namak'
AUDIT_PROOFS['Nuts & Seeds']+='|almond|peanut|pecan|till|malanga|maghaz|channa'
AUDIT_PROOFS['Cheese']+='|parmigiano|brie|camembert|emmental|edam|grana padano|pepperjack|pepper jack'
