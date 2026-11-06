"""Source-bound customer copy and independent description completeness checks."""
import html,re
from collections import Counter,OrderedDict
DESCRIPTION_STYLE_VERSION='customer-copy-v3'

# Plain text headings work in Excel and native mobile text controls.
HEADINGS=OrderedDict([
 ('details','✦ Key Details'),('contents','📦 Pack Contents'),
 ('ingredients','✦ Ingredients & Composition'),('fabric','✦ Fabric & Fit'),
 ('measurements','📏 Measurements'),('age','✦ Age & Suitability'),('specifications','✦ Specifications'),
 ('directions','✦ How to Use'),('styling','✦ Styling & Wear'),('care','✦ Care Instructions'),
 ('warnings','⚠ Precautions'),('warranty','✦ Warranty'),
 ('packaging','📦 Packaging'),('options','🎨 Product Options')])
ALIASES={
 'overview':'overview','about this item':'overview','about the product':'overview','product overview':'overview',
 'age & suitability':'age','recommended age':'age','age suitability':'age',
 'key details':'details','details':'details','key features':'details','features':'details','design details':'details','product highlights':'details',
 'pack contents':'contents','package contents':'contents','what is included':'contents','what\'s included':'contents','in the box':'contents',
 'ingredients':'ingredients','ingredients & composition':'ingredients','composition':'ingredients',
 'fabric':'fabric','fabric details':'fabric','fabric & fit':'fabric','fit details':'fabric',
 'measurements':'measurements','dimensions':'measurements','size chart':'measurements',
 'specifications':'specifications','technical specifications':'specifications','product specifications':'specifications',
 'how to use':'directions','directions':'directions','usage':'directions','preparation':'directions',
 'styling tip':'styling','styling tips':'styling','styling & wear':'styling',
 'care instructions':'care','jewellery care':'care','jewelry care':'care','care':'care','storage':'care','care & storage':'care',
 'precautions':'warnings','warnings':'warnings','safety information':'warnings',
 'warranty':'warranty','packaging':'packaging','product options':'options','available options':'options','options':'options',
}
BOILERPLATE=[
 re.compile(r'(?i)^this (?:earing|earring|item|product) (?:is )?available very reasonable price[.!]?\s*$'),
 re.compile(r'(?i)^fancy jewel(?:ry|lery) for wedding season is normally trendy in Pakistan[.!]?\s*$'),
 re.compile(r'(?i)^we provide\s+100\s*%\s+same\s*(?:&|and)\s*fine quality product as\s+show(?:n)?\s+in\s+(?:the\s+)?picture[.!]?\s*$'),
 re.compile(r'(?i)^we provide very reasonable prices as compared to other stores[.!]?\s*$'),
 re.compile(r'(?i)^(?:buy now|shop now|order now|subscribe|share|read more|product info|description|dsasd)[.!:]?\s*$'),
]
GENERIC=re.compile(r"(?i)^(?:.+?\s+is\s+(?:a|an)\s+(?:fragrance|hair colou?r|hair mask|hair condi?tioner|shalwar garment|denim jeans style|wrist\s*watch|decorative item for the named setting|footwear style)|a\s+(?:peshawari chappal|footwear)\s+style)[.!]?\s*$")
OPTION_LINE=re.compile(r'(?i)^(?:colou?r|size|shade|cup size|pack|stitching type|fit|inseam)\s*:\s*')
CODE=re.compile(r'^(?=.*\d)[A-Za-z0-9]+(?:[-_/.][A-Za-z0-9]+)+$')

class DescriptionCapacityError(ValueError):
 pass

def normalized(value):
 return re.sub(r'[^a-z0-9]+','',str(value or '').casefold())

def text(value):
 value=str(value or '')
 if re.search(r'</?[A-Za-z][^>]*>',value):
  from bs4 import BeautifulSoup
  soup=BeautifulSoup(value,'html.parser')
  for node in soup.select('script,style,noscript'):node.decompose()
  for br in soup.find_all('br'):br.replace_with('\n')
  for node in soup.find_all(['p','div','li','dt','dd','tr','h1','h2','h3','h4']):node.append('\n')
  value=soup.get_text(' ')
 return html.unescape(value).replace('\r\n','\n').replace('\r','\n')

def clean_prose(value):
 value=re.sub(r'[ \t]+',' ',str(value or '')).strip()
 fixes=[(r'\bgold platted\b','gold-plated'),(r'\bsilver platted\b','silver-plated'),
        (r'\bwill be deliverd\b','will be delivered'),(r'\bmix designs will be delivered\b','Mixed designs will be delivered'),
        (r'\bas show in (?:the )?picture\b','as shown in the picture'),
        (r'\bclean it with dry and soft cloth\b','Clean with a dry, soft cloth'),
        (r'\bclean it with a dry, soft cloth\b','Clean with a dry, soft cloth'),
        (r'\bkeep away from water perfume\b','Keep away from water, perfume'),
        (r'\bperfum\b','perfume'),(r'\bcondtioner\b','conditioner'),(r'\bEaring\b','earring'),(r'\bEarings\b','earrings')]
 for pattern,replacement in fixes:value=re.sub(pattern,replacement,value,flags=re.I)
 value=re.sub(r'(?i)\b(gold-plated|silver-plated)\s+(mala|pendant|necklace|bracelet|earrings?|bangles?|rings?)\b',lambda m:m[1].lower()+' '+m[2].lower(),value)
 value=re.sub(r'(?i)other chemicals\s+Clean\b','other chemicals. Clean',value)
 value=re.sub(r'(?i)^(.+?) brings a refined touch to your everyday fragrance routine\.\s*',lambda m:'Product: '+m[1]+'\n',value)
 value=re.sub(r'(?im)^Its generous (\d+(?:\.\d+)?\s*ml) size makes it a practical choice for regular wear, whether you.re heading out or enjoying a special occasion\.?$',lambda m:'Volume: '+m[1],value)
 value=re.sub(r'(?i)^Step into next-level comfort with the\s+','The ',value)
 value=re.sub(r'(?i)\bThe product photograph shows\s+','Shown: ',value)
 value=re.sub(r'(?i)\bThe photograph shows\s+','Shown: ',value)
 value=re.sub(r'(?i)^A sneaker footwear style with\s+','Sneakers with ',value)
 value=re.sub(r'(?i)^All items are packed in the\s+','Packed in a ',value)
 value=re.sub(r'(?i)^As a professional product designed by ([^,]+), the\s+',lambda m:m[1].strip()+' ',value)
 value=re.sub(r'(?i)\bprovides superior protection for colored hair\b','helps protect coloured hair',value)
 value=re.sub(r'(?i)\bFormulated with advanced ingredients, it preserves\b','It helps preserve',value)
 value=re.sub(r'(?i)\bKeep your colored hair vibrant and healthy with this expertly crafted conditioner\.?','Helps keep coloured hair vibrant and healthy.',value)
 value=re.sub(r'(?i)\bCOLOR PROTECT conditioner\b','Color Protect Conditioner',value)
 return value.strip()

def marker(line):
 cleaned=re.sub(r'^[\s✦📦📏🎨⚠️•*#\-]+','',line).strip().rstrip(':').strip()
 return ALIASES.get(cleaned.casefold())

def retained_text(value):
 """Approved cleanup baseline; substantive numbers/options are never discarded."""
 raw=text(value)
 raw=re.sub(r'(?m)^[ \t]*(?:✦|📦|📏|🎨|⚠️?)\s*','',raw)
 indices=[int(m[1]) for m in re.finditer(r'(?m)^\s*(\d+)[.)]\s+(?=[A-Za-z])',raw)]
 if len(indices)>=2 and indices==list(range(1,len(indices)+1)):
  raw=re.sub(r'(?m)^\s*\d+[.)]\s+(?=[A-Za-z])','',raw)
 # Separate known inline section headings without splitting ordinary prose.
 inline=['Key Features','Design Details','Product Highlights','How to Use','Care Instructions','Jewellery Care','Jewelry Care','Product Options','Pack Contents','Technical Specifications']
 for label in inline:
  raw=re.sub(r'(?<![\w])'+re.escape(label)+r'\s*:?\s*(?=[A-Z0-9]|$)', '\n'+label+':\n',raw)
 result=[];seen=set();in_options=False
 for line in raw.splitlines():
  line=re.sub(r'[ \t]+',' ',line).strip()
  if not line:
   if result and result[-1]!='':result.append('')
   continue
  line=re.sub(r'^[•]\s*','',line)
  promotional_line=re.sub(r'^\d+[.)]\s+','',line)
  if any(p.fullmatch(promotional_line) for p in BOILERPLATE):continue
  if line.startswith('Listing: '):line='Product: '+line[len('Listing: '):]
  heading=marker(line) or ALIASES.get(line.partition(':')[0].strip().casefold())
  if heading:in_options=heading=='options'
  if not in_options:line=clean_prose(line)
  identity=line.casefold()
  if identity in seen:continue
  seen.add(identity);result.append(line)
 return '\n'.join(result).strip()

def sections(value):
 raw=retained_text(value);groups=OrderedDict();current='overview';groups[current]=[]
 for line in raw.splitlines():
  if not line:continue
  found=marker(line)
  # Support a labelled source field with a value on the same line.
  left,sep,right=line.partition(':')
  if not found and sep:found=ALIASES.get(left.strip().casefold())
  # Computer storage is a specification, not an instruction to store goods.
  if sep and left.strip().casefold()=='storage' and re.search(r'(?i)\b(?:\d+\s*(?:tb|gb|mb)|ssd|hdd|emmc|nvme)\b',right):
   current='specifications';groups.setdefault(current,[]).append(line);continue
  if found:
   current=found;groups.setdefault(current,[])
   if sep and right.strip():groups[current].append(right.strip())
   continue
  fields={'material':'fabric','fabric type':'fabric','fit type':'fabric','length':'measurements','width':'measurements','height':'measurements','weight':'measurements','recommended age':'age','age':'age','suitable age':'age','sku':'specifications','model':'specifications','product code':'specifications'}
  if sep and left.strip().casefold() in fields:
   current=fields[left.strip().casefold()];groups.setdefault(current,[]).append(line);continue
  if line.startswith('Packed in a ') or re.match(r'(?i)^All items are packed in\b',line):
   groups.setdefault('packaging',[]).append(line);continue
  if current=='overview' and OPTION_LINE.match(line):
   current='options';groups.setdefault(current,[])
  if current=='overview' and CODE.fullmatch(line) and not re.search(r'\b(?:ml|kg|cm|mm|g|inches?|meters?|metres?)\b',line,re.I):
   groups.setdefault('specifications',[]).append('Product Code: '+line)
  else:groups.setdefault(current,[]).append(line)
 return groups

def body(value,name=''):
 groups=sections(value);parts=[]
 for key,lines in groups.items():
  if key in ('options','care','warnings','warranty','packaging'):continue
  for line in lines:
   if line.startswith(('Product:','Product Code:','SKU:')) or OPTION_LINE.match(line):continue
   if line.startswith('Model:') and not re.search(r'(?i)\b(?:wearing|height|chest|length|size)\b',line.partition(':')[2]):continue
   if normalized(line)==normalized(name):continue
   if GENERIC.fullmatch(line):continue
   parts.append(line)
 return '\n'.join(parts)

PURPOSE=re.compile(r'(?i)\b(?:camisoles?|tank tops?|hair\s*brush(?:es)?|chappals?|pendants?|necklaces?|malas?|earrings?|studs|bangles?|karas?|rings?|bracelets?|lipsticks?|lip colours?|nail polish|nail paint|hair masks?|perfumes?|fragrances?|wrist\s*watches?|bedsheets?|bed sheets?|adapter|controllers?|shirts?|trousers?|sandals?|shoes?)\b')
DISTINCTIVE=re.compile(r'(?i)\b(?:solid|printed|embroidered|beaded|layered|cushion(?:ed)?|peshawari|gold[ -]plated|silver[ -]plated|stainless steel|crystal|calligraphy|feather|cotton|polyester|matte|glitter|floral|wireless|bluetooth|sulphate[ -]free|sulfate[ -]free|argan oil|closed[ -]toe|open[ -]toe|low[ -]cut)\b')
MEASURE=re.compile(r'(?i)\b\d+(?:\.\d+)?\s*(?:ml|litres?|liters?|g|kg|cm|mm|inches?)\b')

def source_factual_summary(name,value):
 """Use only explicit source descriptors, never generic invented benefits."""
 raw=retained_text(value);context=str(name or '')+' '+raw
 colour=re.search(r'(?im)^colou?r\s*:\s*(black|white|brown|blue|red|green|pink|purple|grey|gray|beige|navy)\s*$',raw)
 colour=colour[1].lower() if colour else ''
 if re.search(r'(?i)\b(?:camisole|tank top)\b',context) and re.search(r'(?i)\bsolid\b',context):
  return 'A solid camisole'+(' in '+colour if colour else '')+'.'
 if re.search(r'(?i)\bcushion(?:ed)?\s+hair\s*brush\b',context):return 'A cushioned hairbrush.'
 if re.search(r'(?i)\bpeshawari\b',context) and re.search(r'(?i)\bchappal',context):
  audience="Men's " if re.search(r'(?i)\bmen\b',str(name)) else ''
  return audience+'Peshawari chappals'+(' in '+colour if colour else '')+'.'
 if re.search(r'(?i)\bhair mask\b',context) and re.search(r'(?i)\bargan oil\b',context) and re.search(r'(?i)\bsul(?:ph|f)ate[ -]free\b',context):return 'A sulphate-free hair mask with argan oil.'
 if re.search(r'(?i)\bmatte\b',context) and re.search(r'(?i)\blipstick\b',context):return 'A matte lipstick.'
 volume=re.search(r'(?i)\b\d+(?:\.\d+)?\s*ml\b',context)
 if volume and re.search(r'(?i)\bperfume\b',context):
  audience="men's " if re.search(r'(?i)\b(?:pour homme|for men)\b',context) else "women's " if re.search(r'(?i)\bfor (?:women|ladies)\b',context) else ''
  kind='eau de parfum' if re.search(r'(?i)\beau de parfum\b',context) else 'perfume'
  return ('An ' if kind=='eau de parfum' and not audience else 'A ')+audience+kind+' in a '+volume[0]+' size.'
 return None

def completeness_issues(value,name=''):
 useful=body(value,name)
 if not useful or len(re.findall(r'\b\w+\b',useful))<5:
  summary=source_factual_summary(name,value)
  useful=summary or useful
  quantity=re.search(r'(?i)\b(?:set|pack)\s+of\s+\d+\b',useful)
  specific=bool(useful and PURPOSE.search(useful+' '+str(name)) and (DISTINCTIVE.search(useful) or MEASURE.search(useful) or quantity))
  if not specific:return ['Description lacks product-specific detail beyond name, code, care and options']
 if len(str(value or ''))>=32767:return ['Description exceeds Excel cell capacity']
 return []

def sentence(value):
 value=clean_prose(value)
 if value and value[0].islower():value=value[0].upper()+value[1:]
 if value and not re.search(r'[.!?:;]$',value):value+='.'
 return value

def paragraphs(value):
 # Wrap between complete sentences; no overall word/character target or lost facts.
 sentences=re.split(r'(?<!\d\.)(?<=[.!?])\s+(?=[A-Z])',value)
 result=[];group=[];words=0
 for item in sentences:
  size=len(item.split())
  if group and words+size>85:result.append(' '.join(group));group=[];words=0
  group.append(item);words+=size
 if group:result.append(' '.join(group))
 return '\n\n'.join(result)

def render_description(value,name='',category=''):
 groups=sections(value);overview=groups.pop('overview',[])
 # Keep exact named identity/codes as details; never pad a weak description.
 lead=[];identity=[]
 for line in overview:
  if normalized(line)==normalized(name) or line.startswith('Product:'):
   if re.search(r'\d',line):identity.append(line if line.startswith('Product:') else 'Product: '+line)
   continue
  if GENERIC.fullmatch(line):
   # Redundant category statements add no facts. Keep any numeric identity.
   if re.search(r'\d',line):identity.append('Product: '+re.sub(r'(?i)\s+is\s+(?:a|an)\s+.+$','',line))
   continue
  lead.append(line)
 if identity:groups.setdefault('specifications',[]).extend(identity)
 if len(re.findall(r'\b\w+\b',body(value,name)))<5:
  summary=source_factual_summary(name,value)
  if summary:lead=[summary]
 # Combine only design words explicitly present in the exact source title.
 if lead and re.fullmatch(r'(?i)gold-plated mala[.]?',lead[0]):
  design=[]
  if re.search(r'(?i)\blayer(?:ed)?\b',name):design.append('layered')
  if re.search(r'(?i)\bbeaded\b',name):design.append('beaded')
  if design:lead[0]='A gold-plated mala with a '+', '.join(design)+' design.'
 # A one-line fragment can be expressed as a natural factual sentence.
 if lead and not re.search(r'[.!?]',lead[0]) and len(lead[0].split())<=12 and not re.search(r':|\d',lead[0]):
  if not re.match(r'(?i)^(?:a|an|the|these|this|with|includes?|made|suitable|designed|keep|wash|apply|use|avoid|do not)\b',lead[0]):
   first=lead[0];article='An' if first[:1].lower() in 'aeiou' else 'A'
   lead[0]=article+' '+first[:1].lower()+first[1:]
 # Preserve paragraph/sentence meaning and put line-based facts in readable bullets.
 output=[]
 if lead:
  if len(lead)>1 and len(lead[0].split())<15 and all(len(x.split())<30 for x in lead[1:]):
   output.append(sentence(lead[0]));groups['details']=lead[1:]+groups.get('details',[])
  else:output.append('\n\n'.join(paragraphs(sentence(x)) for x in lead))
 for key,label in HEADINGS.items():
  lines=groups.get(key,[])
  if not lines:continue
  cleaned=[];seen=set()
  for line in lines:
   line=line.strip() if key=='options' else clean_prose(line)
   if not line or line.casefold() in seen:continue
   seen.add(line.casefold())
   if key=='options':cleaned.append('• '+line) # source option values stay verbatim
   else:
    # Expose source numbered directions and dense feature labels as separate lines.
    pieces=re.split(r'(?<!\d\.)(?<=[.!?])\s+(?=[A-Z])|\s+(?=Step\s+\d+\s*[:.])',line)
    cleaned.extend('• '+sentence(piece) for piece in pieces if piece.strip())
  if cleaned:output.append(label+'\n'+'\n'.join(cleaned))
 result='\n\n'.join(output).strip()
 if len(result)>=32767:raise DescriptionCapacityError('Description exceeds Excel cell capacity; original facts must be retained outside the sellable export')
 return result

def numeric_facts(value):
 return set(re.findall(r'\d+(?:[.,]\d+)?',retained_text(value)))

def overview_matches(value,overview):
 # Formatting/punctuation must not break an existing identity/hash-bound review.
 simplify=lambda s:re.sub(r'[^a-z0-9]+','',clean_prose(s).casefold())
 return simplify(body(value)).startswith(simplify(overview))
