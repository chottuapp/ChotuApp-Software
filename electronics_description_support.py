"""Source-only electronics layout and conservative warranty extraction."""
import re
from bs4 import BeautifulSoup

STORES={'Computer Zone','Xcessories Hub','Zero Lifestyle','Prime Ticks'}
def electronic(store,category=''):
 return store in STORES or bool(re.search(r'\b(?:laptop|computer|earbuds?|headphones?|speakers?|chargers?|power banks?|smartwatches?|tablets?|monitors?|keyboards?|cameras?|routers?|usb hubs?|docking stations)\b',str(category),re.I))

def html_text(value):
 soup=BeautifulSoup(value or '', 'html.parser')
 for node in soup.select('script,style,noscript'):node.decompose()
 for node in soup.select('br'):node.replace_with('\n')
 for node in soup.select('p,div,li,h1,h2,h3,h4,tr,section'):
  node.insert_before('\n');node.insert_after('\n')
 return '\n'.join(re.sub(r'[ \t]+',' ',line).strip() for line in soup.get_text(' ',strip=False).splitlines() if line.strip())

def warranty_months(value):
 """No duration guessed from returns, lifetime promises or conflicting terms."""
 values=[]
 for match in re.finditer(r'\b(\d+)\s*[- ]?\s*(year|month)s?\s+(?:(?:official|brand|manufacturer|seller|limited|international)\s+){0,3}warranty\b|\bwarranty\s*[:–-]\s*(\d+)\s*(year|month)s?\b',str(value),re.I):
  number,unit=(match[1],match[2]) if match[1] else (match[3],match[4]);values.append(int(number)*(12 if unit.lower()=='year' else 1))
 return values[0] if values and len(set(values))==1 and values[0]>0 else ''

def warranty_attributes(product):
 result=[]
 for attribute in product.get('attributes',[]):
  if not re.fullmatch(r'(?:product\s+)?warranty',str(attribute.get('name','')).strip(),re.I):continue
  values=[str(t.get('name','')).strip() for t in attribute.get('terms',[]) if t.get('name')]
  if values:result.append('Warranty: '+', '.join(values))
 return '\n'.join(result)

def warranty_panels(soup):
 """Only labelled product tabs/attributes; never footer or store-wide promises."""
 result=[]
 for row in soup.select('table.woocommerce-product-attributes tr'):
  label=row.select_one('th');value=row.select_one('td')
  if label and value and re.fullmatch(r'warranty',label.get_text(' ',strip=True),re.I):result.append('Warranty: '+value.get_text(' ',strip=True))
 for panel in soup.select('.woocommerce-Tabs-panel, product-info details, [id^="ProductInfo"] details, .product__info-container details, [data-product-warranty]'):
  heading=panel.select_one('summary,h2,h3,h4')
  if panel.has_attr('data-product-warranty') or heading and re.search(r'\bwarranty\b',heading.get_text(' ',strip=True),re.I):
   fragment=BeautifulSoup(str(panel),'html.parser')
   for node in fragment.select('script,style,form,button,nav'):node.decompose()
   result.append(html_text(str(fragment)))
 return '\n'.join(dict.fromkeys(result))

def format_electronics(value,months=None):
 text=str(value or '').replace('\r\n','\n').replace('\r','\n')
 text=re.sub(r'\bExclusively at\s+[a-z0-9.-]+\.(?:com|pk)\b','',text,flags=re.I)
 text=re.sub(r'(?im)^\s*(?:Weight|Dimensions)\s*:\s*N/?A\s*$','',text)
 # Recover flattened feature labels without splitting decimal points or units.
 labels=r'(?:PitaTap™ Camera Control|Aerospace-Grade Aramid Fiber|Ultra-Thin and Lightweight Design|Mammoth Resin™ Reinforcement|100% MagSafe Compatible|Scratch-Resistant Construction|Ultra-Slim Thickness|Feather-Light Weight|Dimensions|Weight|Battery Capacity|Rated Capacity|Capacity|Input|Output|Compatibility|Material|Warranty|In the Box|Package Contents|Care|Caution|Warning)'
 text=re.sub(r'(?<!^)(?<!\n)\s+(?='+labels+r'\s*:)', '\n',text,flags=re.I)
 lines=[]
 for line in text.splitlines():
  line=line.strip()
  if not line:continue
  # Decimal values, abbreviations and list measurements remain untouched.
  lines.extend(re.split(r'(?<=[.!?])\s+(?=[A-Z])',line))
 blocks=[];section=None
 if lines and len(lines[0].split())<=85 and not re.match(r'^(?:[-•]|Warranty\b|Specifications\b|Key features\b)',lines[0],re.I):blocks.append(lines.pop(0)+'\n')
 for line in lines:
  if not line:continue
  if line in ('Key features','Specifications','Warranty','Product details'):continue
  warranty=bool(re.search(r'\bwarranty\b',line,re.I))
  wanted='Warranty' if warranty else 'Specifications' if re.search(r'^(?:Dimensions|Weight|Ultra-Slim Thickness|Feather-Light Weight|Battery Capacity|Rated Capacity|Input|Output|Material|Capacity)\s*:',line,re.I) else 'Key features'
  if section!=wanted:blocks.append('\n'+wanted+'\n');section=wanted
  blocks.append('- '+re.sub(r'^[-•]\s+','',line).strip())
 if months and not re.search(r'\bwarranty\b',text,re.I):blocks.extend(['\nWarranty\n','- '+str(months)+' months warranty (source-listed).'])
 return '\n'.join(blocks).strip()
