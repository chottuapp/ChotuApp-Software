"""Independent purpose evidence: semantic alternatives, never classifier output as proof."""
import re

def text(value):
 return re.sub(r'\s+',' ',re.sub('<[^>]*>',' ',str(value or ''))).strip()
def has(pattern,value):return bool(re.search(pattern,value,re.I))
def extend_proofs(proofs,additions):
 # New aliases extend existing evidence instead of erasing supported spellings.
 for label,pattern in additions.items():
  old=proofs.get(label)
  proofs[label]=('(?:'+old+')|(?:'+pattern+')') if old and old!=pattern else pattern

def review(name,description,category,sku="",source_type="",verified_path=""):
 title=text(name);body=text(description);cat=text(category).lower()
 if source_type in ('SYNCC - Women Sweater','Women Stitched Sari','Men Peshawari Chappal'):body+=' Source-listed product type: '+source_type
 # Only explicit source garment-type strings; a generic vendor/brand is not purpose evidence.
 if re.fullmatch(r'(?i)(?:women|men|teens|kids|infants)\s+(?:stitched\s+[234]\s+piece(?:\s+shirt\s+trouser)?|(?:cotton\s+silk\s+)?shalwar|(?:special\s+)?kurta|trouser|earrings|bracelet|necklace|ring|eyebrow\s+kit|waistcoat\s+with\s+kurta\s+trouser)',str(source_type or '').strip()):body+=' Source-listed garment type: '+str(source_type)
 evidence=title+' '+body
 # Regional jewellery names denote the sold object; care mentions are not perfume evidence.
 jewellery={
  'forehead jewellery':r'\b(?:jhoom(?:er|ar)|bindiya|matha\s+patti|maang\s+tikka)\b',
  'jhumka earrings':r'\b(?:jhumk(?:ay|a|i|y)|bali)\b',
  'hair ties & scrunchies':r'\b(?:ponytail|hair\s+ties|scrunchies|scrunchy)\b',
 }
 if cat in jewellery and has(jewellery[cat],title+' '+body[:120]):return []
 if cat=='jewellery sets' and has(r'\bset\b',title+' '+body[:150]) and has(r'jewel(?:lery|ry)\s+care|gold\s+plat',body):return []
 # Complete garments outrank the components, colour names and care instructions.
 clothing=has(r'\brtw\b|\bun[ -]?stitched\b|\b(?:stitched|shirts?|kurt[ai]s?|kameez|trousers?|dupattas?|kaftans?|hoodies?|sweaters?|polo|tees?|frocks?|gharara|sharara|suits?|dress(?:es)?|maxi|outfits?|ensembles?|shawls?|boxers?)\b',evidence)
 if has(r'\bmother size\s*:',description) and has(r'\bkid size\s*:',description) and has(r'\b[234]\s*piece\b',title):clothing=True
 if cat=='shawls' and has(r'^SHAWL[-_]',sku) and has(r'velvet|shawl',evidence):return []
 multi=has(r'\b[234]\s*[- ]?\s*(?:pc|piece)s?\b',title) or has(r'\b(?:rtw|unstitched|stitched|suit|outfit)\s*[:-]?\s*[234]\s*(?:pc|piece)s?\b|\b[234]\s*[- ]?(?:pc|piece)s?\b.{0,70}\b(?:outfit|ensemble|suit|stitched)\b',body)
 state_evidence=re.split(r'(?i)Note: Stitched Orders|Product Options:',evidence,maxsplit=1)[0]
 unstitched=has(r'\bun[ -]?stitched\b',state_evidence)
 ready=has(r'\brtw\b|ready[ -]to[ -]wear|\bstitched\b',re.sub(r'\b(?:un|semi)[ -]?stitched\b','',state_evidence,flags=re.I))
 if cat=='unstitched fabric' and has(r'(?im)^\s*length\s*:\s*[2-9](?:\.\d+)?\s*(?:m|meters?|metres?)\b',description) and has(r'(?im)^\s*width\s*:',description) and has(r'(?im)^\s*fabric\s*:',description):return []
 if clothing:
  if cat in ('clothing sets','kurta & trouser sets','co-ord sets','suits & ensembles','stitched outfit sets','kurta & dupatta sets'):
   return [] if multi or has(r'\b(?:co[ -]?ord|kurta.*trouser|shirt.*trouser|(?:kurta|shirt).*dupatta|gharara.*suit)\b',evidence) else None
  if cat=='ready-to-wear outfits':
   if unstitched and not ready:return ['Stitching state conflicts with Category']
   return [] if ready else None
  if cat=='unstitched suits':
   if ready and not unstitched:return ['Stitching state conflicts with Category']
   return [] if unstitched else None
  if cat in ('unstitched fabric','semi-stitched suits'):
   return [] if has(r'\bun[ -]?stitched\b|\bfabric\s*(?:length|cutting)\b|\bsemi[ -]?stitched\b',evidence) else None
  clothing_types={
   'boxers & trunks':r'\bboxers?\b','polo shirts':r'\bpolo\b','t-shirts':r'\b(?:t[ -]?shirt|tee)s?\b','shirts':r'\bshirts?\b',
   'kurtas & kurtis':r'\bkurt[ai]s?\b','trousers':r'\b(?:trousers?|pants?|shalwar)\b',
   'cargo trousers':r'\bcargo\b','joggers':r'\bjoggers?\b','culottes':r'\bculottes?\b',
   'dupattas':r'\bdupattas?\b','hoodies':r'\bhood(?:ie|ies)\b','sweatshirts':r'\bsweat\s*shirts?\b',
   'sweaters':r'\bsweater\b','shawls':r'\bshawl\b','dresses':r'\b(?:dress|frock|maxi)\b',
   'kaftans':r'\bkaftan\b','abayas':r'\babaya\b','leggings':r'\b(?:legging|tight)s?\b'}
  if cat in clothing_types:
   if multi:return ['Complete outfit classified as one component']
   return [] if has(clothing_types[cat],evidence) else None
  if cat in ('blushers','face powders','perfumes & fragrances','lipsticks') and has(r'\brtw\b|\b(?:shirt|trouser|dupatta)\s*:',description):return ['Garment evidence conflicts with cosmetics Category']
 # These aliases each need independent explicit source purpose evidence.
 proofs={
  'peshwas dresses':r'\bpeshwas\b',
  'angrakhas':r'\bangrakha\b',
  'kameez shalwar sets':r'\bkameez\b.{0,800}\bshalwar\b',
  'suit fabric sets':r'\bshirt\s*&\s*trouser\s+[2-9](?:\.\d+)?\s*m\b',
  'cables':'\\b(?:cable|usb.c male to male)\\b',
  'wall chargers':'\\b(?:charger|charging station)\\b',
  'car chargers':'\\bcar\\s+charger\\b',
  'adapters, converters':'\\b(?:adapter|converter|receiver|card\\s+reader)\\b',
  'computer mice':'\\bmouse\\b',
  'belts':'\\bbelts?\\b',
  'leggings':'\\b(?:leggings?|tights?)\\b',
  'shirts':'\\b(?:shirts?|button[ -]down)\\b',
  'hijabs':'\\bhijabs?\\b',
  'earrings':'\\b(?:earrings?|jhumk(?:ay|a|i|y)|bali)\\b',
  'face powders':'\\b(?:pressed|face|compact|loose)\\s+powder\\b',
  'eye patches':'\\beye\\s+patches\\b',
  'skin soothing gels':'\\b(?:skin|aloe\\s+vera)\\b.{0,40}\\bgel\\b',
  'oral care':'\\b(?:breath\\s+spray|mouthwash|toothpaste)\\b',
  'body creams':'\\b(?:body|breast)\\b.{0,50}\\bcream\\b',
  'moccasins':'\\bmoccasins?\\b',
  'court shoes':'\\bcourt\\s+shoes?\\b',
  'backless shoes':'\\bback\\s+open\\b',
  'pencil cases':'\\bpencil\\s+case\\b',
  'lunch bags':'\\blunch\\s+bag\\b',
  'handbags':'\\bbag\\b',
  'baby rash creams':'\\bbaby\\s+rash\\b.*\\bcream\\b',
  'pullovers':'\\bpullovers?\\b',
  'hair ties & accessories':'\\b(?:hair\\s+ties?|scrunch\\w*)\\b',
  'kurta & dupatta sets':'\\b(?:kurta|shirt)\\b.{0,60}\\bdupatta\\b',
  'sweatshirts':'\\bsweat\\s*shirts?\\b',
  'tights':'\\btights?\\b',
  'heels & pumps':r'\b(?:heels?|pumps?)\b',
  'sandals & slides':r'\b(?:sandals?|slides?|flip[ -]?flops?|slippers?)\b',
  'sneakers & trainers':r'\b(?:sneakers?|trainers?)\b',
  'kids shoes':r'\b(?:boys?|girls?|kids?|children)\b.{0,60}\b(?:shoes?|sandals?|pumps?)\b',
  'hair clips & pins':r'\bhair\s+(?:clips?|pins?)\b',
  'shorts':r'\bshorts\b',
  'denim shorts':r'\bdenim\b.{0,30}\bshorts\b',
  'chinos':r'\bchinos?\b',
  'briefs & underwear':r'\b(?:briefs?|underwear)\b',
  'boxers & trunks':r'\b(?:boxers?|trunks?)\b',
  'waistcoats':r'\bwaist\s*coats?\b',
  'blazers & coats':r'\b(?:blazers?|coats?)\b',
  'jubbas & thobes':r'\b(?:jubbas?|thobes?)\b',
  'tunics':r'\btunics?\b',
  'scarves':r'\bscar(?:f|ves)\b',
  'socks':r'\bsocks?\b',
  'cross-body bags':r'\bcross[ -]?body\s+bags?\b',
  'shoulder bags':r'\bshoulder\s+bags?\b',
  'handbags':r'\bhand\s*bags?\b',
  'clutches':r'\bclutch(?:es)?\b',
  'hair ties & scrunchies':r'\b(?:hair ties?|scrunchies|scrunchy)\b',
  'bangles & karas':r'\b(?:bangles?|karas?|kada)\b',
  'pendants & lockets':r'\b(?:pendants?|lockets?)\b',
  'jewellery chains':r'\bchains?\b',
  'bracelets':r'\bbracelets?\b',
  'jewellery sets':r'\b(?:jewel(?:lery|ry)|necklace|earrings?|choker|bridal)\b.{0,80}\bset\b|\bset\b.{0,80}\b(?:earrings?|necklace)\b',
  'necklaces':r'\b(?:mala|necklaces?|chokers?)\b',
  'earrings':r'\b(?:earrings?|baliyan)\b',
  'bath towels':r'\bbath\s+(?:towels?|sheets?)\b',
  'driving wheels':r'\b(?:driving|racing)\s+(?:wheels?|simulator)\b',
  'thermal paste':r'\bthermal\s+(?:paste|compound)\b',
  'cpu coolers':r'\b(?:cpu|processor|air|liquid)\s+cooler\b',
  'cooling fans':r'\b(?:case|chassis|cooling|cpu|uni)\s+fans?\b|\bargb\s+(?:[0-9-]+\s+)?fans?\b',
  'hard drives':r'\b(?:hard\s+(?:disk|drive)|hdd)\b',
  'laptop stands':r'\blaptop\s+(?:stand|riser)\b',
  'laptop chargers':r'\blaptop\s+(?:charger|adapter)\b',
  'hair removal waxes & strips':r'\b(?:wax|waxing)\b',
  'razors & shaving tools':r'\b(?:razor|shaving|shave)\b',
  'petroleum jellies':r'\bpetroleum\s+jelly\b',
  'nail polishes':r'\bnail\s+(?:polish|enamel|colou?r)\b',
  'blackhead removal strips':r'\b(?:blackhead|nose)\s+(?:remov\w*\s+)?strips?\b',
  'bakhoor & incense':r'\b(?:bakhoor|bukhoor|incense)\b',
  'attars & perfume oils':r'\b(?:attar|ittar|perfume\s+oil)\b',
  'rose water & face mists':r'\b(?:rose\s+water|face\s+mist)\b',
  'ubtan powders':r'\bubtan\b',
  'hair colour & henna':r'\b(?:henna|hair\s+colou?r)\b',
  'clay face masks':r'\b(?:multani|fuller.s\s+earth|clay\s+mask)\b',
  'trimmers & clippers':r'\b(?:trimmers?|clippers?)\b',
  'body lotions':r'\blotion\b',
  'baby shampoos':r'\bbaby\b.{0,30}\bshampoo\b',
  'unstitched fabric':r'\bun[ -]?stitched\b',
  'denim trousers':r'\bdenim\b.{0,40}\b(?:trousers?|pants?)\b',
  'smartwatches':r'\bsmart\s*watch(?:es)?\b',
  'hair removal sprays':r'\bhair\s+removal\s+spray\b',
  'depilatory waxes':r'\b(?:depilatory|wax\s+cream)\b',
  'face & body lotions':r'\blotion\b.{0,50}\bface\b|\bface\b.{0,80}\bbody\b.{0,50}\blotion\b',
  'face & body creams':r'\bface\b.{0,80}\bbody\b.{0,50}\bcream\b|\bcream\b.{0,50}\bface\b',

  'eye treatments':r'\beye\s+roller\b|\beye\s+treatment\b',
  'skin moisturisers & creams':r'\b(?:skin|skincare)\b.{0,200}\b(?:cream|moisturi[sz])\w*|\bcream\b.{0,200}\bskin\b',
  'body creams':r'\bbody\s+cream\b|\b(?:intimate areas|underarms|inner thighs)\b',
  'foot creams':r'\b(?:heel|foot|feet)\b.{0,100}\b(?:cream|care)\b',
  'face peels & exfoliators':r'\b(?:peeling|peel|exfoliat)\w*\b',
  'makeup removers':r'\bmicellar\s+water\b|\bmakeup remover\b',
  'face scrubs & exfoliators':r'\b(?:face|facial)\s+scrub\b|\bapricot\s+scrub\b',
  'skin masks':r'\bmask\b.{0,250}\bskin\b|\bskin\b.{0,250}\bmask\b',
  'face masks':r'\b(?:face|facial|mud|clay|kaolin|sheet|tissue)\s+mask\b',
  'beard colours':r'\bbeard\b.{0,50}\bcolou?r\b',
  'hair oils':r'\b(?:hair|scalp|beard)\b.{0,140}\boil\b|\boil\b.{0,140}\b(?:hair|scalp|beard)\b',

  'face serums':r'\bserum\b','lip treatments':r'\blip\b.{0,40}\b(?:serum|treatment)\b',
  'lip sets':r'\blipstick\b.{0,30}\bset\b|\blip\s+duo\b|\blipstick\s+plus\s+liner\b','lipsticks':r'\blip\s+(?:batom|crayon|cream)\b|\blipsticks?\b',
  'eyebrow products':r'\b(?:eyebrow|brow)\b','makeup adhesives':r'\bglitter\s+glue\b',
  'under eye & kajal':r'\bunder\s+eye\s+pencil\b|\bkajal\b',
  'body mists':r'\bbody\s+mists?\b|\bmist\s+notes\b','fragrance sets':r'\b(?:body\s+mist|fragrance|perfume)\b.{0,80}\b(?:set|collection|pack)\b',
  'face washes & cleansers':r'\b(?:cleanser|face\s*wash|facial\s+wash|cleansing\s+(?:milk|oil|balm))\b',
  'face moisturisers & creams':r'\b(?:moisturi[sz]er|face\s+cream|facial\s+cream|ceramide\s+cream|night\s+cream|day\s+cream|brightening\s+cream)\b',
  'face toners':r'\btoner\b','hair colours & dyes':r'\bhair\s+colou?r\b|\bhair\s+dye\b',
  'bath soaps':r'\bsoap\b','hair brushes & combs':r'\bhair\s+brush\b|\bcomb\b',
  'nail tools':r'\bnail\s+(?:cutter|file|filer|clipper|buffer)\b',
  'feminine care':r'\bsanitary\s+pads?\b','body sprays & deodorants':r'\b(?:roll[ -]?on|deodorant|body spray)\b',
  'hair treatments':r'\bhair\s+(?:mask|treatment)\b|\bkeratin\s+mask\b','multipurpose makeup pencils':r'\blip\s*(?:&|and)\s*eye\s+pencil\b',
  'hand washes':r'\bhand\s+(?:soap|wash)\b',
  'spice blends':r'\b(?:qorma|korma|karahi|biryani|tikka|achar gosht|chaat|seekh kabab|malai boti)\s+masala\b',
  'ground spices':r'\b(?:chill?i?|ginger|cumin|coriander|turmeric|pepper|garlic)\s+powder\b',
  'whole spices':r'\b(?:black|white) pepper whole\b|\b(?:cumin|coriander|cardamom|clove)\s+seeds?\b|\bwhole\s+(?:pepper|spice)\b',
  'dried herbs':r'\bkasuri\s+methi\b',
  'headsets & headphones':r'\b(?:headsets?|headphones?|earphones?|earbuds?)\b',
  'earphones/earbuds':r'\b(?:earphones?|earbuds?|tws)\b',
  'motherboards':r'\bmotherboard\b','processors':r'\b(?:processor|ryzen|core i[3579])\b',
  'tablets':r'\b(?:ipad|tablet)\b','microphones':r'\bmicrophone\b',
  'computer speakers':r'\bspeakers?\b','memory cards':r'\b(?:micro\s*sd|microsdxc|memory card)\b',
  'microsd memory cards':r'\b(?:microsd|micro sd)\b','usb hubs & docking stations':r'\b(?:hub|docking station)\b',
  'network switches':r'\b(?:gigabit|ethernet|network)\b.{0,65}\bswitch\b',
  'network routers':r'\brouter\b','vpn gateways & routers':r'\b(?:vpn gateway|router)\b',
  'unmanaged switches':r'\b(?:desktop|gigabit|network|ethernet)\s+switch\b',
  'network range extenders':r'\brange extender\b','mesh wi-fi systems':r'\bmesh\s+(?:wifi|wi-fi)\b',
  'media streaming devices':r'\b(?:tv stick|tv box|streaming media)\b',
  'smart trackers & tags':r'\b(?:smart tracker|find my|find hub)\b',
  'power strips':r'\b(?:power strip|extension socket)\b','security cameras':r'\b(?:home|security|smart) camera\b',
  'graphics cards':r'\b(?:geforce|radeon|graphics card)\b','gaming consoles':r'\b(?:playstation [45](?: pro)? console|gaming console)\b',
  'ink & toner':r'\b(?:ink bottle|toner|ink cartridge)\b',
  'ups & voltage stabilisers':r'\bups\b|\bvoltage stabili[sz]er\b',
  'voltage stabilizers':r'\bvoltage\s+(?:regulator|stabili[sz]er)\b'}
 extend_proofs(proofs,{'cpu contact frames': '\\bcontact\\s+frame\\b', 'fan & lighting controllers': '\\b(?:fan\\s+(?:hub|controller)|argb\\s+(?:and\\s+fan\\s+hub|controller))\\b', 'internal usb hubs': '\\binternal\\s+usb\\b.{0,30}\\bhub\\b', 'computer status displays': '\\btrofeo\\s+vision\\b.{0,50}\\b(?:lcd|display|screen)\\b', 'racing wheels': '\\b(?:racing|steering)\\s+(?:steering\\s+)?wheel\\b', 'smart glasses': '\\bsmart\\s+glasses\\b', 'fitness bands': '\\bsmart\\s+band\\b', 'tablet stylus pens': '\\b(?:apple\\s+pencil|stylus)\\b', 'microsd memory cards': '\\bmicro\\s*sd(?:xc)?\\b', 'monitors': '\\bmonitors?\\b', 'laptops': '\\b(?:laptops?|ideapad|notebook|chromebook|macbook)\\b', 'keyboards': '\\bkeyboards?\\b', 'selfie sticks & tripods': '\\bselfie\\s+stick\\b', 'phone holders & mounts': '\\b(?:phone\\s+(?:stand|holder)|car\\s+mount)\\b', 'computer cases': '\\b(?:atx\\s+(?:gaming\\s+)?case|gaming\\s+case|computer\\s+case)\\b', 'khussa shoes': '\\bkhus[as]+\\b', 'chappals': '\\bchappals?\\b', 'slippers': '\\bslippers?\\b', 'clogs': '\\b(?:clogs?|crocs)\\b', 'baby booties': '\\bbooties\\b', 'mary jane shoes': '\\bmary\\s+janes?\\b', 'derby shoes': '\\bderby\\s+shoes?\\b', 'formal shoes': '\\bformal\\s+shoes?\\b', 'slingback shoes': '\\bsling[ -]?backs?\\b', 'loafers': '\\bloafers?\\b', 'ballet flats': '\\bballet\\s+flats?\\b', 'bras': '\\bbras?\\b', 'camisoles': '\\bcamisoles?\\b', 'panties': '\\bpant(?:y|ies)\\b', 'vests & gilets': '\\b(?:vest|gilet|sando)s?\\b', 'mufflers': '\\bmufflers?\\b', 'watches': '\\bwatch(?:es)?\\b', 'pouches': r'\bpouch(?:es)?\b', 'bowling bags': '\\bbowling\\s+bag\\b', 'backpacks': '\\bback[ -]?packs?\\b', 'bags': '\\bbag\\b', 'hair clips & pins': '\\b(?:claw|bow|heart|hair)\\s+clips?\\b|\\bbobby\\s+pins?\\b', 'hair ties & scrunchies': '\\bscrunch(?:ie|ies|y)\\b|\\bhair\\s+ties?\\b', 'lip oils': '\\blip\\s+(?:glow\\s+)?oil\\b', 'lip plumpers': '\\blip\\s+booster\\b', 'makeup removers': '\\bmakeup\\s+(?:cleanser|remover)\\b|\\bmicellar\\s+water\\b', 'makeup primers': '\\b(?:prime\\s+base|primer\\s+makeup\\s+base|makeup\\s+primer)\\b', 'sunscreens': '\\b(?:sunscreen|sunblock|sun\\s+protect)\\b', 'eyeliners': '\\b(?:smokey\\s+eyes?\\s+pencil|eye\\s+pencil|eyeliner|kajal)\\b', 'makeup powders': '\\b(?:wet\\s*(?:&|and)\\s*dry|terracotta)\\s+powder\\b', 'multipurpose complexion makeup': '\\b3\\s+in\\s+1\\b.*\\bconcealer\\b.*\\bcontour\\b.*\\bfoundation\\b', 'makeup sponges': '\\b(?:sponge\\s+puff|foundation\\s+sponge|makeup\\s+sponge)\\b', 'tweezers': '\\btweezers?\\b', 'blackhead removal tools': '\\bblack\\s*head\\s+pin\\b', 'pedicure sets': '\\bpedicure\\s+kit\\b', 'eyelash curlers': '\\b(?:lash\\s+turner|eyelash\\s+curler)\\b', 'skin scrubs & exfoliators': '\\b(?:skin\\s+polisher|skin\\s+scrub|body\\s+scrub)\\b', 'facial bleach creams': '\\bbleach\\s+cream\\b', 'bleach applicator brushes': '\\bbleach\\s+brush\\b', 'false eyelashes': '\\b(?:false\\s+)?eyelashes\\b', 'bb face makeup': '\\bbb\\s+skin\\s+editor\\b', 'shalwars': '\\bshalwar\\b', 'hair brushes & combs': '\\b(?:hair\\s+brush|blower?\\s+brush|blore\\s+brush|comb)\\b'})
 proofs['hair accessories']=r'\bhair\s+accessor(?:y|ies)\b'
 proofs['jeans']=r'\b(?:denim jeans|jeans)\b'
 proofs['earrings']=r'\b(?:earrings?|earings?|baliyan)\b'
 proofs['girls training bras']=r'\bbeede\b.{0,40}\bgirls\b|\bgirls\s+beede\b'
 proofs['jewellery chains']=r'\b(?:neck\s+chain|jewellery\s+chain|gold[ -]?plated\s+.*chain|gold\s+snake\s+chain)\b|\bchain\b.{0,500}\bjewel(?:lery|ry)\s+care\b'
 proofs['herbal oils']=r'\bherbal\s+oil\b'
 proofs['case fans']=proofs['cooling fans']
 extend_proofs(proofs,{
  'fragrance gift sets':r'\bgift\s+box\b.{0,1600}\b(?:perfume|body mist)\b',
  'sugar substitutes':r'\bksylitol\b.{0,500}\b(?:sweetener|sugar alternative)\b',
  'sleep & relaxation sets':r'\bsleep\s+well\s+package\s+combo\b',
  'wellness supplement sets':r'\b(?:overall\s+health\s+package|wellness\s+set)\b.{0,1000}\b(?:capsules|herbal tea|herbal powder)\b',
  'instant tea mixes':r'\b(?:chai\s+(?:latte\s+)?|kehwa\s+)instant\s+premix\b',
  'hair conditioners':r'\bconditioner\b.{0,1000}\b(?:hair|scalp)\b',
  'hair conditioning treatments':r'\bhair\s+mayonnaise\b.{0,500}\bconditioning\b',
  'bb & cc creams':r'\bbb\s+cream\b',
  'dietary supplement oils':r'\boil\b.{0,1800}\b(?:easy.to.consume|this supplement|daily nutritional care)\b',
 })
 extend_proofs(proofs,{'ponchos & capes':r'\b(?:knit\s+cape\s+jumper|poncho|capelet)\b','sarees':r'\b(?:saree|sari)\b','makeup setting sprays':r'\b(?:makeup\s+)?fixing\s+spray\b','sweaters':r'\bsweater\b'})
 extend_proofs(proofs,{'foundations':r'\bfoundation\b'})
 extend_proofs(proofs,{'facial cleansing cloths':r'\bfacial\s+cleansing\s+(?:whitening\s+)?cloths\b','eyeshadow applicators':r'\beye\s+shade\s+applicator\b','skin & hair care sets':r'\bskin\s+and\s+hair\b.{0,80}\bset\b','lipsticks':r'\blipstick\b'})
 extend_proofs(proofs,{'scented candles': '\\b(?:(?:scented|aromatherapy|solid)\\s+)?candle\\b', 'herbal capsules': '\\b(?:herbalist\\b.*\\bcapsules?|herbal\\s+oil\\s+capsule)\\b', 'food flavourings': '\\bfood\\s+essence\\b', 'olive cooking oils': '\\b(?:extra\\s+virgin|pomace)\\s+olive\\s+oil\\b', 'dental gels': '\\bdental\\s+gel\\b', 'intimate washes': '\\bintimate\\s+wash\\b', 'hand cleansers': '\\bhand\\s+cleanser\\b', 'foot sprays': '\\bfoot\\s+spray\\b', 'soap bars': '^soap\\s+with\\b', 'miswak sticks': '\\bmiswak\\b', 'herbal nasal drops': '\\bherbal\\s+nasal\\s+drops\\b', 'herbal nasal oils': '\\bherbal\\s+nasal\\s+oil\\b', 'herbal relief oils': '\\b(?:herbal\\s+relief\\s+oil|sinu[ -]drain\\s+oil)\\b', 'massage gels': '\\bicy\\s+hot\\b.*\\bgel\\b', 'magnesium sprays': '\\bmagnesium\\s+spray\\b', 'massage creams': '\\b(?:massage\\s+cream|relief\\s+cream\\s*[-–]\\s*himomed)\\b', 'shilajit supplements': '\\bshilajit\\b', 'garden cress seeds': '\\bgarden\\s+cress\\s+seeds\\b', 'psyllium husk supplements': '\\b(?:ispaghol|psyllium\\s+husk)\\b', 'herbal powders': '\\b(?:moringa|berberine)\\s+powder\\b', 'face mask powders': '\\bherbal\\s+beauty\\s+mask\\s+powder\\b', 'disinfectant sprays': '\\bdisinfectant\\s+spray\\b', 'sanitiser sprays': '\\bsanitizer\\s+spray\\b', 'facial gels': '\\bface\\s+gel\\b', 'hair tonics': '\\bhair\\s+tonic\\b'})
 extend_proofs(proofs,{'household batteries': '\\b(?:AA|AAA)\\s+size\\s+cell\\s+batteries\\b', 'eyelash adhesives': '\\beyelash\\s+glue\\b', 'insecticide sprays': '\\b(?:insecticide\\s+spray|insect\\s+killer\\s+spray)\\b', 'mosquito coils': '\\bmosquito\\s+coil\\b', 'mosquito repellent devices': '\\bmosquito\\s+killer\\s+machine\\b', 'mouth fresheners': '\\bmouth\\s+spray\\b', 'facial bleaches': '\\b(?:creme\\s+bleach|cream\\s+bleach|bleach\\s+sachet|facial\\s+bleach)\\b', 'sanitary pads': '\\bpads\\b.{0,80}\\b(?:heavy\\s+flow|leak\\s+protection)\\b', 'facial tissues': '\\b(?:pop[ -]?up\\s+)?tissues\\b', 'packaging stretch wrap': '\\bstretch\\s+wrap\\b.{0,40}\\bpackaging\\b', 'food cling film': '\\bcling\\s+film\\b.{0,40}\\bfood\\b', 'baby rash creams': '\\b(?:nappy|diaper)\\s+rash\\b', 'water filter cartridges': '\\b(?:water\\s+carbon\\s+filter|carbon\\s+filter\\b.*\\bhousehold|micron\\s+filter|PPF\\s+5\\s+micron)\\b', 'lice removal combs': '\\b(?:anti[ -]?lice|lice\\s+removal)\\b.*\\bcomb\\b', 'facial steamers': '\\bfacial\\s+steamer\\b', 'pest-control traps': '\\b(?:mouse|rat)\\s+(?:trap|catching)\\b', 'hand wash': '\\bhand\\s*wash\\b', 'car engine degreasers': '\\b(?:engine\\s+degreaser|car\\s+heavy\\s+duty\\s+degreaser)\\b', 'car polishes': '\\bcar\\s+polish\\b', 'multipurpose household cleaners': '\\bmulti[ -]?purpose\\s+cleaner\\b', 'floor cleaners': '\\bphenyl\\b', 'dishwashing liquids': '\\b(?:liquid\\s+(?:gel\\s+)?dish\\s*wash|dishwashing\\s+liquid)\\b', 'toilet & tile cleaners': '\\btoilet\\s+and\\s+tiles?\\s+cleaner\\b', 'glass cleaners': '\\bglass\\s+cleaner\\b', 'laundry bleaches': '\\bbleach\\s+liquid\\s+for\\s+white\\s+clothes\\b', 'adult diapers': '\\badult\\s+diaper\\b', 'baby diapers': '\\bcarebaby\\b.*\\bdiapers\\b', 'hair removal waxes': '\\b(?:finger\\s+wax|brazilian\\s+.*wax|wax\\b.*\\bhair\\s+removal)\\b', 'hair removal serums': '\\bstop\\s+hair\\b.*\\bserum\\b', 'hair crimpers': '\\bhair\\s+crimple\\b', 'hair curlers': '\\b(?:hair\\s+curler|curler\\s+pro\\s+soft\\s+curl)\\b', 'hair sprays': '\\bhair\\s+spray\\b', 'blackhead removal strips': '\\bnose\\s+pore\\s+strips\\b', 'epilators & trimmers': '\\bepilator\\b', 'lip masks': '\\blip\\s+mask\\b', 'hair protein treatments': '\\bhair\\s+protein\\b.*\\btreatment\\b'})
 proofs['anklets']=r'\banklets?\b'
 proofs['forehead jewellery']=r'\b(?:tikka|mathapatti|jhoomer|bindiya)\b'
 proofs['bangles & karas']=r'\b(?:bangles?|karay|karas?|kada)\b'
 proofs['pendants & lockets']=r'\b(?:pendants?|pendents?|lockets?)\b'
 proofs['hair jewellery']=r'\bhair\s+vine\b'
 proofs['hand harnesses']=r'\b(?:panjangla|angla)\b'
 proofs['commemorative coin cards']=r'\bcoin\s+card\b'
 proofs['artificial nails']=r'\b(?:false\s+nail|nail\s+art\s*\(\d+\s*pcs)\b'

 extend_proofs(proofs,{'remote control cars': '\\bremote\\s+control\\s+car\\b', 'remote control helicopters': '\\bremote\\s+control\\s+helicopter\\b', 'drawing stencils': '\\bstencils?\\b', 'drawing paper': '\\bdrawing\\s+paper\\b', 'board games': '\\bboard\\s+game\\b', 'jigsaw puzzles': '\\bjigsaw\\s+puzzle\\b', 'puzzle cubes': '\\bpuzzle\\s+cube\\b', 'educational puzzles': '\\b(?:math|shape)\\b.*\\bpuzzle\\b|\\bpuzzle\\b.*\\b(?:math|shape)\\b', 'montessori busy boards': '\\bmontessori\\s+busy\\s+board\\b', 'body shapers': '\\bbody\\s+shaper\\b', 'stockings': '\\bstockings?\\b', 'bralettes': '\\bbrallete\\b', 'hand mirrors': '\\bhand\\s+mirror\\b', 'makeup puff & clip sets': '\\bmakeup\\s+puff\\s*&\\s*clip\\s+set\\b'})
 extend_proofs(proofs,{
  'face wash':r'\b(?:face|facial)\s+(?:wash|cleansing\s+gel)\b',
  'foot scrubs':r'\bfoot\s+scrub\b',
  'multipurpose skin creams':r'\bcream\b.*\bface\b.*\bbody\b.*\bhands?\b',
  'lipstick sets':r'\blipstick\s+bundle\b',
  'face serums':r'\bserum\b',
  'makeup setting powders':r'\b(?:illuminating|makeup|beauty)\s+baking\s+powder\b',
  'instant tea mixes':r'\bchai\s+instant\s+premix\b',
  'instant drink mixes':r'\b(?:limopani|drink)\s+instant\s+premix\b|\binstant\s+drink\s+powder\b',
  'herbal gummies':r'\b(?:herbalist|ashwagandha)\b.*\bgummies\b',
  'pain relief ointments':r'\bpain\s+relief\s+massage\s+ointment\b',
  'vapor rubs':r'\bvapor\s+rub\b',
  'pain relief sprays':r'\b(?:quick|pain)\s+relief\s+spray\b',
  'foundation sticks':r'\b(?:professional\s+paint\s+stick|foundation\s+stick)\b',
  'makeup primers':r'\bprimer\b|\bprime\s+base\b',
 })
 extend_proofs(proofs,{
  'nose jewellery':r'\b(?:nath|nose\s+(?:pin|ring))\b',
  'hair claws':r'\bhair\s+claw\b',
  'headbands':r'\b(?:headband|hairband|hair\s+band)\b',
  'hair combs':r'\b(?:hair\s+|trimming\s+)?comb\b',
  'pendant necklaces':r'\b(?:pendent|pendant)\b',
 })
 extend_proofs(proofs,{
  'diffuser oils':r'\bdiffuser\s+oil\b',
  'eyebrow kits':r'\b(?:eye)?brow\s+(?:makeup\s+)?kit\b',
  'eyeliners':r'\b(?:dipliner|eyeliner|kajal|smokey\s+eyes?\s+pencil|eye\s+pencil)\b',
  'face powders':r'\b(?:mineral|face|loose|compact)\s+powder\b',
  'makeup removers':r'\bmake[ -]?up\s+(?:remover|cleanser)\b|\bmicellar\s+water\b',
  'cardigans':r'\bcardigan\b',
  'moccasins':r'\bmocass?ins?\b|\bloafer\b',
  'monk shoes':r'\bmonk\b.{0,30}\bshoes\b',
  'rings':r'\b(?:women\s+ring|finger\s+ring)\b',
  'room fragrances':r'\b(?:room\s+(?:spray|freshener)|reed\s+diffuser)\b',
 })
 proofs['hair clips & pins']=r'\b(?:hair|heart|bow)\s+(?:clips?|pins?)\b|\bbobby\s+pins?\b'
 proofs['hair brushes & combs']=r'\b(?:hair|blower?|blore)\s+brush(?:es)?\b|\bcombs?\b'
 extend_proofs(proofs,{
  'kurta & pyjama sets':r'\bkurta\s+p[ay]jama\b',
  'sherwanis':r'\bsherwanis?\b',
  'denim shorts':r'\bjorts\b|\bdenim\b.{0,30}\bshorts\b',
  'bomber jackets':r'\bbomber\b',
  'flats':r'\bflats\b',
  'pullovers':r'\bpull[ -]?over\b',
  'pyjamas':r'\bp[ay]jama\b',
  'tops':r'\b(?:knit|sleeve|capelet)\b.{0,80}\btop\b',
  'hand creams':r'\bhand\s+cream\b',
 })
 extend_proofs(proofs,{
  'bed sheets':r'\bbed\s+sheet\b',
  'school shoes':r'\bschool\s+shoes?\b',
  'stoles':r'\bstoles?\b',
  'bralettes':r'\bbralettes?\b',
  'loungewear sets':r'\blounge\s*wear\s+set\b',
  'nail care kits':r'\bnail\s+care\s+kit\b',
  'stationery sets':r'\bstationery\s+set\b',
  'boots':r'\bboots?\b',
  'tote bags':r'\btote\s*bag\b',
  'hair crowns & tiaras':r'\b(?:crown|tiara)\b',
  'skin lotions':r'\blotion\b.{0,500}\bskin\b',
  'skin scrubs & exfoliators':r'\bskin\s+polisher\b|\bscrub\b.{0,800}\bskin\b|\bskin\b.{0,800}\bscrub\b',
  'lip balms':r'\blip\s+(?:balm|butter)\b',
  'hand moisturisers':r'\bhand\s+elixir\b.{0,500}\b(?:hydrat|moistur)',
 })
 extend_proofs(proofs,{
  'compressed towels':r'\bcompressed\s+towels?\b',
  'massage devices':r'\b(?:massager|massage\s+gun|fascia\s+gun)\b',
  'skin toning solutions':r'\btoning\s+solution\b',
  'body scrubs':r'\b(?:body|shower)\s+scrub\b',
  'hair colour developers':r'\bdeveloper\b.{0,15}\b(?:volume|vol)\b',
  'nightdresses':r'\bnight(?:y|ie|ies|dress)\b',
  'panties':r'\bpant(?:y|ie|ies)\b',
  'pyjama sets':r'\bp[ay]jama\s+set\b',
  'cardholders':r'\bcard[ -]?holders?\b',
  'jewellery chains':r'\b(?:gold|silver|plated)\s+chain\b',
  'hair accessory sets':r'\bhair\s+accessor(?:y|ies)\s+(?:combo\s+)?set\b',
  'artificial nails':r'\b(?:artificial|false|press[ -]?on)\s+nails?\b|\bnail\s+art\s*\(\d+\s*pcs\b',
  'gift baskets':r'\bgift\s+basket\b.{0,150}\byou can fill\b',
 })
 extend_proofs(proofs,{
  'eyeshadow palettes':r'\bpalette\b.{0,1600}\b(?:eyelids?|eyes?|shadow)\b|\b(?:eyes?|shadow)\b.{0,300}\bpalette\b',
  'face mists & toners':r'\bmist\b.{0,1600}\bface\b',
  'face scrubs & exfoliators':r'\bscrub\b.{0,1600}\bface\b',
  'face wash':r'\b(?:face\s+wash|facial\s+cleansing\s+gel)\b',
  'henna cones':r'\bcone\s+(?:mehndi|henna)\b',
  'skin moisturising gels':r'\b(?:moisturi[sz]ing\s+(?:water\s+)?|soothing\s+)gel\b.{0,800}\bskin\b',
 })
 if cat=='face serums' and (has(r'\b(?:hair|eyelash|lip|lash)\b',title) or has(r'\b(?:hair|scalp|lip|lash)\b.{0,40}\bserum\b',body[:300])):return ['Facial serum Category conflicts with named application area']
 if cat=='face moisturisers & creams' and has(r'\b(?:body|hand|foot|heel|baby)\b',title):return ['Facial cream Category conflicts with named application area']
 if cat in ('body spray','body sprays') and str(verified_path).casefold()=='body spray' and has(r'\b(?:spray|fragrance)\b',body):return []
 if cat=='casual footwear' and has(r'\bsofty\b',title) and has(r'\b(?:feet|footbed|strap|footwear|shoes)\b',body+' '+str(verified_path)):return []
 if cat=='canvas shoes' and has(r'\bcasual\s+canvas\b',title) and has(r'\b(?:heel|sole|footbed|shoes)\b',body):return []
 if cat=='toners & tonics' and 'toner' in str(verified_path).casefold() and has(r'\b(?:rose water|aloe vera)\b',evidence):return []
 if cat=='perfumes & fragrances':
  if has(r'\bfragrance\b.{0,80}\bopens\b',body) and has(r'\b(?:pulse points|notes|musk)\b',body) and not has(r'\b(?:soap|wash|cream|lotion|candle|hair)\b',title):return []
  if has(r'\bapply perfume\b',body) and has(r'\btop\s+note',body) and has(r'\b(?:base|dry)\s+note',body):return []
  if any(part.casefold() in ('fragrance','fragrances','perfume','perfumes',"men's fragrance","women's fragrance",'arabia perfumes','attar') for part in str(verified_path).split(' > ')) and not has(r'body lotion|body wash|hair|soap|cream',title):return []
  if has(r'\bfragrance guide\b',body) and has(r'\bscent family\s*:',body) and has(r'\bsize\s*:\s*\d+\s*ml\b',body):return []
  notes=[has(r'(?m)^\s*'+part+r'(?:\s+notes?)?\s*:?\s*(?:\n|$)',description) for part in ('top','(?:hear(?:t)?|mid(?:dle)?)','(?:base|dry)')]
  if all(notes) and not has(r'body lotion|body wash|hair|soap',title):return []
  if has(r'\b(?:top|head)(?: notes?)?\s*:',evidence) and has(r'\b(?:heart|middle)(?: notes?)?\s*:',evidence) and has(r'\bbase(?: notes?)?\s*:',evidence) and not has(r'body lotion|body wash|hair|soap',title):return []
  if has(r'\bthe fragrance (?:opens|settles|unfolds)\b',body) and has(r'\bml\b',body) and not has(r'body lotion|body wash|hair|soap',title):return []
  if has(r'\b(?:a|this) fragrance\b|\bFragrance (?:Notes|Type)\s*:',body[:2000]) and has(r'\b(?:ml|notes|scent)\b',evidence) and not has(r'body lotion|body wash|hair|soap',title):return []
  if has(r'\b(?:top|head) notes?\b',evidence) and has(r'\b(?:heart|middle) notes?\b',evidence) and has(r'\bbase notes?\b',evidence) and not has(r'body lotion|body wash|hair|soap',title):return []
 # A target compatibility device is not the object being sold.
 if cat=='smartwatches' and has(r'\b(?:strap|band|charger|protector|cable)\b',title):return ['Watch accessory incorrectly classified as smartwatch']
 if cat=='tablets' and has(r'\b(?:stylus|pencil)\b',title):return ['Stylus incorrectly classified as tablet']
 if cat=='processors' and has(r'\bcooler\b|thermal paste|contact frame|motherboard|laptop|memory',title):return ['CPU accessory incorrectly classified as processor']
 if cat=='gaming consoles' and has(r'controller|driving|racing wheel',title):return ['Gaming accessory incorrectly classified as console']
 if cat=='memory cards' and has(r'card reader',title):return ['Reader incorrectly classified as memory card']
 if cat in proofs and has(proofs[cat],title+' '+body[:1600]):
  return []
 bundle=has(r'\b(?:bundle|kit|combo|duo|trio|pack|set|basket|therapy)\b|\bbuy\b.*\bget\b.*\bfree\b',title+' '+body[:250])
 families={
  'spice bundles':r'\b(?:spice|masala|cumin|coriander|pepper)\b',
  'makeup sets':r'\b(?:makeup|contour|highlight|blush|lipstick|eyeshadow)\b',
  'beauty sets & bundles':r'\b(?:makeup|skin|face|cream|serum)\b',
  'skin care bundles':r'\b(?:skincare|rose water|lotion|skin|face|facial|cream|retinol|pigmentation|niacinamide|serum|acne|hand|feet|pores|breakouts)\b',
  'hair care bundles':r'\b(?:hair|shampoo|conditioner)\b',
  'sun care bundles':r'\b(?:sunscreen|sunblock|sun protection)\b',
  'personal care bundles':r'\b(?:skincare|haircare|fragrance|hair|shampoo|face|body)\b'}
 if cat=='skin care bundles' and has(r'\b(?:lipstick|lip gloss|eyeshadow|mascara|foundation|concealer)\b',title):return ['Cosmetics bundle incorrectly classified as skincare']
 if cat in families and bundle and has(families[cat],evidence):return []
 return None
