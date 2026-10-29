"""Source-named sold-object corrections for Xcessories Hub; no price/stock edits."""
import re,unicodedata

def normalized(value):
 value=unicodedata.normalize('NFKC',str(value or ''))
 return re.sub('[‐‑‒–—−]','-',value)
# Accessories before the devices they fit; compound sold objects before components.
RULES=[
 ('USB Chargers',r'\bUSB.C\s+Power\s+Adapter\b'),
 ('Stylus Pens',r'\b(?:stylus|Apple\s+Pencil|Focus\s+Pen|S\s+Pen)\b'),
 ('Tablet Screen Protectors',r'\b(?:ipad|tablet)\b.*\b(?:glass|screen)\s+protector\b'),
 ('Keyboards',r'\bkeyboard\b.*\bfor\s+(?:ipad|tablet)\b'),
 ('Watch Cases',r'\b(?:watch|amazfit)\b.*\bcase\b'),
 ('Watch Screen Protectors',r'\b(?:watch|amazfit)\b.*\b(?:glass|protector)\b'),
 ('Diaper Backpacks',r'\b(?:diaper|baby)\s+backpack\b'),
 ('Camera Bags',r'\b(?:DSLR|camera)\s+bag\b'),
 ('Phone Screen Protectors',r'\bscreen\s+protector\b|\b(?:iphone|galaxy).*\b(?:privacy|tempered|anti.dust).*\bglass\b|\b(?:iphone|galaxy).*\bprivacy\s+glass\b'),
 ('Phone Cases',r'\b(?:iphone|galaxy|phone|pixel|oneplus)\b.*\bcase\b|\bcase\b.*\b(?:iphone|galaxy|phone|pixel|oneplus)\b'),
 ('Tablet Cases',r'\b(?:ipad|tablet)\b.*\bcase\b|\bcase\b.*\b(?:ipad|tablet)\b'),
 ('Watch Straps',r'\b(?:strap|rubber band)\b.*\b(?:fitbit|watch|20mm|22mm)\b|\bwatch\s+(?:strap|band)\b|\bfitbit\b.*\bstrap\b'),
 ('Watch Screen Protectors',r'\b(?:watch|amazfit)\b.*\b(?:glass|protector)\b'),
 ('Phone Pouches',r'\bphone\s+pouch\b'),
 ('Racing Wheel Stands',r'\b(?:racing|steering)\s+wheel.*\bstand\b'),
 ('Gaming Racing Wheels',r'\b(?:racing|steering)\s+wheel\b|\bdirect\s+drive\s+racing\b'),
 ('Gaming Handbrakes',r'\b(?:racing|gaming).*\bhandbrake\b'),
 ('Flight Simulator Controllers',r'\bflight\s+simulator\b'),
 ('Game Controllers',r'\b(?:gamepad|gaming\s+controller|simulation\s+controller)\b'),
 ('Console Receiver Adapters',r'\bracing\s+wheel\s+dongle\b'),
 ('Wireless Microphone Sets',r'\b(?:DJI|dji)\s+mic\b.*\b(?:TX|RX)\b'),
 ('Wireless Microphone Transmitters',r'\bmic\b.*\btransmitter\b'),
 ('Microphones',r'\b(?:microphone|DJI\s+Mic)\b'),
 ('Portable Power Stations',r'\b(?:portable\s+)?power\s+station\b'),
 ('Power Banks',r'\bpower\s*bank\b'),
 ('Power Strips',r'\bpower\s*strip\b|\bextension\s+(?:socket|board)\b'),
 ('Car FM Transmitters',r'\bcar\b.*\b(?:MP3|FM\s+transmitter)\b'),
 ('Car Wireless Chargers',r'\b(?:car\b.*\b(?:wireless\s+charg|charg.*wireless)|wireless\b.*\bcar\b.*\bcharg)'),
 ('Car Chargers',r'\bcar\s+charg(?:er|ing)\b'),
 ('Wireless Chargers',r'\bwireless\s+charg(?:er|ing)\b|\bmagnetic\b.*\bcharg(?:er|ing\s+pad)\b|\bcableless\s+charger\b'),
 ('Charging Stations',r'\bcharging\s+station\b'),
 ('USB Chargers',r'\bcharger\b'),
 ('Car Phone Mounts',r'\bcar\s+mount\b|\bphone\s+mount\b.*\b(?:bike|motorcycle)\b'),
 ('Phone Stands & Grips',r'\bphone\s+(?:stand|grip|holder)\b|\bgrip\s*&\s*stand\b'),
 ('Tablet Stands',r'\btablet\s+(?:stand|holder)\b'),
 ('USB Docking Stations',r'\bUSB.C\s+dock\b|\bdocking\s+station\b'),
 ('USB Hubs',r'\bUSB.C\s+hub\b|\bUSB\s+hub\b'),
 ('HDMI Switches & Splitters',r'\bHDMI\b.*\b(?:splitter|switch)\b'),
 ('Display Emulators',r'\b(?:HDMI\s+dummy|EDID\s+emulator)\b'),
 ('Storage Expansion Cards',r'\b(?:NVMe|SATA)\b.*\bexpansion\s+card\b'),
 ('USB Charging Cables',r'\bcharging\s+cable\b|\bUSB\b.*\bcable\b'),
 ('Wireless USB Receivers',r'\bUSB\b.*\breceiver\b'),
 ('Keyboard & Mouse Sets',r'\b(?:multimedia|wired|wireless).*\bcombo\s+set\b'),
 ('Smart Glasses',r'\bsmart\s+glasses\b|\b(?:Ray.Ban|Meta)\b.*\bdisplay\s+glasses\b'),
 ('Fitness Trackers',r'\b(?:fitness\s+(?:band|tracker)|smart\s+band|screenless\s+(?:health|fitness))\b'),
 ('Smartphones',r'^Apple\s+iPhone\s+\d+.*\bPTA\s+Approved\b|\bRedmi\s+Note\s+\d+.*\b\d+GB\b'),
 ('Tablets',r'\b(?:Redmi\s+Pad|Xiaomi\s+Pad|iPad)\b'),
 ('Stylus Pens',r'\b(?:Focus\s+Pen|S\s+Pen|stylus)\b'),
 ('Projectors',r'\bprojector\b'),
 ('Action Cameras',r'\baction\s+camera\b'),
 ('Hair Styling Tools',r'\bmulti.styler\b'),
 ('Electric Hair Removers',r'\belectric\s+hair\s+remover\b'),
 ('Air Purifiers',r'\bair\s+purifier\b'),
 ('Air Fryers',r'\bair\s*fryer\b'),
 ('Electric Scooters',r'\belectric\s+scooter\b'),
 ('Solar Lighting Systems',r'\bsolar\s+light\s+system\b'),
 ('Reading Lights',r'\breading\s+light\b'),
 ('Pet Water Fountains',r'\bpet\s+fountain\b'),
 ('Air Circulation Fans',r'\bair\s+circulation\s+fan\b'),
 ('Waist & Crossbody Bags',r'\b(?:crossbody\s+waist|waist\s+bag)\b'),
]+ [('Earbud Cases', '\\b(?:silicone|protective|carrying)\\s+case\\b.*\\b(?:airpods|earbuds)\\b|\\bcase\\s+for\\s+(?:airpods|earbuds)\\b'), ('Phone Cases', '\\b(?:cover|case)\\b.*\\b(?:iphone|galaxy|samsung|phone|pixel)\\b|\\b(?:iphone|galaxy|samsung|phone|pixel)\\b.*\\bcover\\b'), ('Car Phone Mounts', '\\bcar\\s+(?:stand|backseat\\s+mount)\\b'), ('Bicycle Phone Cases', '\\brainshield\\s+case\\s+for\\s+bike\\b'), ('USB Hubs', '\\b(?:Type.C|USB.C|multifunction|HDMI)\\b.*\\bhub\\b'), ('Smartwatches', '\\bsmartwatch\\b'), ('Earbuds', '\\b(?:gaming\\s+buds|zbuds|earbuds|earphones)\\b'), ('Headphones', '\\bheadphones\\b|^Apple\\s+AirPods\\s+Max\\b'), ('Digital Cameras', '\\binstant\\s+film\\s+camera\\b'), ('Wireless Microphones', '\\b(?:wireless\\s+lavalier\\s+mic|lavalier\\s+microphone)\\b'), ('Security Cameras', '\\b(?:outdoor|smart|floodlight|security|conference)\\s+camera\\b'), ('Video Doorbells', '\\bvideo\\s+doorbell\\b'), ('Robot Vacuums', '\\brobot\\s+vacuum\\b'), ('Vacuum Cleaners', '\\bvacuum\\s+cleaner\\b'), ('Hard Floor Cleaners', '\\bhard\\s+floor\\s+cleaner\\b'), ('Air Purifiers', '\\b(?:Dyson\\s+(?:HushJet\\s+)?Purifier)\\b'), ('Fans', '\\b(?:handheld|outdoor|stroller|standing|table|neck|mount)\\s+fan\\b'), ('Smart Scales', '\\bsmart\\s+scale\\b'), ('Wireless Presenters', '\\bwireless\\s+presenter\\b'), ('Smart Light Switches', '\\bsmart\\s+light\\s+switch\\b'), ('Smart Plugs', '\\bsmart\\b.*\\b(?:socket|plug)\\b'), ('Smart Light Strips', '\\bsmart\\b.*\\blight\\s+strip\\b'), ('Smart Bulbs', '\\bsmart\\b.*\\b(?:light\\s+bulb|spotlight)\\b'), ('Cabinet Lights', '\\bcabinet\\s+light\\b'), ('GPS & Bluetooth Trackers', '\\b(?:bluetooth\\s+(?:finder|tracker)|anti.lost\\s+smart\\s+tracker|Apple\\s+AirTag|Xiaomi\\s+Tag)\\b'), ('Expansion Batteries', '\\bextra\\s+battery\\b'), ('Smart Home Displays', '\\bsmart\\s+home\\s+display\\b'), ('Power Strips', '\\bextension\\s+cord\\s+socket\\b'), ('Rice Cookers', '\\brice\\s+cooker\\b'), ('HDMI Repeaters', '\\bHDMI\\b.*\\b(?:repeater|extender)\\b'), ('Televisions', '\\bXiaomi\\s+TV\\b'), ('Automatic Pet Feeders', '\\bpet\\s+food\\s+feeder\\b'), ('Mesh Wi-Fi Systems', '\\bmesh\\s+system\\b'), ('USB Audio Adapters', '\\baudio\\s+transfer\\b|\\bUSB\\s+sound\\s+card\\b'), ('Kettles', '\\bkettle\\b'), ('Memory Card Readers', '\\bcard\\s+reader\\b'), ('USB Charging Kits', '\\bcharging\\s+kit\\b'), ('Audio Interfaces', '\\baudio\\s+interface\\b'), ('Subwoofers', '\\bsubwoofer\\b'), ('Numeric Keypads', '\\bnumeric\\s+keypad\\b'), ('Travel Pouches', '\\b(?:travel\\s+pouch|camo\\s+jungle\\s+pouch)\\b'), ('Laptop Sleeves', '\\b(?:stand|slim|leather|armour|layer)\\s+sleeve\\b'), ('E-Readers', '\\bKindle\\b'), ('Smartphones', '^(?:Nothing\\s+(?:CMF\\s+)?Phone|Xiaomi\\s+\\d+T|Samsung\\s+Galaxy\\s+(?:A\\d+|S\\d+)|Redmi\\s+(?:Note\\s+)?\\d+)\\b'), ('Tablets', '\\b(?:Galaxy\\s+Tab|Samsung\\b.*\\bTab\\s+S\\d+|Black\\s+Shark\\s+Wifi\\s+Pad)\\b')]
RULES += [('Camera Lens Protectors', '\\blens\\s+protector\\b'), ('Phone Screen Protectors', '\\b(?:iphone|samsung)\\b.*\\bglass\\s+protector\\b'), ('Phone Cases', '\\bSamsung\\s+(?:S\\d+|Z\\s+Fold)\\b.*\\bcase\\b|\\bMagSafe\\s+case\\b'), ('Gaming Racing Wheels', '\\bracing\\s+simulator\\s+wheel\\b'), ('Racing Gear Shifters', '\\bdriving\\s+force\\s+shifter\\b'), ('Car Rearview Mirrors', '\\bcar\\s+backseat\\s+rearview\\s+mirror\\b|\\bbackseat\\s+rearview\\s+mirror\\b'), ('Laptop Sleeves', '\\b(?:pocket|layer)\\s+sleeve\\b'), ('Video Capture Cards', '\\bcapture\\s+card\\b'), ('Laptop Cooling Pads', '\\bmobile\\s+cooling\\s+radiator\\b'), ('Fans', '\\b(?:tower|Handelheld)\\s+fan\\b'), ('USB Hubs', '\\bHUB\\b'), ('Computer Cases', '\\btower\\b.*\\bcase\\b'), ('Video Adapters', '\\b(?:HDMI|DisplayPort|\\bDP\\b)\\b.*\\b(?:convertor|connector|female|switch)\\b'), ('Storage Expansion Cards', '\\bNVME\\b.*\\bexpress\\s+card\\b'), ('SSD Enclosures', '\\bSSD\\s+enclosure\\b'), ('Hard Drive Enclosures', '\\bhard\\s+drive\\s+enclosure\\b'), ('USB Cables', '\\b(?:USB|Type.C)\\b.*\\bto\\b.*\\b(?:USB|Type.C)\\b'), ('Backpacks', '\\bbackpack\\b|\\bdaypack\\b'), ('Fitness Jump Ropes', '\\bjump\\s+rope\\b'), ('Fitness Trackers', '\\b(?:fitness\\s+wearable|Huawei\\s+Band|Galaxy\\s+Fit)\\b'), ('Vacuum Cleaners', '\\bwet\\s+dry\\s+vacuum\\b'), ('Water Purifiers', '\\bfaucet\\s+water\\s+purifier\\b'), ('Portable Blenders', '\\bportable\\s+blender\\b'), ('Travel Luggage', '\\bluggage\\b'), ('Cooking Appliances', '\\bcooking\\s+robot\\b'), ('Hot Water Dispensers', '\\bhot\\s+water\\s+dispenser\\b'), ('OTG Adapters', '\\bOTG\\b'), ('Car Jump Starters', '\\bcar\\s+jump\\s+starter\\b'), ('Car Socket Splitters', '\\bcar\\s+cigarette\\s+lighter\\b'), ('Ethernet Splitters', '\\bLAN\\s+splitter\\b'), ('Car Phone Mounts', '\\bcar\\s+phone\\s+mount\\b|\\bcar\\s+holder\\b.*\\bphone\\b'), ('Headphones', '\\bAirpod\\s+Max\\b'), ('Power Strips', '\\bpower\\s+socket\\b|\\bpower\\s+extension\\b|\\bextension\\s+power\\s+socket\\b|\\b(?:SC1017|SC2413|SCW3451)\\b.*\\bextension\\b'), ('LED Light Strips', '\\b(?:light\\s+strip|lightstrip)\\b'), ('Selfie Sticks', '\\bselfie\\s+stick\\b'), ('Hair Styling Tools', '\\bmulti\\s*-?\\s*styler\\b'), ('Microphone Kits', '\\bmic\\s+setup\\b'), ('Camera & Phone Gimbals', '\\bgimbal\\b'), ('Tablets', '\\bFire\\s+HD\\b.*\\btablet\\b'), ('Media Streaming Devices', '\\bFire\\s+TV\\s+Stick\\b|\\bApple\\s+TV\\s+4k\\b'), ('Computer Speakers', '\\b(?:PC|multimedia|stereo)\\s+speakers?\\b'), ('Soundbars', '\\bsound\\s*bar\\b'), ('Wired Earphones', '\\b(?:handfree|EarPods)\\b'), ('Microphone Arms', '\\bsuspension\\s+arm\\b'), ('Humidifiers', '\\bhumidifier\\b'), ('Travel Mugs', '\\bstraw\\s+mug\\b'), ('Wireless Microphones', '\\bwireless\\s+mic\\b|\\blavalier\\s+mic\\b'), ('USB Sharing Switches', '\\bUSB\\b.*\\bsharing\\s+switch\\b'), ('Wireless Video Extenders', '\\bwireless\\s+HDMI\\s+transmitter\\b'), ('Wi-Fi Adapters', '\\bUSB\\s+WiFi\\s+dongle\\b'), ('Body Composition Scales', '\\bbody\\s+composition\\s+scale\\b'), ('Lamps', '\\brechargeable\\s+lamp\\b|\\b(?:desk|bedside)\\s+lamp\\b'), ('Night Lights', '\\bnight\\s+light\\b'), ('AA Batteries', '\\bbatteries\\s+AA\\b'), ('Presentation Remotes', '\\bpresentation\\s+remote\\b'), ('Microphones', '\\bexpansion\\s+microphones\\b'), ('Video Conferencing Cameras', '\\bPTZ\\b.*\\bcamera\\b'), ('Power Banks', '\\bbattery\\s+pack\\b'), ('Bluetooth Bookshelf Speakers', '\\bbluetooth\\s+bookshelf\\s+speakers\\b'), ('Car Tyre Inflators', '\\bcar\\s+inflator\\b'), ('Stylus Pens', '\\bApple\\s+Pencil\\b'), ('Pressure Washers', '\\bpressure\\s+washer\\b'), ('Portable Air Pumps', '\\bportable\\s+air\\s+pump\\b'), ('Bluetooth Trackers', '\\bGalaxy\\s+SmartTag\\b'), ('Smart Doorbells', '\\bsmart\\s+doorbell\\b'), ('Bluetooth Transceivers', '\\bBluetooth\\b.*\\btransmitter\\s+and\\s+receiver\\b'), ('Cordless Drills', '\\bcordless\\s+drill\\b'), ('Smart Bulbs', '\\bsmart\\s+LED\\s+bulb\\b'), ('Toasters', '\\btoaster\\b'), ('Earbuds', '\\b(?:Redmi\\s+Buds|Tech\\s+Life\\s+Buds|Master\\s+Buds)\\b'), ('Smartphones', '^Redmi\\s+\\d+[A-Z]\\b'), ('Laptop Bags', '\\bOffice\\s*Mate\\b.*\\bBag\\b'), ('Travel Bags', '\\bcity\\s+commuter\\s+bag\\b')]

def classify(row):
 title=normalized(row.get('name'));body=normalized(row.get('description'))
 for title_pattern,body_pattern,label in [('^DJI Osmo Mobile 8P$', '3.axis\\s+stabilization|mobile\\s+stabilizer', 'Phone Gimbals'), ('^Amaze MAGPRO Magnetic Wireless 10000mAh', 'Li.Polymer\\s+Battery', 'Power Banks'), ('^JBL Boombox 4$', 'woofers.*tweeters', 'Speakers'), ('^Amaze Battle Gear.*Stand', 'GAMING\\s+LAPTOPS', 'Laptop Stands'), ('^Insta360 X5 8K Camera$', '360.\\s*Video', '360 Cameras'), ('^Anker Soundcore Liberty 5$', 'in.ear\\s+wireless\\s+earbuds', 'Earbuds'), ('^Mcdodo Multifunctional Storage Box', 'built.in\\s+charging\\s+cable.*adapter', 'Charging Accessory Kits'), ('^Xiaomi 33W Charging Combo', 'AC\\s+100.240V', 'USB Charging Kits'), ('^Amazon Echo Spot', 'smart\\s+alarm\\s+clock', 'Smart Alarm Clocks'), ('^Amazon Echo Show', 'HD\\s+(?:touchscreen|display)|smart\\s+display', 'Smart Displays'), ('^1HORA Magnetic Bracket', 'support\\s+for\\s+cell\\s+phone', 'Phone Holders'), ('^1Hora 15W Wireless Charge', 'Wireless\\s+Charger', 'Wireless Chargers'), ('^Ugreen 2 IN 1 Output Hdmi Switcher', 'HDMI\\s+Switch', 'HDMI Switches & Splitters'), ('^Meta Quest 3S$', '\\bheadset\\b', 'VR Headsets'), ('^DJI Osmo Action 5 Pro$', 'action\\s+camera', 'Action Cameras'), ('^Amazon Echo Buds', '\\bearbuds\\b', 'Earbuds'), ('^Mi Type.C Fast Charging Version 20W$', 'Input:\\s*100.240V.*Output\\s+Port:\\s*USB.C', 'USB Chargers'), ('^DUDAO F10MAX.*desktop holder', 'Portable\\s+stand\\s+holder', 'Desktop Stands'), ('^1Hora Fast Car Chager', 'car\\s+charger', 'Car Chargers'), ('^Anker 735 PowerPort', 'Anker\\s+735\\s+Charger', 'USB Chargers'), ('^UGREEN 6.in.1 USB C to 3 Ports USB3.0', 'USB\\s+C\\s+Hub', 'USB Hubs'), ('^HUAWEI WiFi AX2$', 'HUAWEI\\s+AX1500\\s+Router', 'Wi-Fi Routers')]:
  if re.search(title_pattern,title,re.I) and re.search(body_pattern,body,re.I|re.S):return label,'reviewed_source_model_purpose','Exact source model name and explicit product-purpose prose; all technical details retained.'
 for label,pattern in RULES:
  if re.search(pattern,title,re.I):return label,'reviewed_source_sold_object','Explicit source product name identifies sold object: '+title
 # Model families need explicit product-purpose prose, not just a device brand.
 if not re.search(r'\b(?:case|strap|protector|charger|cable|stand|holder|cover|bag|band)\b',title,re.I):
  for label,pattern in [('Earbuds',r'\b(?:earbuds?|earphones?|TWS)\b'),('Bluetooth Speakers',r'\b(?:bluetooth|wireless)\s+speaker\b'),('Smartwatches',r'\bsmart\s*watch\b'),('Headphones',r'\bheadphones?\b')]:
   if re.search(pattern,body[:1200],re.I):return label,'reviewed_source_product_purpose','Product-specific description explicitly identifies '+label+': '+body[:700]
 if not re.search(r'\b(?:case|strap|protector|charger|cable|stand|holder|cover|bag)\b',title,re.I):
  for label,pattern in [('Smartwatches',r'\bsmartwatc\s*h\b|\bwatch\s+faces\b'),('Speakers',r'\bspeakers?\b'),('Open-Ear Earphones',r'\bopen.ear\b'),('Gimbal Cameras',r'\bgimbal\s+camera\b|\bportable\s+filming\s+kit\b'),('360 Cameras',r'\b360.?(?:degree|°)?\s*camera\b'),('Phone Gimbals',r'\b(?:smartphone|phone)\b.{0,80}\bgimbal\b'),('Vacuum Cleaners',r'\bvacuum\b|\bhigh.precision\s+suction\b'),('Keyboard & Mouse Sets',r'\bkeyboard\s+and\s+mouse\s+combo\b'),('Keyboards',r'\b(?:keyboard|scissor\s+switch\s+keys)\b'),('USB Charging Kits',r'\ball.in.one\s+charging\s+kit\b')]:
   if re.search(pattern,body[:2500],re.I):return label,'reviewed_source_object_prose','Exact product prose identifies '+label+': '+body[:1200]
 return None
