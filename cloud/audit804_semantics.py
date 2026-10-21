"""Independent purpose evidence: semantic alternatives, never classifier output as proof."""
import re

def text(value):
 return re.sub(r'\s+',' ',re.sub('<[^>]*>',' ',str(value or ''))).strip()
def has(pattern,value):return bool(re.search(pattern,value,re.I))
def review(name,description,category,sku=""):
 title=text(name);body=text(description);evidence=title+' '+body;cat=text(category).lower()
 # Complete garments outrank the components, colour names and care instructions.
 clothing=has(r'\brtw\b|\bun[ -]?stitched\b|\b(?:shirts?|kurt[ai]s?|kameez|trousers?|dupattas?|kaftans?|hoodies?|sweaters?|polo|tees?|frocks?|gharara|sharara|suits?|dress(?:es)?|maxi|outfits?|ensembles?|shawls?|boxers?)\b',evidence)
 if has(r'\bmother size\s*:',description) and has(r'\bkid size\s*:',description) and has(r'\b[234]\s*piece\b',title):clothing=True
 if cat=='shawls' and has(r'^SHAWL[-_]',sku) and has(r'velvet|shawl',evidence):return []
 multi=has(r'\b[234]\s*[- ]?\s*(?:pc|piece)s?\b',title) or has(r'\b(?:rtw|unstitched|stitched|suit|outfit)\s*[:-]?\s*[234]\s*(?:pc|piece)s?\b|\b[234]\s*[- ]?(?:pc|piece)s?\b.{0,70}\b(?:outfit|ensemble|suit|stitched)\b',body)
 state_evidence=re.split(r'(?i)Note: Stitched Orders|Product Options:',evidence,maxsplit=1)[0]
 unstitched=has(r'\bun[ -]?stitched\b',state_evidence)
 ready=has(r'\brtw\b|ready[ -]to[ -]wear|\bstitched\b',re.sub(r'\b(?:un|semi)[ -]?stitched\b','',state_evidence,flags=re.I))
 if clothing:
  if cat in ('clothing sets','kurta & trouser sets','co-ord sets','suits & ensembles'):
   return [] if multi or has(r'\b(?:co[ -]?ord|kurta.*trouser|shirt.*trouser|gharara.*suit)\b',evidence) else None
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
   'dupattas':r'\bdupattas?\b','hoodies':r'\bhood(?:ie|ies)\b','sweatshirts':r'\bsweatshirt\b',
   'sweaters':r'\bsweater\b','shawls':r'\bshawl\b','dresses':r'\b(?:dress|frock|maxi)\b',
   'kaftans':r'\bkaftan\b','abayas':r'\babaya\b','leggings':r'\b(?:legging|tight)s?\b'}
  if cat in clothing_types:
   if multi:return ['Complete outfit classified as one component']
   return [] if has(clothing_types[cat],evidence) else None
  if cat in ('blushers','face powders','perfumes & fragrances','lipsticks') and has(r'\brtw\b|\b(?:shirt|trouser|dupatta)\s*:',description):return ['Garment evidence conflicts with cosmetics Category']
 # These aliases each need independent explicit source purpose evidence.
 proofs={
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
  'lip sets':r'\blip\s+duo\b|\blipstick\s+plus\s+liner\b','lipsticks':r'\blip\s+(?:batom|crayon|cream)\b|\blipsticks?\b',
  'eyebrow products':r'\b(?:eyebrow|brow)\b','makeup adhesives':r'\bglitter\s+glue\b',
  'under eye & kajal':r'\bunder\s+eye\s+pencil\b|\bkajal\b',
  'body mists':r'\bbody\s+mists?\b','fragrance sets':r'\b(?:body\s+mist|fragrance|perfume)\b.{0,80}\b(?:set|collection|pack)\b',
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
  if has(r'\b(?:top|head)(?: notes?)?\s*:',evidence) and has(r'\b(?:heart|middle)(?: notes?)?\s*:',evidence) and has(r'\bbase(?: notes?)?\s*:',evidence) and not has(r'body lotion|body wash|hair|soap',title):return []
  if has(r'\bthe fragrance (?:opens|settles|unfolds)\b',body) and has(r'\bml\b',body) and not has(r'body lotion|body wash|hair|soap',title):return []
  if has(r'\b(?:a|this) fragrance\b|\bFragrance (?:Notes|Type)\s*:',body[:2000]) and has(r'\b(?:ml|notes|scent)\b',evidence) and not has(r'body lotion|body wash|hair|soap',title):return []
  if has(r'\b(?:top|head) notes?\b',evidence) and has(r'\b(?:heart|middle) notes?\b',evidence) and has(r'\bbase notes?\b',evidence) and not has(r'body lotion|body wash|hair|soap',title):return []
 # A target compatibility device is not the object being sold.
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
  'skin care bundles':r'\b(?:skin|face|facial|cream|retinol|pigmentation|niacinamide|serum|acne|hand|feet)\b',
  'hair care bundles':r'\b(?:hair|shampoo|conditioner)\b',
  'personal care bundles':r'\b(?:hair|shampoo|face|body)\b'}
 if cat=='skin care bundles' and has(r'\b(?:lipstick|lip gloss|eyeshadow|mascara|foundation|concealer)\b',title):return ['Cosmetics bundle incorrectly classified as skincare']
 if cat in families and bundle and has(families[cat],evidence):return []
 return None
