"""Owner-locked retailer branding removal; commercial/source identities stay intact."""
import html,re
from urllib.parse import urlsplit
from bs4 import BeautifulSoup
HOST='barkatmeathouse.com'
NAME=re.compile(r'\bbarkat(?:[\x27’]s)?[\s_-]*meat[\s_-]*house\b',re.I)
DOMAIN=re.compile(r'(?:https?://)?(?:www\.)?barkatmeathouse\.com/?',re.I)

def applies(url):return (urlsplit(str(url or '')).hostname or '').casefold().removeprefix('www.')==HOST

def plain(value):
 text=html.unescape(str(value or ''))
 return BeautifulSoup(text,'html.parser').get_text('\n',strip=True) if re.search(r'<[/a-zA-Z]',text) else text

def clean(value):
 text=plain(value)
 text=DOMAIN.sub('',text);text=re.sub(r'\b(?:by|from|at)\s+(?='+NAME.pattern+r')','',text,flags=re.I);text=NAME.sub('',text)
 text=re.sub(r'[ \t]+',' ',text);text=re.sub(r' +([,.;:])',r'\1',text)
 text=re.sub(r'\n{3,}','\n\n',text)
 text=text.strip()
 text=re.sub(r'\s+[-|–—:]$','',text)
 return re.sub(r'^[|–—:]\s+','',text).strip()

def customer_fields(url,title,description):
 if not applies(url):return dict(name=title,description=description)
 return dict(name=clean(title),description=clean(description),original_source_title=str(title or ''),original_source_description=str(description or ''),retailer_branding_rule='Owner lock: retailer name omitted from title and description; original source retained')

def issues(row):
 if not applies(row.get('source_url')):return []
 if any(NAME.search(plain(row.get(k))) or DOMAIN.search(plain(row.get(k))) for k in ('name','description')):return ['Owner retailer branding lock violated in product title/description']
 return []
