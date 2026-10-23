"""Independent purpose evidence: semantic alternatives, never classifier output as proof."""
import re

def text(value):
 return re.sub(r'\s+',' ',re.sub('<[^>]*>',' ',str(value or ''))).strip()
def has(pattern,value):return bool(re.search(pattern,value,re.I))
def review(name,description,category,sku=""):
 title=text(name);body=text(description);evidence=title+' '+body;cat=text(category).lower()
 # Regional jewellery names denote the sold object; care mentions are not perfume evidence.
 jewellery={
  'forehead jewellery':r'\b(?:bindiya|matha\s+patti|maang\s+tikka)\b',
  'jhumka earrings':r'\b(?:jhumk[ai]|bali)\b',
  'hair ties & scrunchies':r'\b(?:hair\s+ties|scrunchies|scrunchy)\b',
 }
 if cat in jewellery and has(jewellery[cat],title+' '+body[:120]):return []
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
  'earrings':'\\b(?:earrings?|jhumk[ai]|bali)\\b',
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
  'jewellery sets':r'\b(?:jewell?ery|necklace|earrings?|choker|bridal)\b.{0,80}\bset\b|\bset\b.{0,80}\b(?:earrings?|necklace)\b',
  'necklaces':r'\b(?:necklaces?|chokers?)\b',
  'earrings':r'\bearrings?\b',
  'bath towels':r'\bbath\s+(?:towels?|sheets?)\b',
  'driving wheels':r'\b(?:driving|racing)\s+(?:wheels?|simulator)\b',
  'thermal paste':r'\bthermal\s+(?:paste|compound)\b',
  'cpu coolers':r'\b(?:cpu|processor|air|liquid)\s+cooler\b',
  'cooling fans':r'\b(?:case|chassis|cooling)\s+fans?\b',
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
 if cat=='face serums' and (has(r'\b(?:hair|eyelash|lip|lash)\b',title) or has(r'\b(?:hair|scalp|lip|lash)\b.{0,40}\bserum\b',body[:300])):return ['Facial serum Category conflicts with named application area']
 if cat=='face moisturisers & creams' and has(r'\b(?:body|hand|foot|heel|baby)\b',title):return ['Facial cream Category conflicts with named application area']
 if cat=='perfumes & fragrances':
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
 bundle=has(r'\b(?:bundle|kit|combo|duo|trio|pack|set|therapy)\b',title+' '+body[:250])
 families={
  'spice bundles':r'\b(?:spice|masala|cumin|coriander|pepper)\b',
  'makeup sets':r'\b(?:makeup|contour|highlight|blush|lipstick|eyeshadow)\b',
  'beauty sets & bundles':r'\b(?:makeup|skin|face|cream|serum)\b',
  'skin care bundles':r'\b(?:skin|face|facial|cream|retinol|pigmentation|niacinamide|serum|acne|hand|feet|pores|breakouts)\b',
  'hair care bundles':r'\b(?:hair|shampoo|conditioner)\b',
  'personal care bundles':r'\b(?:hair|shampoo|face|body)\b'}
 if cat=='skin care bundles' and has(r'\b(?:lipstick|lip gloss|eyeshadow|mascara|foundation|concealer)\b',title):return ['Cosmetics bundle incorrectly classified as skincare']
 if cat in families and bundle and has(families[cat],evidence):return []
 return None
