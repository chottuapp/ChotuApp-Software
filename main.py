import tempfile
import sys
import subprocess
"""ChotuApp Extractor - Shopify public catalog refresh tool."""
import os, re, json, time, hashlib, threading, queue, html, shutil, csv, datetime
from pathlib import Path
from decimal import Decimal, InvalidOperation
from urllib.parse import urlparse, urljoin, urlsplit, urlunsplit, parse_qsl, urlencode
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import requests

# CHOTUAPP_MANUAL_RESUME_CHECKPOINT_V1
# Persist successful API responses only for the current run. Every newly
# started fetch uses a new database and never replays an earlier run.
import sqlite3
import zlib
_chotu_tls = threading.local()
_chotu_pause_gate = threading.Event()
_chotu_pause_gate.set()

class ChotuRateLimited(RuntimeError):
    pass

def _chotu_wait():
    _chotu_pause_gate.wait()

# CHOTUAPP_PAUSE_RATE_LIMIT_RESPONSIVE_V1
def _chotu_backoff(seconds, reason='Retry'):
    deadline = time.monotonic() + max(0, float(seconds))
    while True:
        _chotu_wait()
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return
        if reason == 'Rate limit':
            secs = int(remaining + .99)
            if secs % 5 == 0 or secs <= 3:
                _chotu_debug('RATE LIMIT: retry in ' + str(secs) + 's (manual Pause available)')
        time.sleep(min(1.0, remaining))


def _chotu_open_checkpoint(base, name):
    safe = re.sub(r'[^\w .-]', '', name).strip() or 'Shopify'
    identity = hashlib.sha256((base.rstrip('/') + '|' + name).encode()).hexdigest()[:14]
    folder = Path(__file__).resolve().parent / 'resume_checkpoints'
    folder.mkdir(parents=True, exist_ok=True)
    # Each fetch owns a new database. Older failed-run checkpoints are never
    # replayed into a fresh catalog, price or availability run.
    descriptor, filename = tempfile.mkstemp(prefix=safe + '-' + identity + '-fresh-', suffix='.sqlite3', dir=folder)
    os.close(descriptor)
    path = Path(filename)
    db = sqlite3.connect(str(path), timeout=30)
    db.execute('CREATE TABLE IF NOT EXISTS responses (url TEXT PRIMARY KEY, payload BLOB NOT NULL)')
    db.commit()
    _chotu_tls.db = db
    _chotu_tls.checkpoint_path = path
    return path

def _chotu_close_checkpoint(success=False):
    db = getattr(_chotu_tls, 'db', None)
    path = getattr(_chotu_tls, 'checkpoint_path', None)
    _chotu_tls.db = None
    _chotu_tls.checkpoint_path = None
    if db is not None:
        db.close()
    if success and path is not None:
        try:
            path.unlink(missing_ok=True)
        except OSError:
            pass

# CHOTUAPP_LIVE_DEBUG_V1
import traceback as _chotu_traceback
import urllib.parse as _chotu_urlparse
_chotu_debug_lock = threading.Lock()
_chotu_debug_state = {'stage': 'Idle', 'request': '', 'started': 0.0, 'attempt': 0}
_chotu_debug_sink = None

def _chotu_debug(message):
    global _chotu_debug_sink
    stamp = datetime.datetime.now().strftime('%H:%M:%S')
    line = '[' + stamp + '] ' + str(message)
    sink = _chotu_debug_sink
    if sink is not None:
        try: sink(line)
        except Exception: pass

def _chotu_debug_stage(stage):
    with _chotu_debug_lock:
        _chotu_debug_state['stage'] = stage
    _chotu_debug('STAGE: ' + stage)

def _chotu_debug_request(url, attempt):
    with _chotu_debug_lock:
        _chotu_debug_state.update(request=url, started=time.monotonic(), attempt=attempt)
    _chotu_debug('HTTP START attempt=' + str(attempt) + ' ' + url)

def _chotu_debug_response(status, size=0, cached=False):
    with _chotu_debug_lock:
        started = _chotu_debug_state['started']
        url = _chotu_debug_state['request']
        _chotu_debug_state.update(request='', started=0.0)
    duration = (time.monotonic() - started) if started else 0
    _chotu_debug(('CACHE HIT ' if cached else 'HTTP END ') + 'status=' + str(status) + ' elapsed=' + format(duration, '.1f') + 's bytes=' + str(size) + ' ' + url)

from bs4 import BeautifulSoup
from openpyxl import load_workbook

HOME = Path(os.environ.get('CHOTUAPP_DATA_DIR', str(Path.home() / 'Desktop')))
OUT = HOME / 'ANAS_DATA_FETCH'
CONFIG = HOME / 'chotuapp_extractor_sites.json'
HEADERS = {'User-Agent': 'Mozilla/5.0 (compatible; ChotuAppCatalogRefresh/1.0)',
           'Cache-Control': 'no-cache', 'Pragma': 'no-cache'}
S = requests.Session(); S.headers.update(HEADERS)

# CHOTUAPP_ADAPTIVE_SPEED_V4
# Respect site throttling. Cached requests never hit the network.
def get_json(url, tries=4):
    import email.utils
    _chotu_debug('GET_JSON: ' + url)
    _chotu_wait()
    db = getattr(_chotu_tls, 'db', None)
    if db is not None:
        cached = db.execute('SELECT payload FROM responses WHERE url=?', (url,)).fetchone()
        if cached is not None:
            _chotu_debug('CACHE HIT: ' + url)
            return json.loads(zlib.decompress(cached[0]).decode('utf-8'))
    for n in range(tries):
        _chotu_wait()
        # One network request at a time in the existing extraction worker.
        # Gradually slow down after 429, gently recover after successful requests.
        pace = getattr(_chotu_tls, 'adaptive_pace', 1.5)
        previous = getattr(_chotu_tls, 'adaptive_last_request', 0.0)
        remaining = previous + pace - time.monotonic()
        if remaining > 0:
            _chotu_backoff(remaining, 'Adaptive pacing')
        _chotu_wait()
        _chotu_tls.adaptive_last_request = time.monotonic()
        try:
            _chotu_debug_request(url, n + 1)
            try:
                r = S.get(url, timeout=35)
            except Exception:
                _chotu_debug_response('EXCEPTION')
                raise
            _chotu_debug_response(r.status_code, len(r.content))
            if r.status_code in (403, 404):
                raise RuntimeError(f'Website endpoint unavailable ({r.status_code}): {url}')
            if r.status_code in (429, 503):
                _chotu_tls.adaptive_pace = min(12.0, max(2.5, pace * 1.8))
                retry_after = r.headers.get('Retry-After', '').strip()
                delay = min(90, 12 * (2 ** n))
                if retry_after:
                    try:
                        parsed = float(retry_after)
                    except ValueError:
                        try:
                            dt = email.utils.parsedate_to_datetime(retry_after)
                            parsed = (dt - datetime.datetime.now(datetime.timezone.utc)).total_seconds()
                        except (TypeError, ValueError, OverflowError):
                            parsed = 0
                    delay = max(delay, parsed)
                if n == tries - 1 or delay > 120:
                    raise ChotuRateLimited(f'HTTP {r.status_code} rate limit at {url}; checkpoint preserved. Retry later.')
                _chotu_debug(f'ADAPTIVE SPEED: HTTP {r.status_code}; pace={_chotu_tls.adaptive_pace:.1f}s; cooldown={delay:.0f}s')
                _chotu_backoff(delay, 'Rate limit')
                continue
            r.raise_for_status()
            data = r.json()
            _chotu_tls.adaptive_pace = max(1.5, pace * 0.95)
            if db is not None:
                blob = sqlite3.Binary(zlib.compress(json.dumps(data, ensure_ascii=False, separators=(',', ':')).encode('utf-8'), 5))
                db.execute('INSERT OR REPLACE INTO responses(url,payload) VALUES (?,?)', (url, blob))
                db.commit()
            return data
        except ChotuRateLimited:
            raise
        except (requests.RequestException, ValueError) as exc:
            if n == tries - 1:
                raise RuntimeError(f'Network/JSON error: {exc}') from exc
            _chotu_backoff(n + 1, 'Network retry')
    raise ChotuRateLimited('Rate limit; checkpoint preserved. Retry later')



def txt(v):
    # CHOTUAPP_TEXT_FAST_V1: plain strings need no HTML tree.
    value=str(v or '')
    if '<' not in value and '&' not in value:
        return re.sub(r'\s+', ' ', value).strip()
    return re.sub(r'\s+', ' ', html.unescape(BeautifulSoup(value, 'html.parser').get_text(' ', strip=True))).strip()

def money(v):
    try:
        value = Decimal(str(v)).quantize(Decimal('0.01'))
        return value if value.is_finite() and value >= 0 else None
    except (InvalidOperation, TypeError, ValueError):
        return None


def uid(prefix, key): return prefix + hashlib.sha256(str(key).encode()).hexdigest()[:12]

def discover(base, log):
    _chotu_debug_stage('Discover catalog')
    """Collect catalog, then use collection-scoped pagination for large Shopify stores.
    Never silently treat Shopify's 100-page ceiling as catalog completion.
    """
    items = {}; hit_limit = False
    for page in range(1, 101):
        batch = get_json(f'{base}/products.json?limit=250&page={page}').get('products', [])
        for product in batch:
            if product.get('id') is not None:
                items[product['id']] = product
        log(f'  Catalog page {page}: {len(batch)} records')
        if len(batch) < 250:
            return list(items.values()), True
        if getattr(_chotu_tls, 'db', None) is None: time.sleep(.10)
    hit_limit = True
    log('  Shopify 100-page ceiling reached; trying collection-scoped discovery...')
    collections_found = []
    try:
        for page in range(1, 101):
            batch = get_json(f'{base}/collections.json?limit=250&page={page}').get('collections', [])
            collections_found.extend(c for c in batch if c.get('handle'))
            if len(batch) < 250: break
        else:
            log('  WARNING: Collections listing also reached 100-page ceiling')
            return list(items.values()), False
    except ChotuRateLimited as exc:
        # CHOTUAPP_STYLO_429_GRACEFUL_REVIEW_V1
        if (urlparse(base).hostname or '').lower().removeprefix('www.') == 'stylo.pk':
            _chotu_tls.stylo_collections_rate_limited = True
            log('  STYLO RATE LIMITED: collections endpoint blocked; preserving cached products as INCOMPLETE REVIEW, not FINAL.')
            log('  STYLO DETAIL: ' + str(exc))
            return list(items.values()), False
        raise
    except Exception as exc:
        log(f'  WARNING: Could not enumerate collections: {exc}')
        return list(items.values()), False
    complete_collections = True
    added = 0
    for ix, c in enumerate(collections_found, 1):
        handle = c['handle']
        for page in range(1, 101):
            try:
                batch = get_json(f'{base}/collections/{handle}/products.json?limit=250&page={page}').get('products', [])
            except ChotuRateLimited:
                raise
            except Exception as exc:
                complete_collections = False
                log(f'  Collection {handle} failed: {exc}')
                break
            for product in batch:
                pid = product.get('id')
                if pid is not None and pid not in items:
                    items[pid] = product
                    added += 1
            if len(batch) < 250: break
        else:
            complete_collections = False
            log(f'  Collection {handle} reached 100-page ceiling')
        if ix % 20 == 0:
            log(f'  Collections processed: {ix}/{len(collections_found)}; additional products: {added}')
    log(f'  Collection discovery: {len(items)} unique records; {added} beyond initial 25,000')
    # Collection membership cannot guarantee inclusion of uncollected products.
    # Mark as unproven even if every collection paginated successfully.
    return list(items.values()), False

def collections(base, log):
    _chotu_debug_stage('Collection/category mapping')
    mapping={}
    seen_handles=set(); skipped_empty=0; fetched=0
    try:
        for page in range(1, 30):
            _chotu_debug('CATEGORY LIST page ' + str(page))
            data=get_json(f'{base}/collections.json?limit=250&page={page}')
            batch=data.get('collections', [])
            if not batch: break
            for c in batch:
                handle=c.get('handle'); title=txt(c.get('title'))
                if not handle or not title or handle in seen_handles: continue
                seen_handles.add(handle)
                # Empty collections cost a request each and add nothing; skip when the store reports a zero count.
                if c.get('products_count') == 0:
                    skipped_empty += 1
                    continue
                fetched += 1
                if fetched % 25 == 0:
                    log(f'  Category mapping: {fetched} collections fetched, {skipped_empty} empty skipped, {len(mapping)} products mapped')
                _chotu_debug('CATEGORY COLLECTION: ' + handle)
                for pageno in range(1, 30):
                    _chotu_wait()
                    try: ps=get_json(f'{base}/collections/{handle}/products.json?limit=250&page={pageno}').get('products',[])
                    except ChotuRateLimited: raise
                    except RuntimeError: break
                    for p in ps: mapping.setdefault(p.get('id'),[]).append(title)
                    if len(ps)<250: break
            if len(batch)<250: break
        log(f'  Collection categories mapped: {len(mapping)} products ({skipped_empty} empty collections skipped)')
    except ChotuRateLimited as exc:
        # Category mapping is optional: keep what we have and force REVIEW instead of failing the whole store.
        log(f'  Collection categories mapped: {len(mapping)} products (partial)')
        log('  Category mapping INCOMPLETE: rate limited; using product type/title fallback for the rest. ' + str(exc))
    except RuntimeError as exc: log(f'  Collections incomplete: {exc}')
    return mapping

# CHOTUAPP_FRIENDLY_CATALOG_V1
# Content-only formatting: prices, variants, option names/values, SKU and images are untouched.
# CHOTUAPP_CONSOLIDATED_QUALITY_V1
# Only category and short description presentation; never alters Shopify facts.
# CHOTUAPP_CATEGORY_DESCRIPTION_QUALITY_V2
# Source-grounded categories: clothing never classified by beauty keyword fragments.

# Medium-length description: prefer original source wording; no invented features.

# CHOTUAPP_PRICE_AUDIT_V1
# Read-only cross-endpoint verification. Does not change prices or variants.
def shopify_minor_price(value):
    amount = Decimal(str(value))
    if not amount.is_finite() or amount < 0 or amount != amount.to_integral_value():
        raise ValueError('Invalid Shopify minor-unit price')
    return amount / Decimal('100')


def refresh_variant_prices(base, product, log):
    # Product.js uses minor units, unlike products.json decimal rupees.
    # Stage the complete response before changing the source product.
    if getattr(_chotu_tls, 'price_throttled', False):
        raise ChotuRateLimited('Live price checks paused after source rate limit')
    try:
        live = get_json(base.rstrip('/') + '/products/' + product['handle'] + '.js')
    except ChotuRateLimited:
        _chotu_tls.price_throttled = True
        raise
    if live.get('currency') and str(live['currency']).upper() != 'PKR':
        raise ValueError('Source currency is not PKR: ' + str(live['currency']))
    if str(live.get('id')) != str(product.get('id')):
        raise ValueError('Product.js identity does not match catalog product')
    source = {str(v['id']): v for v in product.get('variants', []) if v.get('id') is not None}
    variants, ids = [], set()
    changed = 0
    for current in live.get('variants', []):
        vid = str(current.get('id') or '')
        if not vid or vid in ids or not isinstance(current.get('available'), bool):
            raise ValueError('Missing/duplicate variant identity or unknown availability')
        ids.add(vid)
        variant = dict(source.get(vid, {}))
        variant.update(current)
        price = shopify_minor_price(current['price'])
        compare = shopify_minor_price(current['compare_at_price']) if current.get('compare_at_price') is not None else None
        previous = source.get(vid, {})
        if money(previous.get('price')) != price or money(previous.get('compare_at_price')) != compare:
            changed += 1
        variant['price'] = str(price)
        variant['compare_at_price'] = str(compare) if compare is not None else None
        variants.append(variant)
    if not variants:
        raise ValueError('Product.js returned no variants')
    product['variants'] = variants
    options = live.get('options')
    if isinstance(options, list) and all(isinstance(o, dict) for o in options):
        product['options'] = options
    log('LIVE VARIANT PRICES: ' + txt(product.get('title')) + ' — ' + str(len(variants)) + ' checked; ' + str(changed) + ' refreshed')
    return variants


def audit_fractional_prices(base, rows, combos, output, log):
    from urllib.parse import urlparse
    by_product = {}
    for c in combos:
        by_product.setdefault(c.get('product_id'), []).append(c)
    findings = []
    checked = 0
    for r in rows:
        _chotu_wait()
        bp = money(r.get('base_price (PKR)'))
        sp = money(r.get('sale_price (PKR, agar discount ho)'))
        checked += 1
        url = r.get('source_url') or ''
        try:
            handle = urlparse(url).path.rstrip('/').split('/')[-1]
            if getattr(_chotu_tls, 'price_throttled', False):
                raise ChotuRateLimited('Source rate limited; remaining price verification deferred')
            live = get_json(f"{base}/products/{handle}.js")
            live_variants = {str(v.get('id')): v for v in live.get('variants', [])}
            if not live_variants:
                findings.append(('REVIEW', url, '', 'NO_LIVE_VARIANTS', '', '', 'Product .js endpoint returned no variants'))
                continue
            for c in by_product.get(r['product_id'], []):
                vid = str(c.get('source_variant_id') or '')
                current = live_variants.get(vid)
                if current is None:
                    findings.append(('REVIEW', url, vid, 'VARIANT_MISSING', '', '', 'Variant absent from current product.js'))
                    continue
                # Shopify product.js amounts are integer minor currency units (cents/paisa).
                try:
                    live_price = (Decimal(str(current['price'])) / Decimal('100')).quantize(Decimal('0.01'))
                    live_compare = (Decimal(str(current['compare_at_price'])) / Decimal('100')).quantize(Decimal('0.01')) if current.get('compare_at_price') is not None else None
                except (InvalidOperation, TypeError, ValueError, KeyError) as exc:
                    findings.append(('REVIEW', url, vid, 'UNREADABLE_LIVE_PRICE', '', '', str(exc)))
                    continue
                expected_base = live_compare if live_compare is not None and live_compare > live_price else live_price
                expected_sale = live_price if expected_base > live_price else None
                exported_base = money(c.get('base_price (PKR)'))
                exported_sale = money(c.get('sale_price (PKR, agar discount ho)'))
                if exported_base != expected_base or exported_sale != expected_sale:
                    findings.append(('MISMATCH', url, vid, 'VARIANT_PRICE_DIFFERENCE', f'{exported_base} / {exported_sale}', f'{expected_base} / {expected_sale}', 'Export base/sale vs current product.js base/sale'))
            if not any(x[1] == url for x in findings):
                findings.append(('CHECKED', url, '', 'API_PRICES_MATCH', '', '', 'Current product.js variants agree; storefront display and checkout NOT verified'))
        except Exception as exc:
            findings.append(('REVIEW', url, '', 'FETCH_FAILED', '', '', str(exc)))
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('w', encoding='utf-8-sig', newline='') as f:
        w=csv.writer(f)
        w.writerow(['status','product_url','source_variant_id','check','export_base_sale','current_api_base_sale','detail'])
        w.writerows(findings)
    problems=sum(x[0] in ('REVIEW','MISMATCH') for x in findings)
    log(f'PRICE AUDIT: {output} ({checked} products checked; {problems} review/mismatch rows)')
    log('PRICE AUDIT NOTE: product.js is a second Shopify API endpoint, NOT visual storefront/checkout verification. No prices changed.')

# CHOTUAPP_STOREFRONT_AUDIT_V1
# Website's static price markup is not guaranteed to equal JS-rendered/cart/checkout price.
# CHOTUAPP_RATE_LIMIT_SAFETY_V2
def storefront_price_audit(rows, output, log):
    # HTTP 429 is an incomplete verification, never a confirmed price mismatch.
    import email.utils
    import random
    from decimal import Decimal as _Decimal
    from bs4 import BeautifulSoup as _Soup
    findings = []
    checked = 0
    session = requests.Session()
    session.headers.update(HEADERS)
    for r in rows:
        _chotu_wait()
        base = money(r.get('base_price (PKR)'))
        sale = money(r.get('sale_price (PKR, agar discount ho)'))
        if not any(x is not None and x != x.to_integral_value() for x in (base, sale)):
            continue
        checked += 1
        url = r.get('source_url') or ''
        try:
            resp = None
            for attempt in range(2):  # One initial request and at most one retry.
                resp = session.get(url, timeout=25)
                if resp.status_code not in (429, 503):
                    break
                if attempt == 0:
                    retry_header = resp.headers.get('Retry-After', '')
                    delay = 8.0
                    if retry_header:
                        try:
                            delay = float(retry_header)
                        except ValueError:
                            try:
                                dt = email.utils.parsedate_to_datetime(retry_header)
                                delay = (dt - datetime.datetime.now(datetime.timezone.utc)).total_seconds()
                            except (TypeError, ValueError, OverflowError):
                                pass
                    if delay > 30:
                        log('  Server requested a long retry delay; deferring verification instead.')
                        break
                    delay = max(3.0, delay)
                    log(f'  HTTP {resp.status_code} for {url}; waiting {delay:.0f}s before one retry')
                    _chotu_backoff(delay, 'Storefront retry')
            if resp.status_code in (429, 503):
                findings.append(['RATE_LIMITED', url, str(resp.status_code), str(base), str(sale), '',
                                 'Storefront verification deferred; API price unchanged; NOT a mismatch'])
                log(f'  RATE LIMITED: {url} (HTTP {resp.status_code}); verification pending')
                # Avoid further page requests when the site is throttling.
                break
            if resp.status_code != 200:
                findings.append(['REVIEW', url, str(resp.status_code), str(base), str(sale), '',
                                 'HTTP status not 200; verification pending'])
                continue
            soup = _Soup(resp.text, 'html.parser')
            nodes = soup.select('.price-item--sale, .price-item--regular, .price-item')
            values = []
            for node in nodes[:16]:
                match = re.search(r'(?:Rs\.?|PKR\s*)([\d,]+(?:\.\d+)?)',
                                  node.get_text(' ', strip=True), re.I)
                if match:
                    value = _Decimal(match.group(1).replace(',', ''))
                    if value not in values:
                        values.append(value)
            if not values:
                findings.append(['REVIEW', url, '200', str(base), str(sale), '',
                                 'No recognizable theme price; do not infer'])
                continue
            active = sale if sale is not None else base
            display = active.quantize(_Decimal('1')) if active is not None else None
            if active in values:
                status = 'EXACT_DISPLAY_MATCH'
            elif display in values:
                status = 'DISPLAY_WHOLE_RUPEE_MATCH'
            else:
                status = 'REVIEW'
            findings.append([status, url, '200', str(base), str(sale),
                             ' / '.join(map(str, values)),
                             'Static HTML only; checkout and JS changes not verified'])
            _chotu_backoff(0.5, 'Storefront pacing')
        except requests.RequestException as exc:
            findings.append(['REVIEW', url, '', str(base), str(sale), '',
                             'Network failure: ' + str(exc)[:140]])
        except Exception as exc:
            findings.append(['REVIEW', url, '', str(base), str(sale), '', str(exc)[:180]])
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('w', encoding='utf-8-sig', newline='') as fh:
        w = csv.writer(fh)
        w.writerow(['status', 'product_url', 'http_status', 'api_base',
                    'api_sale', 'html_price_values', 'note'])
        w.writerows(findings)
    reviews = sum(x[0] in ('REVIEW', 'RATE_LIMITED') for x in findings)
    log(f'STOREFRONT AUDIT: {output} ({checked} fractional-price products; '
        f'{reviews} pending/review; {sum(x[0] == "RATE_LIMITED" for x in findings)} rate limited)')
    log('STOREFRONT NOTE: HTML is not checkout; no source or exported prices changed.')
    return {x[1] for x in findings
            if x[0] in ('EXACT_DISPLAY_MATCH', 'DISPLAY_WHOLE_RUPEE_MATCH')}

def discount_export_fields(vals):
    # CHOTUAPP_DISCOUNT_FIELDS_V1: additive export fields, never change prices.
    from decimal import Decimal, ROUND_HALF_UP
    result = dict(vals)
    base = money(vals.get('base_price (PKR)'))
    sale = money(vals.get('sale_price (PKR, agar discount ho)'))
    result.update({'discount_percentage (%)': None, 'discount_tag': None,
                   'discount_tag_source': None, 'source_discount_tag': None})
    if base is not None and sale is not None and base > 0 and 0 <= sale < base:
        percentage = (base - sale) / base * Decimal('100')
        result['discount_percentage (%)'] = float(percentage.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))
        result['discount_tag'] = str(percentage.quantize(Decimal('1'), rounding=ROUND_HALF_UP)) + '% Off'
        result['discount_tag_source'] = 'calculated_from_prices'
    return result


def write_row(ws, vals):
    if ws.title in ('Products', 'Variant Combinations'):
        vals = discount_export_fields(vals)
    if ws.title == 'Products':
        vals = dict(vals)
        vals['sale_price (PKR, only if discounted)'] = vals.get('sale_price (PKR, agar discount ho)')
        vals['scraped_image_url (auto)'] = vals.get('scraped_image_url (cover, auto)')
        vals['final_image_url (main photo)'] = vals.get('final_image_url (cover/thumbnail — hosted link)') or vals.get('scraped_image_url (cover, auto)')
    elif ws.title == 'Option Groups':
        vals = dict(vals, **{'title (customer sees this)': vals.get('title (customer ko dikhega)')})
    elif ws.title == 'Options':
        vals = dict(vals, option_image_url=vals.get('option_image_url (agar size/color/variant ki apni image ho)'))
    # CHOTUAPP_GREEN_SMOOTH_V1: cache headers instead of re-reading them for every row.
    headers = getattr(ws, '_chotu_export_headers', None)
    if headers is None:
        headers = tuple(str(c.value).strip() if c.value is not None else '' for c in ws[1])
        ws._chotu_export_headers = headers
    ws.append([vals.get(h) for h in headers])


# CHOTUAPP_CATALOG_QUALITY_V3
# Conservative source-grounded categorization and description formatting.
def is_free_gift(product):
    # Only explicit promotional product identities. A paid "Gift Set" stays.
    identity = txt(product.get('title')) + ' ' + str(product.get('handle') or '').replace('-', ' ').replace('_', ' ')
    return bool(re.search(r'(?i)\bfree\s+gifts?\b|\bgifts?\s*\(\s*free\b|\bfree\s+(?:for|on)\s+(?:premium\s+)?orders\b', identity))


def normalize_category(value):
    value = re.sub(r'\s+', ' ', str(value or '')).strip()
    result = value.title()
    for acronym in ('BB', 'CC', 'UV', 'SPF', 'PKR', '3D'):
        result = re.sub(r'\b' + acronym + r'\b', acronym, result, flags=re.I)
    return result or 'Uncategorized'


def description_images(product, base):
    # Images in Shopify body_html are product content, not gallery metadata.
    soup = BeautifulSoup(product.get('body_html') or '', 'html.parser')
    result, seen = [], set()
    for image in soup.select('img'):
        src = image.get('data-src') or image.get('src')
        if not src and image.get('srcset'):
            src = image['srcset'].split(',')[-1].strip().split()[0]
        if not src:
            continue
        url = urljoin(base + '/', html.unescape(src))
        parsed = urlparse(url)
        if parsed.scheme not in ('https', 'http') or not parsed.hostname or '{' in url:
            continue
        if image_key(url) not in seen:
            seen.add(image_key(url)); result.append({'src': url})
    return result


def best_category(p, categories):
    title = txt(p.get('title'))
    ptype = txt(p.get('product_type'))
    options = [txt(c) for c in (categories or []) if c]
    context = ' '.join([title, ptype] + options).casefold()
    generic = re.compile(r'(?i)^(all|all products|shop all|new arrivals?|best sellers?|sale|featured|uncategorized|general|catalog|products?|collections?|shop now|in stock feed)$')
    def specific(value):
        return bool(value) and not re.search(r'(?i)product categories|shop online', value) and value.casefold() not in ('cosmetic', 'cosmetics', 'makeup', 'eye', 'lip') and not generic.fullmatch(value) and not re.search(r'(?i)\b(sale|discount|clearance|new arrival|best seller|trending|shop now|feed|under rs|under pkr)\b', value)
    # Explicit product words in the title take priority over broad site collections.
    rules = [
        (r'\b(brush cleaner|brush cleanser)\b', 'Brush Cleaner'),
        (r'\b(lip gloss|lipgloss|shiny gloss|shiny lip gloss)\b', 'Lip Gloss'),
        (r'\b(lip liners?|lipliners?)\b', 'Lip Liner'),
        (r'\b(lip balm|lipbalm)\b', 'Lip Balm'),
        (r'\b(lip tint|lip oil|lip serum)\b', 'Lip Care'),
        (r'\b(eyebrow|eye brow)\b', 'Eyebrow'),
        (r'\b(eyelash serum|eye lash serum)\b', 'Eyelash Serum'),
        (r'\b(eyelashes?|eye lashes?)\b', 'Eyelashes'),
        (r'\b(eyeliner|eye liner|gel liner|gelliner|kajal)\b', 'Eyeliner'),
        (r'\b(eye ?shadow|eye shades|eye palette)\b', 'Eyeshadow'),
        (r'\b(eye glitter|liquid glitter)\b', 'Eye Glitter'),
        (r'\bmascara\b', 'Mascara'),
        (r'\bfoundation\b', 'Foundation'),
        (r'\bconcealer\b', 'Concealer'),
        (r'\bcolor corrector|colour corrector\b', 'Color Corrector'),
        (r'\b(compact powder|pressed powder|face powder)\b', 'Face Powder'),
        (r'\bloose powder\b', 'Loose Powder'),
        (r'\bblush(?:er)?\b', 'Blush'),
        (r'\bhighlighters?\b', 'Highlighter'),
        (r'\bcontour|bronzer\b', 'Contour & Bronzer'),
        (r'\b(primer|bb cream|bbcream)\b', 'Face Primer' if 'primer' in title.casefold() else 'BB Cream'),
        (r'\b(makeup removers?|make up removers?)\b', 'Makeup Remover'),
        (r'\b(setting spray|fixer|setting mist)\b', 'Setting Spray'),
        (r'\b(brush|brushes)\b', 'Makeup Brushes'),
        (r'\b(face wash|cleanser)\b', 'Face Cleanser'),
        (r'\btoner\b', 'Toner'),
        (r'\b(hand cream|moisturizer|moisturiser)\b', 'Moisturizer'),
        (r'\bserum\b', 'Serum'),
        (r'\b(blender|blenders|sponge|sponges)\b', 'Makeup Sponges'),
        (r'\bnails?\b', 'Nails'),
        (r'\b(body mists?|perfumes?|fragrances?)\b', 'Fragrances'),

        (r'\b(khussa|khusa|khussas)\b', 'Khussa'),
        (r'\b(sneakers?|trainers?)\b', 'Sneakers'),
        (r'\b(slippers?|slides?)\b', 'Slippers'),
        (r'\b(sandals?)\b', 'Sandals'),
        (r'\b(heels?|stilettos?)\b', 'Heels'),
        (r'\b(pumps?)\b', 'Pumps'),
        (r'\b(boots?|booties)\b', 'Boots'),
        (r'\b(loafers?)\b', 'Loafers'),
        (r'\b(flip[ -]?flops?)\b', 'Flip Flops'),
        (r'\b(hand[ -]?bags?|tote bags?|shoulder bags?)\b', 'Hand Bags'),
        (r'\b(cross[ -]?body bags?)\b', 'Crossbody Bags'),
        (r'\b(clutches?|wallets?)\b', 'Clutches & Wallets'),
        (r'\b(backpacks?)\b', 'Backpacks'),
        (r'\b(gharara|sharara)\b', 'Gharara & Sharara'),
        (r'\b(kurta|kurti|kameez)\b', 'Kurtas & Kurtis'),
        (r'\b(dupatta|shawl)\b', 'Dupattas & Shawls'),
        (r'\b(dress|frock|gown)\b', 'Dresses'),
        (r'\b(jeans|trousers?|pants?)\b', 'Trousers & Jeans'),
        (r'\b(abayas?|hijabs?)\b', 'Abayas & Hijabs'),
        (r'\b(lipsticks?)\b', 'Lipstick'),
        (r'\b(perfumes?|fragrances?)\b', 'Fragrances'),
    ]
    # Explicit apparel words outrank beauty color words such as 'blush'.
    for pattern, label in rules:
        if label in ('Kurtas & Kurtis', 'Dresses', 'Trousers & Jeans', 'Abayas & Hijabs', 'Dupattas & Shawls', 'Gharara & Sharara') and re.search(pattern, title, re.I):
            return label
    if re.search(r'\b(bundle|deal)\b', title, re.I):
        return 'Bundles & Deals'
    if re.search(r'\bmake[ -]?up (kit|box|set)\b', title, re.I):
        return 'Makeup Kits'
    for pattern, label in rules:
        if re.search(pattern, title, re.I):
            return label
    # Do not classify generic gender or piece-count tags as precise product types.
    vague = re.compile(r'(?i)^(girls?|boys?|kids?|women|men|ladies|clothing|footwear|[123]\s*(?:pc|piece|pcs|pieces))$')
    for candidate in [ptype] + options:
        if specific(candidate) and not vague.fullmatch(candidate):
            for pattern, label in rules:
                if re.search(pattern, candidate, re.I):
                    return label
            return candidate.strip().title()
    if re.search(r'\b(shoes?|footwear)\b', context): return 'Footwear'
    if re.search(r'\b(shirt|suit|lawn|cotton|embroidered|2 piece|3 piece|co-ord)\b', context): return 'Clothing'
    if re.search(r'\b(bags?|purses?)\b', context): return 'Bags'
    return ptype if specific(ptype) else 'Uncategorized'

def needs_detailed_description(product, soup):
    identity = ' '.join([txt(product.get('title')), txt(product.get('product_type'))])
    electronics = r'\b(laptops?|notebooks?|macbooks?|computers?|desktops?|smartphones?|mobiles?|mobile phones?|phones?|iphones?|ipads?|tablets?|monitors?|televisions?|smart tv|led tv|routers?|printers?|headphones?|earphones?|earbuds?|speakers?|smart[ -]?watches?|cameras?|projectors?|power banks?|chargers?|graphics cards?|motherboards?|processors?|refrigerators?|washing machines?|air conditioners?)\b'
    # Any product's structured specification table deserves preservation.
    labels = set(re.findall(r'(?i)\b(ram|processor|chipset|storage|battery capacity|screen size|resolution|connectivity|usb)\b', soup.get_text(' ', strip=True)))
    specification_heading = any(re.search(r'(?i)\bspecifications?\b', node.get_text(' ',strip=True)) for node in soup.select('h1,h2,h3,h4'))
    return bool(re.search(electronics, identity, re.I) or soup.find(['table', 'dl']) or specification_heading or len(labels) >= 3)


def detailed_description(product, soup):
    title = txt(product.get('title'))
    specifications, seen = [], set()
    def add_spec(text):
        text = re.sub(r'\s+', ' ', text).strip()
        key = text.casefold()
        if text and key not in seen:
            seen.add(key); specifications.append(text)
    for table in soup.select('table'):
        for row in table.select('tr'):
            cells = [cell.get_text(' ', strip=True) for cell in row.find_all(['th','td'], recursive=False)]
            cells = [cell for cell in cells if cell]
            if cells:
                add_spec(cells[0] + ': ' + ' | '.join(cells[1:]) if len(cells) > 1 else cells[0])
        table.decompose()
    for definition in soup.select('dl'):
        for term in definition.select('dt'):
            value = term.find_next_sibling('dd')
            if value:
                add_spec(term.get_text(' ',strip=True) + ': ' + value.get_text(' ',strip=True))
        definition.decompose()
    for tag in soup.find_all(['p','li','h1','h2','h3','h4','br','div']):
        tag.insert_before('\n')
    lines, used = [], set()
    boilerplate = re.compile(r'(?i)^(add to cart|buy now|shop now|share|subscribe|newsletter|follow us|related products|you may also like|customer reviews|shipping policy|return policy)\b')
    for line in soup.get_text(' ',strip=False).splitlines():
        line = re.sub(r'\s+', ' ', html.unescape(line)).strip(' •|:-\t')
        heading = re.sub(r'(?i)^(what (?:is|are)|about)\s+', '', line).rstrip('?').strip()
        if not line or heading.casefold() == title.casefold() or boilerplate.search(line):
            continue
        if line.casefold() in ('description','specifications','technical specifications','product details'):
            continue
        if line.casefold() not in used and line.casefold() not in seen:
            used.add(line.casefold()); lines.append(line)
    # Specifications first: protect important details if Excel's hard cell
    # capacity is reached. No guessed model, capacity, warranty or features.
    sections = (['Specifications:\n' + '\n'.join(specifications)] if specifications else [])
    if lines:
        sections.append('\n'.join(lines))
    result = '\n\n'.join(sections) or title
    if len(result) > 32767:
        _chotu_debug('DESCRIPTION LIMIT: Excel cell capacity reached for ' + title)
        result = result[:32767]
    return result


def friendly_description(p):
    title = txt(p.get('title'))
    body = (p.get('body_html') or '') + (p.get('_storefront_specs_html') or '')
    if not body: return title
    soup = BeautifulSoup(str(body), 'html.parser')
    for tag in soup.find_all(['script','style','noscript','iframe','svg']): tag.decompose()
    if needs_detailed_description(p, soup):
        return detailed_description(p, soup)
    for tag in soup.find_all(['p','li','h2','h3','h4','br','div']): tag.insert_before('\n')
    source = html.unescape(soup.get_text(' ', strip=False)).replace('\xa0', ' ')
    reject = re.compile(r'(?i)(add to cart|buy now|shop now|wishlist|share this|free shipping|cash on delivery|return policy|subscribe|newsletter|follow us|limited time|hurry|order now|click here|discount code|customer reviews|read more|view all|related products|you may also like)')
    sentences, seen = [], set()
    for line in source.splitlines():
        line = re.sub(r'\s+', ' ', line).strip(' •|:-\t')
        if not line or reject.search(line): continue
        heading = re.sub(r'(?i)^(what (?:is|are)|about|description)\s*[:?-]?\s*', '', line).rstrip('?').strip()
        if heading.casefold() == title.casefold() or line.casefold() in ('features', 'benefits', 'description', 'how to use', 'product details'):
            continue
        for sentence in re.split(r'(?<=[.!?])\s+(?=[A-Z0-9])', line):
            sentence = sentence.strip(' •|:-\t')
            if not 8 <= len(sentence) <= 400 or 'http' in sentence.lower(): continue
            key = re.sub(r'\W+', '', sentence).casefold()
            if key and key not in seen:
                seen.add(key); sentences.append(sentence)
    if not sentences: return title
    title_words = set(re.findall(r'[a-z0-9]{4,}', title.lower()))
    def score(s):
        low=s.lower()
        return sum(w in low for w in title_words)*3 + len(re.findall(r'\b(size|shade|color|colour|material|fabric|includes|contains|made|capacity|volume|weight|finish|texture|set|pack|piece|ml|cm)\b',low))*2
    ranked = sorted(enumerate(sentences), key=lambda x:(-score(x[1]),x[0]))
    chosen, length = set(), 0
    for i, sentence in ranked:
        if length + len(sentence) + 1 > 300: continue
        chosen.add(i); length += len(sentence)+1
        if length >= 180 or len(chosen) >= 4: break
    result=' '.join(s for i,s in enumerate(sentences) if i in chosen)
    result = re.sub(r'\s+', ' ', result).strip()
    return result or title


# CHOTUAPP_TOP20_V1: best-selling ordering is used only when the storefront
# explicitly exposes the requested sort. Never infer sales volume.
def image_key(url):
    parts = urlsplit(urljoin('https://cdn.shopify.com', str(url)))
    path = re.sub(r'_\d+x\d*(?=\.[a-zA-Z]+$)', '', parts.path)
    # Shopify serves the same asset through store /cdn/shop/ and CDN /s/files/.
    if path.startswith('/cdn/shop/'):
        return ('shopify-asset', path[len('/cdn/shop/'):])
    if parts.netloc.casefold().endswith('.shopify.com'):
        match = re.search(r'.*/(files|products)/(.*)$', path)
        if match:
            return ('shopify-asset', match.group(1) + '/' + match.group(2))
    return (parts.netloc.casefold(), path)


def storefront_cover(base, product, pictures, log):
    url = base.rstrip('/') + '/products/' + product['handle']
    product['_storefront_specs_html'] = ''
    fallback = pictures[0]['src'] if pictures else ''
    status, detail, cover = 'REVIEW', '', fallback
    try:
        if getattr(_chotu_tls, 'image_throttled', False):
            raise RuntimeError('Image verification paused after source rate limit')
        _chotu_wait()
        # Apply existing source pacing; never send a burst of per-product requests.
        last = getattr(_chotu_tls, 'adaptive_last_request', 0)
        _chotu_backoff(max(0, last + getattr(_chotu_tls, 'adaptive_pace', 1.5) - time.monotonic()), 'Image pacing')
        _chotu_tls.adaptive_last_request = time.monotonic()
        resp = S.get(url, timeout=25)
        if resp.status_code in (429, 503):
            _chotu_tls.image_throttled = True
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, 'html.parser')
        # Only product-detail areas; do not harvest recommendation/global tables.
        product['_storefront_specs_html'] = ''.join(str(node) for node in soup.select(
            'product-info table, .product__info-container table, [id^="ProductInfo"] table, .product-specifications, #specifications, [data-product-specifications]'))
        hero = soup.select_one('media-gallery .product__media img, [id^="MediaGallery"] .product__media img, .product__media img')
        meta = soup.find('meta', property='og:image')
        candidate = (hero.get('data-src') or hero.get('src')) if hero else (meta.get('content') if meta else None)
        if not candidate:
            raise RuntimeError('No recognized product hero or og:image')
        candidate = urljoin(url, candidate)
        match = next((im['src'] for im in pictures if image_key(im['src']) == image_key(candidate)), None)
        if not match:
            raise RuntimeError('Front image not matched to this product gallery; API order preserved')
        cover, status, detail = match, 'VERIFIED', 'Product-page hero' if hero else 'Product-page og:image'
    except Exception as exc:
        detail = str(exc)[:250]
        log('IMAGE VERIFICATION INCOMPLETE: ' + url + ' — ' + detail)
    _chotu_tls.image_audit.append([url, status, cover, detail])
    return cover if status == 'VERIFIED' else None


# CHOTUAPP_FINAL_CATALOG_ORDER_V1

def genuine_discount(row):
    base=money(row.get('base_price (PKR)'))
    sale=money(row.get('sale_price (PKR, agar discount ho)'))
    return base is not None and sale is not None and base>0 and 0<=sale<base


def prioritize_top_sellers(rows, handles, variant_discount_ids=()):
    # CHOTUAPP_STRICT_DISCOUNT_ORDER_V2: only the visible Products row qualifies.
    discounted=genuine_discount
    has_discount=any(discounted(row) for row in rows)
    rank={handle:i for i,handle in enumerate(dict.fromkeys(handles)) if has_discount or i<20}
    def key(row):
        handle=urlparse(row['source_url']).path.rstrip('/').rsplit('/',1)[-1]
        eligible=discounted(row) if has_discount else True
        if eligible and handle in rank:return (0,rank[handle])
        return (1 if eligible else 2,0)
    rows.sort(key=key)
    return [row for row in rows if key(row)[0]==0]


def finalize_catalog_order(workbook_path, ranking_path, log):
    # Apply the order after price policy and immediately before publication.
    book=load_workbook(workbook_path)
    try:
        sheet=book['Products'];headers=[cell.value for cell in sheet[1]]
        rows=[dict(zip(headers,values)) for values in sheet.iter_rows(min_row=2,values_only=True)]
        handles=[]
        if Path(ranking_path).is_file():
            with Path(ranking_path).open(encoding='utf-8-sig',newline='') as stream:
                handles=[urlparse(row['source_url']).path.rstrip('/').rsplit('/',1)[-1] for row in csv.DictReader(stream)]
        ranked=prioritize_top_sellers(rows,handles)
        for index,row in enumerate(rows,2):
            for col,header in enumerate(headers,1):sheet.cell(index,col).value=row.get(header)
        temporary=Path(workbook_path).with_name('.'+Path(workbook_path).stem+'-order.xlsx')
        try:
            book.save(temporary)
            verify=load_workbook(temporary,read_only=True,data_only=True)
            try:
                if verify['Products'].max_row!=len(rows)+1:raise RuntimeError('Final ordering row count mismatch')
            finally:verify.close()
            os.replace(temporary,workbook_path)
        finally:temporary.unlink(missing_ok=True)
        log('FINAL FILE ORDER: '+str(len(ranked))+' verified best sellers first; remaining discounted products, then non-discounted; prices/variants/images retained')
    finally:book.close()


def verified_top20(base, log, eligible_handles=None, rank_all=False):
    # Walk verified collection grids, never navigation/recommendation links.
    found, seen = [], set()
    sort_verified_without_control = False
    wanted = len(eligible_handles) if rank_all and eligible_handles is not None else (min(20, len(eligible_handles)) if eligible_handles is not None else 20)
    page_limit = 100 if rank_all else 25
    if not wanted:
        return []
    try:
        for page in range(1, page_limit + 1):
            _chotu_wait()
            if page > 1:
                _chotu_backoff(getattr(_chotu_tls, 'adaptive_pace', 1.5), 'Best-selling pagination')
            response = S.get(base.rstrip('/') + '/collections/all?sort_by=best-selling&page=' + str(page), timeout=25)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            selected = any(node.get('value') == 'best-selling' and node.has_attr('selected')
                           for node in soup.select('option'))
            grid = soup.select_one('#product-grid, .product-grid, [data-product-grid]')
            if not selected and grid is not None:
                # Some Shopify themes hide sorting controls but emit server-side
                # pagination preserving the requested best-selling sort. Check
                # against a separate alphabetic control response before trusting it.
                next_link = soup.find('link', rel='next')
                next_url = urlparse(urljoin(base + '/', next_link.get('href', ''))) if next_link else None
                server_sort = next_url is not None and next_url.hostname == urlparse(base).hostname and dict(parse_qsl(next_url.query)).get('sort_by') == 'best-selling'
                if server_sort and page == 1:
                    _chotu_backoff(getattr(_chotu_tls, 'adaptive_pace', 1.5), 'Sort verification')
                    control = S.get(base.rstrip('/') + '/collections/all?sort_by=title-ascending&page=1', timeout=25)
                    control.raise_for_status()
                    control_grid = BeautifulSoup(control.text, 'html.parser').select_one('#product-grid, .product-grid, [data-product-grid]')
                    control_links = control_grid.select('h3 a[href*="/products/"]') if control_grid else []
                    labels = [a.get_text(' ', strip=True).casefold() for a in control_links]
                    current = [a.get('href') for a in grid.select('h3 a[href*="/products/"]')]
                    control_order = [a.get('href') for a in control_links]
                    selected = len(labels) >= 3 and labels == sorted(labels) and current != control_order
                    sort_verified_without_control = selected
                elif server_sort and page > 1:
                    selected = sort_verified_without_control
            if not selected or grid is None:
                raise RuntimeError('Selected best-selling sort and collection product grid were not both found')
            new_handles = 0
            for anchor in grid.select('a[href*="/products/"]'):
                parsed = urlparse(urljoin(base + '/', anchor.get('href', '')))
                if parsed.hostname != urlparse(base).hostname:
                    continue
                match = re.search(r'/products/([^/?#]+)', parsed.path)
                if match and match.group(1) not in seen:
                    handle = match.group(1)
                    seen.add(handle); new_handles += 1
                    if eligible_handles is None or handle in eligible_handles:
                        found.append(handle)
                if len(found) == wanted:
                    log('TOP 20: Storefront best-selling grid order confirmed; prioritizing ' + str(wanted) + ' available products')
                    return found
            if not new_handles:
                break
        raise RuntimeError('Could not verify all requested best-selling products within ' + str(page_limit) + ' pages')
    except Exception as exc:
        log('TOP 20: UNVERIFIED — ' + str(exc)[:200] + '; verified prefix retained; remaining ranks unknown, REVIEW required')
        return found if rank_all else []


def run_site(base, name, template, log):
    # CHOTUAPP_MULTIDIM_VARIANTS_V1
    OUT.mkdir(exist_ok=True)
    _chotu_tls.stylo_collections_rate_limited = False
    products, complete_catalog=discover(base,log)
    if not products: raise RuntimeError('No public products found. Shopify endpoint may be unavailable.')
    if getattr(_chotu_tls, 'stylo_collections_rate_limited', False):
        log('  STYLO: Skipping category endpoint after HTTP 429; using product type/title fallback. Category accuracy needs REVIEW.')
        cats = {}
    else:
        cats=collections(base,log)
    _chotu_debug_stage('Building Excel rows')
    wb=load_workbook(template)
    for sheet in ('Products','Product Images','Option Groups','Options','Variant Combinations'):
        if sheet not in wb.sheetnames: raise RuntimeError(f'Template missing sheet: {sheet}')
        ws=wb[sheet]
        if ws.max_row>1: ws.delete_rows(2,ws.max_row-1)
    rows=[]; imgs=[]; groups=[]; opts=[]; combos=[]; review=[]
    _chotu_tls.image_audit = []
    _chotu_tls.image_throttled = False
    _chotu_tls.price_throttled = False
    skipped_hidden = skipped_out_of_stock = skipped_invalid = 0
    for p in products:
        _chotu_wait()
        variants=[v for v in p.get('variants',[]) if v.get('id') is not None]
        priced=[v for v in variants if money(v.get('price')) is not None and money(v.get('price'))>0]
        # CHOTUAPP_AVAILABLE_PRODUCTS_ONLY_V1
        # A public catalog listing is not proof that a product is visible in every channel.
        # If Shopify explicitly reports unpublished/draft/archived, exclude it.
        status = str(p.get('status') or '').strip().lower()
        if status and status != 'active':
            skipped_hidden += 1
            continue
        if 'published_at' in p and not p.get('published_at'):
            skipped_hidden += 1
            continue
        if not p.get('handle') or not priced:
            skipped_invalid += 1
            continue
        available_priced=[v for v in priced if v.get('available') is True]
        # Only sellable products; retain unavailable variants of each included product.
        if not available_priced:
            skipped_out_of_stock += 1
            continue
        if is_free_gift(p):
            skipped_invalid += 1
            log('CATALOG FILTER: excluded free-gift promotion: ' + txt(p.get('title')))
            continue
        if re.search(r"(?i)don't buy me|default out of stock product", txt(p.get('body_html'))) or p.get('handle') in ('shipping-protection', 'back-in-stock-apps'):
            skipped_invalid += 1
            log('CATALOG FILTER: excluded service/placeholder: ' + txt(p.get('title')))
            continue
        try:
            variants = refresh_variant_prices(base, p, log)
            available_priced = [v for v in variants if v.get('available') is True and money(v.get('price')) is not None and money(v.get('price')) > 0]
            if not available_priced:
                skipped_out_of_stock += 1
                continue
        except Exception as exc:
            log('PRICE VERIFICATION INCOMPLETE: ' + txt(p.get('title')) + ' — ' + str(exc))
        cheapest=min(available_priced,key=lambda v:money(v['price']))
        lowest=money(cheapest['price'])
        compare=money(cheapest.get('compare_at_price'))
        baseprice=compare if compare is not None and compare>lowest else lowest
        sale=lowest if baseprice>lowest else None
        pid=uid('CP',base+'|'+str(p['id']))
        pictures=[im for im in (p.get('images') or []) if isinstance(im,dict) and im.get('src')]
        pictures.sort(key=lambda im:(im.get('position') if isinstance(im.get('position'),int) else 999999))
        featured=(p.get('image') or {}).get('src') or ''
        if featured and not any(im['src'] == featured for im in pictures):
            pictures.append({'src': featured})
        for variant in variants:
            image = variant.get('featured_image') or {}
            if isinstance(image, dict) and image.get('src'):
                pictures.append({'src': image['src']})
        pictures.extend(description_images(p, base))
        verified_cover = storefront_cover(base, p, pictures, log)
        if verified_cover:
            pictures.sort(key=lambda im: 0 if image_key(im['src']) == image_key(verified_cover) else 1)
        seen_urls=set(); pictures=[im for im in pictures if not (image_key(im['src']) in seen_urls or seen_urls.add(image_key(im['src'])))]
        cover=pictures[0]['src'] if pictures else featured
        category=normalize_category(best_category(p,cats.get(p.get('id'),[])))
        desc=friendly_description(p)
        url=f"{base}/products/{p['handle']}"
        dimensions=[]
        for idx,dim in enumerate((p.get('options') or [])[:3],1):
            title=txt(dim.get('name')) or f'Option {idx}'
            values=[]
            available_values = set()
            seen_values = set()
            for v in variants:
                value=txt(v.get(f'option{idx}'))
                if value and value not in seen_values:
                    seen_values.add(value)
                    values.append(value)
                if value and v.get('available') is True:
                    available_values.add(value)
            if values and not (len(values)==1 and values[0].lower() in ('default title','default')):
                # CHOTUAPP_VERIFIED_SHADE_QUALITY_V1: exact observed Shopify product only.
                if (urlparse(base).hostname or '').lower().removeprefix('www.') == 'missrose.com.pk' and p.get('handle') == 'miss-rose-under-eye-pencil-2' and idx == 1 and title.casefold() == 'title' and set(values) == {'White M3', 'nude M1'}:
                    title = 'Shade'
                gid=uid('CG',pid+'|'+str(idx))
                dimensions.append((idx,gid,title,values))
                groups.append({'group_id':gid,'title (customer ko dikhega)':title,'select_type':'single','min':1,'max':1,'required (yes/no)':'yes'})
                for value in values:
                    # Same availability rule, precomputed once per dimension.
                    opts.append({'option_id':uid('CO',gid+'|'+value),'group_id':gid,'option_name':value,'extra_price (PKR)':0,'option_image_url (agar size/color/variant ki apni image ho)':'','available (yes/no)':'yes' if value in available_values else 'no'})
        gid=','.join(x[1] for x in dimensions)
        for v in variants:
            vp=money(v.get('price')); vc=money(v.get('compare_at_price'))
            variant_base=vc if vp is not None and vc is not None and vc>vp else vp
            variant_sale=vp if vp is not None and variant_base is not None and variant_base>vp else None
            image=v.get('featured_image') or {}
            image_url=image.get('src') if isinstance(image,dict) else ''
            entry={'combination_id':uid('CC',base+'|'+str(v['id'])),'product_id':pid,'source_variant_id':str(v['id']),'sku':str(v.get('sku') or ''),'base_price (PKR)':float(variant_base) if variant_base is not None else None,'sale_price (PKR, agar discount ho)':float(variant_sale) if variant_sale is not None else None,'available (yes/no)':'yes' if v.get('available') is True else 'no','stock_quantity (agar public ho)':'','variant_image_url':image_url or '','source_url':url}
            for pos,(idx,group_id,title,values) in enumerate(dimensions,1):
                entry[f'option_{pos}_group_id']=group_id
                entry[f'option_{pos}_value']=txt(v.get(f'option{idx}'))
            combos.append(entry)
        if len(p.get('options') or [])>3: review.append(f'More than 3 dimensions: {url}')
        rows.append({'product_id':pid,'category':category,'subcategory':'','name':txt(p.get('title')),'description':desc,'brand':txt(p.get('vendor')) or name,'material':'','weight_grams (agar ho)':'','condition (new/used)':'new','warranty_months (agar ho)':'','base_price (PKR)':float(baseprice),'sale_price (PKR, agar discount ho)':float(sale) if sale is not None else None,'sku':str(cheapest.get('sku') or ''),'scraped_image_url (cover, auto)':cover,'final_image_url (cover/thumbnail — hosted link)':'','option_groups':gid,'available (yes/no)':'yes' if any(v.get('available') is True for v in variants) else 'no','stock_quantity (kitni quantity bechni hai)':'','max_qty_per_user (ek user zyada se zyada kitni le sakta hai)':'','source_url':url})
        if not pictures: review.append(f'No image: {p.get("title")}')
        for i,im in enumerate(pictures,1):
            src=im.get('src')
            if not src: continue
            imgs.append({'image_id':uid('CI',pid+'|'+str(im.get('id') or i)),'product_id':pid,'image_order':i,'scraped_image_url (auto)':src,'final_image_url (paste — hosted link)':'','is_primary (yes/no)':'yes' if i==1 else 'no','source_url':url})
    log(f'PRODUCT FILTER: excluded {skipped_out_of_stock} fully unavailable products; skipped {skipped_hidden} explicitly unpublished, {skipped_invalid} invalid/unpriced; retained {len(rows)} products with ALL their variants')
    if not rows: raise RuntimeError('No public, priced products found')
    rows.sort(key=lambda x:(x['category'].lower(), x['sale_price (PKR, agar discount ho)'] or x['base_price (PKR)'],x['name'].lower()))
    # CHOTUAPP_DISCOUNT_TOP20_V1: strict visible-row discount grouping.
    discount_handles={urlparse(r['source_url']).path.rstrip('/').rsplit('/',1)[-1] for r in rows if genuine_discount(r)}
    ranking_handles=discount_handles or {urlparse(r['source_url']).path.rstrip('/').rsplit('/',1)[-1] for r in rows}
    top_handles=verified_top20(base,log,ranking_handles,rank_all=bool(discount_handles))
    safe_name = re.sub(r'[^\w .-]', '', name).strip() or 'Shopify'
    with (OUT / (safe_name + ' - IMAGE AUDIT.csv')).open('w', encoding='utf-8-sig', newline='') as stream:
        writer = csv.writer(stream)
        writer.writerow(['product_url', 'status', 'cover_url', 'detail'])
        writer.writerows(_chotu_tls.image_audit)
    ranked_rows = prioritize_top_sellers(rows, top_handles)
    with (OUT / (safe_name + ' - BEST SELLERS.csv')).open('w', encoding='utf-8-sig', newline='') as stream:
        writer = csv.writer(stream)
        writer.writerow(['rank', 'product_id', 'name', 'category', 'source_url'])
        for rank, row in enumerate(ranked_rows, 1):
            writer.writerow([rank, row['product_id'], row['name'], row['category'], row['source_url']])
    if ranked_rows:
        log('FILE ORDER: verified top sellers among discounted products first (all products if no discounts); then remaining discounted, then non-discounted across ALL categories')

    log(f'VARIANT EXPORT: {len(combos)} combinations; ' +
        str(sum(c['available (yes/no)'] == 'no' for c in combos)) + ' unavailable preserved as no')
    galleries = {}
    for image in imgs:
        galleries.setdefault(image['product_id'], []).append(image['scraped_image_url (auto)'])
    for r in rows:
        r['gallery_urls (extra photos, separate with |)'] = '|'.join(galleries.get(r['product_id'], []))
        write_row(wb['Products'],r)
    log('DISCOUNT TAGS: product and variant percentages calculated from exported regular/sale prices; exact website badge text not independently fetched')
    for r in imgs: write_row(wb['Product Images'],r)
    for r in groups: write_row(wb['Option Groups'],r)
    for r in opts: write_row(wb['Options'],r)
    for r in combos: write_row(wb['Variant Combinations'],r)
    if len({x['combination_id'] for x in combos})!=len(combos): raise RuntimeError('Duplicate combination IDs')
    product_ids_for_validation = {r['product_id'] for r in rows}
    if any(x['product_id'] not in product_ids_for_validation for x in combos): raise RuntimeError('Orphan variant combination')
    if len({r['product_id'] for r in rows})!=len(rows): raise RuntimeError('Duplicate product IDs')
    if any(x['product_id'] not in product_ids_for_validation for x in imgs): raise RuntimeError('Orphan image')
    safe=re.sub(r'[^\w .-]','',name).strip() or 'Shopify'
    target=OUT/f'{safe} - REFRESH REVIEW.xlsx'; temp=OUT/f'{safe} - BUILDING.xlsx'
    _chotu_debug_stage('Saving Excel workbook')
    wb.save(temp)
    verify=load_workbook(temp,read_only=True)
    if verify['Products'].max_row-1!=len(rows): raise RuntimeError('Export row count mismatch')
    verify.close()
    os.replace(temp,target)
    log(f'EXPORT BUILT: {len(rows)} products, {len(imgs)} images, {len(groups)} selector groups, {len(opts)} selector values, {len(combos)} actual variants ({sum(x["available (yes/no)"]=="no" for x in combos)} unavailable)')
    log(f'FILE: {target}')
    audit_fractional_prices(base, rows, combos, OUT/f'{safe} - PRICE AUDIT.csv', log)
    storefront_verified = storefront_price_audit(rows, OUT/f'{safe} - STOREFRONT AUDIT.csv', log)
    quality_issues = quality_validation(rows, imgs, groups, opts, combos, OUT/f'{safe} - QUALITY REPORT.csv', log, storefront_verified)
    final=OUT/f'{safe} - FINAL.xlsx'
    report=OUT/f'{safe} - CHANGE REPORT.csv'
    old_rows={}
    if final.is_file():
        old_wb=load_workbook(final,read_only=True,data_only=True)
        old_ws=old_wb['Products']
        old_iter=old_ws.values
        old_headers=list(next(old_iter))
        for values in old_iter:
            d=dict(zip(old_headers,values))
            if d.get('source_url'): old_rows[d['source_url']]=d
        old_wb.close()
    new_rows={r['source_url']:r for r in rows}
    changes=[]
    price_keys=('base_price (PKR)','sale_price (PKR, agar discount ho)')
    for url,r in new_rows.items():
        if url not in old_rows:
            changes.append(('ADDED',url,'',''))
        else:
            old=old_rows[url]
            for key in price_keys:
                if money(old.get(key)) != money(r.get(key)):
                    changes.append(('PRICE CHANGE',url,key,f'{old.get(key)} -> {r.get(key)}'))
    for url in old_rows.keys()-new_rows.keys():
        changes.append(('MISSING IN REFRESH',url,'','Check stock / page visibility'))
    with report.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.writer(f);w.writerow(['change','product_url','field','detail']);w.writerows(changes)
    log(f'CHANGE REPORT: {report} ({len(changes)} changes)')
    if final.exists():
        log(f'OLD vs NEW: {len(old_rows)} -> {len(new_rows)} products')
    if quality_issues:
        log('STATUS: REVIEW REQUIRED — quality report has findings')
    elif not complete_catalog:
        log('STATUS: REVIEW REQUIRED — large catalog completeness unverified')
    elif any(',' in r['option_groups'] for r in rows):
        log('STATUS: REVIEW REQUIRED — multi-selector importer and combination mapping must be confirmed by developer')
    elif review:
        log('STATUS: REVIEW REQUIRED — missing product images')
    else:
        log('STATUS: REVIEW READY — product-page verification and ChotuApp import not guaranteed')

    log('Existing FINAL file preserved. Review refresh before manually replacing it.')
    if not complete_catalog: log('WARNING: Catalog completeness NOT PROVEN (Shopify 100-page ceiling). Never auto-promote this export.')
    if review: log(f'REVIEW: {len(review)} products without gallery images')
    log('NOTE: Public catalog only; not a checkout, importer or current product-page verification.')


def quality_validation(rows, imgs, groups, opts, combos, output, log, storefront_verified=None):
    storefront_verified = storefront_verified or set()
    # CHOTUAPP_QUALITY_VALIDATION_V1
    # Read-only checks: do not alter source data or auto-correct prices/categories.
    from collections import Counter, defaultdict
    issues = []
    product_ids = {r['product_id'] for r in rows}
    group_ids = {g['group_id'] for g in groups}
    option_values = defaultdict(set)
    for o in opts:
        option_values[o.get('group_id')].add(str(o.get('option_name') or ''))
    group_owner = {}
    for r in rows:
        for gid in str(r.get('option_groups') or '').split(','):
            if gid:
                group_owner[gid] = r['product_id']
    product_urls = {r['product_id']: r.get('source_url', '') for r in rows}

    def flag(severity, code, pid='', detail='', url=''):
        issues.append((severity, code, str(pid or ''), str(url or product_urls.get(pid, '')), str(detail)))

    generic = {'miss rose product categories', 'in stock feed', 'all products',
               'shop all', 'sale', 'new arrivals', 'uncategorized', 'general'}
    product_id_counts = Counter(r.get('product_id') for r in rows)
    url_counts = Counter(r.get('source_url') for r in rows)
    images_by_pid = defaultdict(list)
    image_keys = Counter()
    for im in imgs:
        pid = im.get('product_id')
        images_by_pid[pid].append(im)
        image_keys[(pid, im.get('scraped_image_url (auto)'))] += 1
        if pid not in product_ids:
            flag('ERROR', 'ORPHAN_IMAGE', pid, 'Image refers to absent product', im.get('source_url'))
    for (pid, src), count in image_keys.items():
        if count > 1:
            flag('WARNING', 'DUPLICATE_IMAGE_URL', pid, f'{count} copies: {src}')

    for r in rows:
        pid = r['product_id']
        url = r.get('source_url', '')
        if product_id_counts[pid] > 1:
            flag('ERROR', 'DUPLICATE_PRODUCT_ID', pid, product_id_counts[pid], url)
        if url_counts[url] > 1:
            flag('ERROR', 'DUPLICATE_PRODUCT_URL', pid, url_counts[url], url)
        cat = str(r.get('category') or '').strip()
        if not cat or cat.casefold() in generic or 'categories' in cat.casefold() or 'feed' in cat.casefold():
            flag('WARNING', 'GENERIC_CATEGORY', pid, cat or '(empty)', url)
        desc = str(r.get('description') or '').strip()
        if len(desc) >= 32767:
            flag('WARNING', 'DESCRIPTION_EXCEL_CELL_LIMIT', pid, 'Description reaches Excel cell limit; check source for omitted detail', url)
        if re.search(r'(?i)\b(free gift|premium orders|free for orders)\b',str(r.get('name') or '')):
            flag('WARNING', 'PROMOTIONAL_PRODUCT_REVIEW', pid, 'Confirm this is separately saleable before importing', url)
        if not desc:
            flag('ERROR', 'MISSING_DESCRIPTION', pid, '', url)
        elif len(desc) < 35 or desc.casefold() == str(r.get('name') or '').strip().casefold():
            flag('WARNING', 'SHORT_DESCRIPTION', pid, f'{len(desc)} characters', url)
        cover = str(r.get('scraped_image_url (cover, auto)') or '').strip()
        if not cover:
            flag('ERROR', 'MISSING_COVER', pid, '', url)
        elif not (cover.startswith('https://') or cover.startswith('http://') or cover.startswith('//')):
            flag('WARNING', 'INVALID_COVER_URL', pid, cover, url)
        if not images_by_pid[pid]:
            flag('ERROR', 'MISSING_GALLERY', pid, '', url)
        base = money(r.get('base_price (PKR)'))
        sale = money(r.get('sale_price (PKR, agar discount ho)'))
        if base is None or base <= 0:
            flag('ERROR', 'INVALID_BASE_PRICE', pid, str(base), url)
        if sale is not None and (sale <= 0 or (base is not None and sale >= base)):
            flag('WARNING', 'SUSPICIOUS_SALE_PRICE', pid, f'base={base}, sale={sale}', url)
        if any(p is not None and p != p.to_integral_value() for p in (base, sale)):
            if url in storefront_verified:
                flag('INFO', 'FRACTIONAL_PRICE_DISPLAY_MATCH', pid, f'API base={base}, sale={sale}; static storefront HTML matched exact/whole-rupee active price; no export change', url)
            else:
                flag('WARNING', 'FRACTIONAL_PKR_PRICE', pid, f'base={base}, sale={sale}', url)
        for gid in str(r.get('option_groups') or '').split(','):
            if gid and gid not in group_ids:
                flag('ERROR', 'MISSING_OPTION_GROUP', pid, gid, url)

    for g in groups:
        gid = g['group_id']
        pid = group_owner.get(gid, '')
        if not pid:
            flag('ERROR', 'UNREFERENCED_GROUP', '', gid)
        title = str(g.get('title (customer ko dikhega)') or '').strip()
        if title.casefold() in ('title', 'default title', 'default', 'option'):
            flag('WARNING', 'PLACEHOLDER_GROUP_TITLE', pid, title)
        if not option_values.get(gid):
            flag('ERROR', 'EMPTY_OPTION_GROUP', pid, gid)
    for o in opts:
        gid = o.get('group_id')
        if gid not in group_ids:
            flag('ERROR', 'ORPHAN_OPTION', '', str(gid))
        if o.get('available (yes/no)') not in ('yes', 'no'):
            flag('ERROR', 'INVALID_OPTION_AVAILABILITY', group_owner.get(gid, ''), str(o.get('available (yes/no)')))

    variant_ids = Counter((c.get('product_id'), str(c.get('source_variant_id'))) for c in combos)
    combos_by_pid = defaultdict(list)
    for c in combos:
        pid = c.get('product_id')
        combos_by_pid[pid].append(c)
        if pid not in product_ids:
            flag('ERROR', 'ORPHAN_COMBINATION', pid, c.get('source_variant_id'), c.get('source_url'))
        if variant_ids[(pid, str(c.get('source_variant_id')))] > 1:
            flag('ERROR', 'DUPLICATE_VARIANT_ID', pid, c.get('source_variant_id'))
        if c.get('available (yes/no)') not in ('yes', 'no'):
            flag('ERROR', 'INVALID_VARIANT_AVAILABILITY', pid, c.get('source_variant_id'))
        base = money(c.get('base_price (PKR)'))
        sale = money(c.get('sale_price (PKR, agar discount ho)'))
        if base is None or base <= 0:
            flag('WARNING', 'VARIANT_MISSING_PRICE', pid, c.get('source_variant_id'))
        if sale is not None and (sale <= 0 or (base is not None and sale >= base)):
            flag('WARNING', 'VARIANT_SALE_PRICE', pid, c.get('source_variant_id'))
        for i in (1, 2, 3):
            gid = c.get(f'option_{i}_group_id')
            value = c.get(f'option_{i}_value')
            if gid and gid not in group_ids:
                flag('ERROR', 'VARIANT_UNKNOWN_GROUP', pid, f'{gid}: {value}')
            elif gid and str(value or '') not in option_values.get(gid, set()):
                flag('ERROR', 'VARIANT_UNKNOWN_VALUE', pid, f'{gid}: {value}')
            if gid and group_owner.get(gid) != pid:
                flag('ERROR', 'VARIANT_WRONG_PRODUCT_GROUP', pid, gid)

    for r in rows:
        pid = r['product_id']
        cs = combos_by_pid.get(pid, [])
        if not cs:
            flag('ERROR', 'PRODUCT_WITHOUT_VARIANTS', pid)
        else:
            actual = 'yes' if any(c.get('available (yes/no)') == 'yes' for c in cs) else 'no'
            if r.get('available (yes/no)') != actual:
                flag('ERROR', 'PRODUCT_AVAILABILITY_MISMATCH', pid, f'product={r.get("available (yes/no)")}, variants={actual}')

    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('w', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f)
        w.writerow(['severity', 'issue_code', 'product_id', 'source_url', 'detail'])
        w.writerows(issues)
    counts = Counter(x[0] for x in issues)
    log(f'QUALITY REPORT: {output} ({len(issues)} findings; {counts["ERROR"]} errors, {counts["WARNING"]} warnings)')
    log('QUALITY NOTE: Structural and heuristic checks only; live website price, images, and checkout NOT verified.')
    return sum(x[0] in ('ERROR', 'WARNING') for x in issues)



# CHOTUAPP_PROGRESS_SINGLE_FINAL_V1
# Percentage represents pipeline stages, not exact network bytes or elapsed time.
_chotuapp_run_site_original = run_site

def run_site(base, name, template, log):
    global OUT
    real_out = OUT
    safe = re.sub(r'[^\w .-]', '', name).strip() or 'Shopify'
    software_dir = Path(__file__).resolve().parent
    audit_dir = software_dir / 'audit_reports' / safe
    staging_root = software_dir / '_build_temp'
    staging_root.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix='chotu_', dir=str(staging_root)))
    final = real_out / (safe + ' - FINAL.xlsx')
    current_progress = 0

    def progress(pct, message):
        nonlocal current_progress
        pct = max(current_progress, min(100, int(pct)))
        current_progress = pct
        log('__CHOTU_PROGRESS__|' + str(pct) + '|' + str(message))

    def intercept(message):
        text = str(message)
        log(text)
        if 'Catalog page ' in text:
            progress(min(25, 5 + 2 * len([x for x in logs if 'Catalog page ' in x])), 'Fetching catalog')
        elif 'Collection categories mapped:' in text:
            progress(35, 'Categories mapped')
        elif 'PRODUCT FILTER:' in text:
            progress(58, 'Products and variants processed')
        elif 'EXPORT BUILT:' in text:
            progress(70, 'Excel built')
        elif 'PRICE AUDIT:' in text:
            progress(80, 'Price audit complete')
        elif 'STOREFRONT AUDIT:' in text:
            progress(88, 'Storefront audit complete')
        elif 'QUALITY REPORT:' in text:
            progress(93, 'Quality checks complete')
        elif 'CHANGE REPORT:' in text:
            progress(96, 'Change report complete')
        logs.append(text)

    logs = []
    progress(1, 'Starting ' + name)
    try:
        real_out.mkdir(parents=True, exist_ok=True)
        # Keep original FINAL available for old-vs-new comparison inside the staging area.
        if final.exists():
            shutil.copy2(final, staging / final.name)
        OUT = staging
        try:
            _chotuapp_run_site_original(base, name, template, intercept)
        finally:
            OUT = real_out

        review_file = staging / (safe + ' - REFRESH REVIEW.xlsx')
        if not review_file.is_file():
            raise RuntimeError('Refresh workbook missing; existing FINAL preserved')

        # CHOTUAPP_DECIMAL_TRUNCATE_V1
        # User-selected integer PKR export policy. Original source prices remain in API audit.
        # Do not silently publish transformed prices as verified FINAL.
        from decimal import Decimal as _Decimal
        _book = load_workbook(review_file)
        _changed = 0
        for _sheet_name in ('Products', 'Variant Combinations'):
            if _sheet_name not in _book.sheetnames:
                _book.close()
                raise RuntimeError('Price policy: missing sheet ' + _sheet_name)
            _ws = _book[_sheet_name]
            _headers = {str(c.value).strip(): c.column for c in _ws[1] if c.value is not None}
            for _field in ('base_price (PKR)', 'sale_price (PKR, agar discount ho)'):
                if _field not in _headers:
                    _book.close()
                    raise RuntimeError('Price policy: missing column ' + _field)
                for _cells in _ws.iter_rows(min_row=2, min_col=_headers[_field], max_col=_headers[_field]):
                    _cell = _cells[0]
                    if _cell.value is None or _cell.value == '':
                        continue
                    try:
                        _value = _Decimal(str(_cell.value))
                        if not _value.is_finite() or _value < 0:
                            raise ValueError('Invalid price')
                        _integer = int(_value)  # truncate, do not round
                    except Exception as _exc:
                        _book.close()
                        raise RuntimeError('Price policy: invalid value in ' + _sheet_name + ' cell ' + _cell.coordinate) from _exc
                    if _value != _integer:
                        _cell.value = _integer
                        _changed += 1
        if _changed:
            # Keep new export aliases/tags consistent with the final integer prices.
            for _sheet_name in ('Products', 'Variant Combinations'):
                _ws = _book[_sheet_name]
                _headers = {str(c.value).strip(): c.column for c in _ws[1] if c.value is not None}
                for _row in _ws.iter_rows(min_row=2):
                    _vals = {key: _row[col-1].value for key, col in _headers.items()}
                    _tags = discount_export_fields(_vals)
                    for _key in ('discount_percentage (%)', 'discount_tag', 'discount_tag_source', 'source_discount_tag'):
                        if _key in _headers: _row[_headers[_key]-1].value = _tags[_key]
                    if 'sale_price (PKR, only if discounted)' in _headers:
                        _row[_headers['sale_price (PKR, only if discounted)']-1].value = _vals.get('sale_price (PKR, agar discount ho)')
            _temp = staging / (safe + ' - PRICE POLICY BUILDING.xlsx')
            try:
                _book.save(_temp)
                _book.close()
                _check = load_workbook(_temp, read_only=True)
                _check.close()
                os.replace(_temp, review_file)
            finally:
                _book.close()
                if _temp.exists(): _temp.unlink()
        else:
            _book.close()
        log('PRICE POLICY: Removed fractional parts from ' + str(_changed) + ' Excel price cells (Products + Variant Combinations); original API price audits preserved.')
        finalize_catalog_order(review_file, staging / (safe + ' - BEST SELLERS.csv'), log)

        def problem_rows(filename, bad_values, column):
            file = staging / (safe + ' - ' + filename + '.csv')
            if not file.exists():
                return [filename + ' report missing']
            with file.open('r', encoding='utf-8-sig', newline='') as stream:
                reader = csv.DictReader(stream)
                if not reader.fieldnames or column not in reader.fieldnames:
                    return [filename + ' report malformed']
                return [str(row) for row in reader if (row.get(column) or '').upper() in bad_values]

        problems = []
        if _changed:
            problems.append('Integer-only export prices differ from source; manual price approval required')
        problems += problem_rows('QUALITY REPORT', {'ERROR', 'WARNING'}, 'severity')
        problems += problem_rows('PRICE AUDIT', {'REVIEW', 'MISMATCH'}, 'status')
        problems += problem_rows('STOREFRONT AUDIT', {'REVIEW', 'RATE_LIMITED'}, 'status')
        # Early stop after throttling leaves other fractional products unverified.
        storefront_report = staging / (safe + ' - STOREFRONT AUDIT.csv')
        quality_report = staging / (safe + ' - QUALITY REPORT.csv')
        if storefront_report.is_file() and quality_report.is_file():
            with storefront_report.open(encoding='utf-8-sig', newline='') as fh:
                audited_urls = {row.get('product_url') for row in csv.DictReader(fh)}
            with quality_report.open(encoding='utf-8-sig', newline='') as fh:
                fractional_urls = {row.get('source_url') for row in csv.DictReader(fh)
                                   if row.get('issue_code') in
                                   ('FRACTIONAL_PKR_PRICE', 'FRACTIONAL_PRICE_DISPLAY_MATCH')}
            if fractional_urls - audited_urls:
                problems.append('Storefront verification incomplete after rate limiting')

        # Do not publish a partial/uncertain catalog if the source hit its known page limit.
        if any('PRICE VERIFICATION INCOMPLETE:' in line for line in logs):
            problems.append('Some live variant prices could not be verified')
        if any('IMAGE VERIFICATION INCOMPLETE:' in line for line in logs):
            problems.append('Some storefront front images could not be verified')
        if any('TOP 20: UNVERIFIED' in line for line in logs):
            problems.append('Best-selling order could not be verified')
        if any('Catalog completeness NOT PROVEN' in line for line in logs):
            problems.append('Catalog completeness unverified')
        if any('Category mapping INCOMPLETE' in line for line in logs):
            problems.append('Category mapping incomplete after rate limiting')
        audit_dir.mkdir(parents=True, exist_ok=True)
        for report in staging.glob(safe + ' - *.csv'):
            shutil.copy2(report, audit_dir / report.name)
        if any('multi-selector importer and combination mapping' in line for line in logs):
            problems.append('Multi-selector importer compatibility not verified')
        if problems:
            shutil.copy2(review_file, audit_dir / review_file.name)
            # CHOTUAPP_VISIBLE_REVIEW_V1
            # A completed extraction must remain visible even when FINAL is blocked.
            # Never overwrite a prior REVIEW without preserving a timestamped backup.
            visible_review = real_out / (safe + '.xlsx')
            if visible_review.exists():
                review_backups = software_dir / 'review_backups'
                review_backups.mkdir(parents=True, exist_ok=True)
                stamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f')
                shutil.copy2(visible_review, review_backups / (safe + ' - REVIEW - ' + stamp + '.xlsx'))
            with tempfile.NamedTemporaryFile(prefix='.' + safe + '-review-', suffix='.xlsx',
                                             dir=str(real_out), delete=False) as tmp_file:
                review_tmp = Path(tmp_file.name)
            try:
                shutil.copy2(review_file, review_tmp)
                check_wb = load_workbook(review_tmp, read_only=True)
                try:
                    if check_wb['Products'].max_row < 2:
                        raise RuntimeError('REVIEW workbook has no products')
                finally:
                    check_wb.close()
                os.replace(review_tmp, visible_review)
            finally:
                review_tmp.unlink(missing_ok=True)
            log('SAVED REVIEW EXCEL: ' + str(visible_review))
            progress(min(current_progress, 96), 'REVIEW REQUIRED: FINAL preserved')
            log('REVIEW REQUIRED: ' + str(len(problems)) + ' audit issue(s). Previous FINAL kept.')
            log('Review files: ' + str(audit_dir))
            return

        # Never overwrite the last good FINAL without a separate backup.
        if final.exists():
            backups = software_dir / 'final_backups'
            backups.mkdir(parents=True, exist_ok=True)
            stamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f')
            shutil.copy2(final, backups / (safe + ' - FINAL - ' + stamp + '.xlsx'))
        tmp = real_out / ('.' + safe + '.building.xlsx')
        try:
            shutil.copy2(review_file, tmp)
            os.replace(tmp, real_out / (safe + '.xlsx'))
        finally:
            if tmp.exists():
                tmp.unlink()
        progress(100, 'COMPLETED: ' + name)
        log('COMPLETED: ' + str(final))
        log('One current Excel named <store>.xlsx; legacy files are preserved. Audit reports: ' + str(audit_dir))
        log('NOTE: Excel structure passed local checks; live importer/checkout compatibility still unverified.')
    except Exception:
        progress(current_progress, 'FAILED: ' + name)
        raise
    finally:
        OUT = real_out
        shutil.rmtree(staging, ignore_errors=True)


class App:
    # CHOTUAPP_PREMIUM_DASHBOARD_V1 — UI only; extraction engine unchanged.
    # CHOTUAPP_STUDIO_2026 — UI-only replacement, extractor unchanged.
    def __init__(self, root):
        import customtkinter as ctk
        ctk.set_appearance_mode('dark')
        ctk.set_default_color_theme('blue')
        self.root = root
        root.title('ChotuApp Studio R11 | Detailed specifications')
        root.geometry('1370x900')
        root.minsize(900, 640)
        root.configure(bg='#07170f')
        self.events = queue.Queue()
        self.sites = []
        try:
            self.sites = json.loads(CONFIG.read_text(encoding='utf-8'))
        except (OSError, ValueError):
            pass
        self.running = False
        self.job_reviewed = False
        root.protocol('WM_DELETE_WINDOW', self.close)
        self.job_failed = False
        self.job_completed = 0
        self.job_expected = 0
        self._ui_pulse = 0
        self._ui_products = 0
        self._ui_collections = 0
        self._ui_started = None
        self._ui_request_count = 0
        self._ui_429_count = 0
        BG='#07170f'; PANEL='#10271b'; PANEL2='#173b28'; EDGE='#28513a'
        FG='#f1fff5'; MUTED='#a2c5ad'; ACCENT='#20b86b'
        def frame(parent, color=PANEL, radius=18, **kw):
            return ctk.CTkFrame(parent, fg_color=color, corner_radius=radius, border_width=0, **kw)
        def label(parent, text, size=12, color=MUTED, bold=False, **kw):
            return ctk.CTkLabel(parent, text=text, text_color=color,
                font=ctk.CTkFont(family='Segoe UI', size=size, weight='bold' if bold else 'normal'), **kw)
        def button(parent, text, command, primary=False, width=130, **kw):
            return ctk.CTkButton(parent, text=text, command=command, width=width, height=39,
                corner_radius=11, fg_color=ACCENT if primary else '#244b34',
                hover_color='#159450' if primary else '#346e4a',
                text_color='#ffffff', font=ctk.CTkFont(family='Segoe UI',size=12,weight='bold'), **kw)
        def entry(parent, var, placeholder='', width=170):
            return ctk.CTkEntry(parent, textvariable=var, width=width, height=41,
                corner_radius=10, fg_color='#0b1e14', border_color=EDGE,
                text_color=FG, placeholder_text=placeholder,
                font=ctk.CTkFont(family='Segoe UI',size=12))

        # Compact header and scrollable workspace prevent controls disappearing on 1366x768 screens.
        header=frame(root,'#0c2116',0)
        header.pack(fill='x')
        header_inner=ctk.CTkFrame(header,fg_color='transparent')
        header_inner.pack(fill='x',padx=26,pady=16)
        label(header_inner,'◆',25,ACCENT,True).pack(side='left',padx=(0,12))
        title=ctk.CTkFrame(header_inner,fg_color='transparent')
        title.pack(side='left')
        label(title,'ChotuApp Studio',23,FG,True).pack(anchor='w')
        label(title,'PRODUCT SPECIFICATIONS · DETAILED DESCRIPTIONS · R11',10,MUTED,True).pack(anchor='w')
        self.header_clock=label(header_inner,'●  SYSTEM READY',11,ACCENT,True)
        self.header_clock.pack(side='right')

        workspace=ctk.CTkScrollableFrame(root,fg_color=BG,corner_radius=0,
                    scrollbar_button_color='#28513a',scrollbar_button_hover_color=ACCENT)
        workspace.pack(fill='both',expand=True)
        self._wheel_workspace = workspace
        body=ctk.CTkFrame(workspace,fg_color='transparent')
        body.pack(fill='both',expand=True,padx=23,pady=(17,25))

        hero=ctk.CTkFrame(body,fg_color='transparent')
        hero.pack(fill='x',pady=(0,15))
        label(hero,'Overview',23,FG,True).pack(side='left')
        label(hero,'Manage stores, run safe catalog exports and inspect live activity',11,MUTED).pack(side='right',pady=(9,0))
        metrics=ctk.CTkFrame(body,fg_color='transparent')
        metrics.pack(fill='x',pady=(0,15))
        self.metric_values={}
        for i,(key,heading,color) in enumerate([
            ('products','PRODUCTS DISCOVERED','#55e69a'),
            ('collections','COLLECTIONS MAPPED','#b4e5a4'),
            ('requests','NETWORK REQUESTS','#d1efb6'),
            ('limits','RATE LIMIT EVENTS','#fbbf24')]):
            metrics.grid_columnconfigure(i,weight=1,uniform='metrics')
            card=frame(metrics,PANEL,16)
            card.grid(row=0,column=i,sticky='ew',padx=(0,10 if i<3 else 0))
            label(card,heading,10,MUTED,True).pack(anchor='w',padx=19,pady=(17,5))
            val=label(card,'0',29,color,True)
            val.pack(anchor='w',padx=19,pady=(0,17))
            self.metric_values[key]=val

        controls=frame(body)
        controls.pack(fill='x',pady=(0,14))
        label(controls,'Store workspace',16,FG,True).pack(anchor='w',padx=19,pady=(16,3))
        label(controls,'Configure your template and add storefronts',11,MUTED).pack(anchor='w',padx=19,pady=(0,13))
        row=ctk.CTkFrame(controls,fg_color='transparent')
        row.pack(fill='x',padx=19,pady=(0,9))
        legacy_template = HOME / 'ChotuApp_Seller_Template_Updated_Variants.xlsx'
        bundled_template = Path(__file__).resolve().with_name('ChotuApp_Template.xlsx')
        self.template=tk.StringVar(value=str(legacy_template if legacy_template.is_file() else bundled_template))
        try:
            preferences = json.loads(CONFIG.with_name('chotuapp_preferences.json').read_text(encoding='utf-8'))
            if isinstance(preferences, dict) and isinstance(preferences.get('template'), str):
                self.template.set(preferences['template'])
        except (OSError, ValueError):
            pass
        label(row,'TEMPLATE',10,MUTED,True,width=86,anchor='w').pack(side='left')
        entry(row,self.template).pack(side='left',fill='x',expand=True,padx=(0,9))
        button(row,'Browse file',self.browse,width=125).pack(side='left')
        row=ctk.CTkFrame(controls,fg_color='transparent')
        row.pack(fill='x',padx=19,pady=(0,12))
        self.name=tk.StringVar(value='')
        self.url=tk.StringVar(value='')
        entry(row,self.name,'Brand name',width=220).pack(side='left',padx=(0,9))
        entry(row,self.url,'https://store.example',width=320).pack(side='left',fill='x',expand=True,padx=(0,9))
        button(row,'+ Add store',self.add,primary=True,width=142).pack(side='left')
        bulkrow=ctk.CTkFrame(controls,fg_color='transparent')
        bulkrow.pack(fill='x',padx=19,pady=(0,16))
        label(bulkrow,'BULK IMPORT  ·  URL per line, or Brand | URL',10,MUTED,True).pack(anchor='w',pady=(0,6))
        self.bulk=tk.Text(bulkrow,height=2,wrap='none',bg='#0b1e14',fg=FG,
                insertbackground='white',relief='flat',padx=12,pady=8,
                font=('Segoe UI',11),highlightthickness=1,highlightbackground=EDGE)
        self.bulk.pack(side='left',fill='x',expand=True,padx=(0,9))
        button(bulkrow,'Import list',self.add_bulk,width=130).pack(side='right')

        middle=ctk.CTkFrame(body,fg_color='transparent')
        middle.pack(fill='x',pady=(0,13))
        middle.grid_columnconfigure(0,weight=3)
        middle.grid_columnconfigure(1,weight=1)
        list_panel=frame(middle)
        list_panel.grid(row=0,column=0,sticky='nsew',padx=(0,12))
        label(list_panel,'Connected stores · tap-hold and drag to scroll',15,FG,True).pack(anchor='w',padx=17,pady=(14,8))
        self.store_checks = {}
        self.store_list = ctk.CTkScrollableFrame(list_panel, height=172,
            fg_color='#0b1e14', corner_radius=12,
            scrollbar_button_color='#28513a', scrollbar_button_hover_color=ACCENT)
        self.store_list.pack(fill='both',expand=True,padx=17,pady=(0,10))
        select_tools=ctk.CTkFrame(list_panel,fg_color='transparent')
        select_tools.pack(fill='x',padx=17,pady=(0,12))
        self.selection_label=label(select_tools,'0 stores selected',11,MUTED)
        self.selection_label.pack(side='left')
        button(select_tools,'Select all',self.select_all_stores,width=100).pack(side='right',padx=(7,0))
        button(select_tools,'Clear',self.clear_selected_stores,width=74).pack(side='right')
        status_panel=frame(middle)
        status_panel.grid(row=0,column=1,sticky='nsew')
        label(status_panel,'ENGINE STATUS',10,MUTED,True).pack(anchor='w',padx=18,pady=(17,7))
        self.live_status=label(status_panel,'● READY',17,ACCENT,True,anchor='w',wraplength=240)
        self.live_status.pack(fill='x',padx=18,pady=(0,8))
        self.live_spinner=ttk.Progressbar(status_panel,mode='indeterminate',length=190)
        self.runtime_label=label(status_panel,'SESSION  00:00:00',11,MUTED)
        self.runtime_label.pack(anchor='w',padx=18,pady=(13,13))

        # CHOTUAPP_STICKY_UI_V1: toolbar is pinned below scrollable workspace
        actions=ctk.CTkFrame(root,fg_color='#10271b')
        actions.pack(side='top',fill='x',padx=18,pady=(5,7))
        self.refresh=button(actions,'▶  Refresh all',self.start,primary=True,width=153)
        self.refresh.pack(side='left',padx=(0,8))
        self.refresh_selected=button(actions,'▶  FETCH SELECTED',self.start_selected,width=188)
        self.refresh_selected.pack(side='left',padx=(0,8))
        self.pause_button=button(actions,'⏸ Pause',self.toggle_pause,width=105)
        self.pause_button.configure(state='disabled')
        self.pause_button.pack(side='left',padx=(0,8))
        button(actions,'Remove ticked',self.remove,width=100).pack(side='left',padx=(0,8))
        button(actions,'Open exports',lambda: self.open_folder(OUT),width=137).pack(side='right')
        label(body,'●  DATA SAFETY     Existing exports and checkpoints protected  ·  REVIEW is not FINAL',
              10,MUTED).pack(anchor='w',pady=(0,12))

        monitors=ctk.CTkFrame(body,fg_color='transparent')
        monitors.pack(fill='both',expand=True,pady=(0,13))
        monitors.grid_columnconfigure(0,weight=3)
        monitors.grid_columnconfigure(1,weight=2)
        main_console=frame(monitors)
        side_console=frame(monitors)
        main_console.grid(row=0,column=0,sticky='nsew',padx=(0,12))
        side_console.grid(row=0,column=1,sticky='nsew')
        label(main_console,'Extraction activity',14,FG,True).pack(anchor='w',padx=15,pady=(14,8))
        label(side_console,'Network diagnostics',14,FG,True).pack(anchor='w',padx=15,pady=(14,8))
        self.logbox=tk.Text(main_console,height=11,wrap='word',font=('Consolas',10),
                bg='#07180f',fg='#c8f7d8',insertbackground='#f8fafc',
                relief='flat',padx=12,pady=10)
        self.logbox.pack(fill='both',expand=True,padx=14,pady=(0,14))
        self._chotu_side_console=side_console
        self._chotu_monitor_area=monitors
        self.debug_status=label(side_console,'STAGE: Idle',10,MUTED,anchor='w')
        self.debug_status.pack(fill='x',padx=15,pady=(0,5))
        self.debug_box=tk.Text(side_console,height=9,wrap='word',font=('Consolas',9),
                bg='#07180f',fg='#b6e9c3',insertbackground='#f8fafc',
                relief='flat',padx=12,pady=10)
        self.debug_box.pack(fill='both',expand=True,padx=14,pady=(0,8))
        debug_actions=ctk.CTkFrame(side_console,fg_color='transparent')
        debug_actions.pack(fill='x',padx=14,pady=(0,12))
        button(debug_actions,'Copy log',self.copy_debug,width=104).pack(side='left')
        self.debug_file=Path(__file__).resolve().parent/'debug_logs'/'live_debug.log'
        self.debug_file.parent.mkdir(parents=True,exist_ok=True)
        button(debug_actions,'Open logs',lambda:self.open_folder(self.debug_file.parent),width=105).pack(side='left',padx=(8,0))

        bottom=frame(root)
        bottom.pack(side='bottom',fill='x',padx=18,pady=(4,2))
        label(bottom,'Export progress',13,FG,True).pack(anchor='w',padx=17,pady=(13,7))
        self.progress_value=tk.IntVar(value=0)
        self.progress_bar=ttk.Progressbar(bottom,mode='determinate',maximum=100,variable=self.progress_value)
        self.progress_bar.pack(fill='x',padx=17,pady=(0,8))
        self.progress_label=label(bottom,'Ready — 0%',11,MUTED)
        self.progress_label.pack(anchor='w',padx=17,pady=(0,14))
        self._top20_last_auto=time.monotonic()
        # Unified mouse-wheel router installed once below.
        self.root.after(60000,self._top20_auto_tick)
        self.root.after(1000,self.debug_watchdog)
        self.root.after(250,self._animate_dashboard)
        self.redraw()
        # Pack the scrollable workspace LAST so the bottom toolbar and progress
        # reserve their screen space instead of being pushed below the viewport.
        workspace.pack_forget()
        workspace.pack(fill='both', expand=True)
        self._install_wheel_scrolling(workspace)
        self.root.after(100,self.poll)

    def _apply_green_theme(self):
        style = ttk.Style(self.root)
        style.theme_use('clam')
        style.configure('.', font=('Segoe UI', 10), background='#10271b', foreground='#e2e8f0')
        style.configure('TFrame', background='#10271b')
        style.configure('TLabel', background='#10271b', foreground='#e2e8f0')
        style.configure('TButton', background='#20b86b', foreground='white',
                        borderwidth=0, padding=(13, 9), font=('Segoe UI', 10, 'bold'))
        style.map('TButton', background=[('disabled', '#334155'), ('pressed', '#159450'),
                                          ('active', '#20b86b')],
                  foreground=[('disabled', '#94a3b8')])
        style.configure('TEntry', fieldbackground='#0b1e14', foreground='#e2e8f0',
                        insertcolor='white', padding=7, borderwidth=1)
        style.configure('Horizontal.TProgressbar', troughcolor='#244b34',
                        background='#20b86b', thickness=12)
        style.configure('TPanedwindow', background='#07170f')
        self.root.configure(bg='#07170f')

    def _animate_dashboard(self):
        # Lightweight 4fps heartbeat; no extraction work on the UI thread.
        try:
            self._ui_pulse += 1
            active = str(self.refresh.cget('state')) == 'disabled'
            dot = '●' if self._ui_pulse % 4 < 2 else '◉'
            self.header_clock.configure(text=(dot + '  EXTRACTION ACTIVE') if active else '●  SYSTEM READY',
                                     text_color='#55e69a' if active else '#a2c5ad')
            if active and self._ui_started is not None:
                elapsed = max(0, int(time.monotonic() - self._ui_started))
                self.runtime_label.configure(text='SESSION  {:02d}:{:02d}:{:02d}'.format(
                    elapsed // 3600, (elapsed // 60) % 60, elapsed % 60))
        finally:
            self.root.after(250, self._animate_dashboard)

    def _dashboard_metrics(self, line, debug=False):
        if debug:
            if 'HTTP START attempt=' in line:
                self._ui_request_count += 1
            if 'HTTP END status=429' in line:
                self._ui_429_count += 1
        else:
            m = re.search(r'Catalog page \d+: (\d+) records', line)
            if m:
                self._ui_products += int(m.group(1))
            m = re.search(r'Category mapping: (\d+) collections fetched', line)
            if m:
                self._ui_collections = int(m.group(1))
            m = re.search(r'EXPORT BUILT: (\d+) products', line)
            if m:
                self._ui_products = int(m.group(1))
        self.metric_values['products'].configure(text=f'{self._ui_products:,}')
        self.metric_values['collections'].configure(text=f'{self._ui_collections:,}')
        self.metric_values['requests'].configure(text=f'{self._ui_request_count:,}')
        self.metric_values['limits'].configure(text=f'{self._ui_429_count:,}')

    @staticmethod
    def _trim_console(widget, max_lines=500):
        count = int(widget.index('end-1c').split('.')[0])
        if count > max_lines:
            widget.delete('1.0', f'{count-max_lines+1}.0')

    def copy_debug(self):
        try:
            text = self.debug_file.read_text(encoding='utf-8') if self.debug_file.exists() else self.debug_box.get('1.0', 'end-1c')
        except OSError:
            text = self.debug_box.get('1.0', 'end-1c')
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        self.debug_status.configure(text='Debug log copied (visible lines)')

    def debug_watchdog(self):
        try:
            with _chotu_debug_lock:
                state = dict(_chotu_debug_state)
            if state['request'] and state['started']:
                elapsed = int(time.monotonic() - state['started'])
                self.debug_status.configure(text='STAGE: ' + state['stage'] + ' | HTTP ' + str(elapsed) + 's')
                self._chotu_last_request = state['request']
            else:
                self.debug_status.configure(text='STAGE: ' + state['stage'] + ' | HTTP idle')
            if not hasattr(self, '_chotu_last_watchdog_stage') or self._chotu_last_watchdog_stage != state['stage']:
                self._chotu_last_watchdog_stage = state['stage']
                self.debug_box.insert('end', '[MONITOR] Stage: ' + state['stage'] + '\n')
                self.debug_box.see('end')
                self._trim_console(self.debug_box, 400)
        finally:
            self.root.after(2000, self.debug_watchdog)

    def set_live_status(self, state, detail=''):
        if state == 'working':
            self.live_status.configure(text='● WORKING' + (' — '+detail if detail else ''),text_color='#55e69a')
            self.live_spinner.pack(fill='x',padx=18,pady=(0,3))
            self.live_spinner.start(12)
        else:
            self.live_spinner.stop()
            self.live_spinner.pack_forget()
            color = '#fbbf24' if state == 'review' else '#55e69a' if state == 'completed' else '#f87171'
            word = '● REVIEW REQUIRED' if state == 'review' else '● COMPLETED' if state == 'completed' else '● ERROR'
            self.live_status.configure(text=word + (' — '+detail if detail else ''),text_color=color)

    @staticmethod
    def _output_snapshot(name):
        safe = re.sub(r'[^\w .-]', '', name).strip() or 'Shopify'
        result = {}
        for suffix in ('.xlsx', ' - REVIEW.xlsx', ' - FINAL.xlsx'):
            file = OUT / (safe + suffix)
            if file.is_file():
                stat = file.stat()
                result[str(file)] = (stat.st_mtime_ns, stat.st_size)
        return result

    def _run_checked(self, site, template):
        global _chotu_debug_sink
        name = site['name']
        _chotu_debug_sink = lambda line: self.events.put(('__DEBUG__', line))
        _chotu_debug_stage('Starting ' + name)
        checkpoint_opened = False
        success = False
        try:
            cp = _chotu_open_checkpoint(site['url'], name)
            checkpoint_opened = True
            self.events.put('FRESH FETCH: new run; previous request checkpoints ignored. Products, prices, availability and images fetched again.')
            self.events.put('CHECKPOINT: ' + str(cp) + ' (this run only; restarting Fetch begins from zero)')
            before = self._output_snapshot(name)
            evidence = []
            def log_line(line):
                evidence.append(str(line))
                self.events.put(line)
            run_site(site['url'], name, template, log_line)
            after = self._output_snapshot(name)
            saved = any(after[k] != before.get(k) for k in after)
            announced = any('SAVED REVIEW EXCEL:' in x or x.startswith('COMPLETED: ') for x in evidence)
            if not saved or not announced:
                raise RuntimeError('New Excel was not confirmed in ANAS_DATA_FETCH')
            success = True
            self.events.put(('__JOB_RESULT__', True, name))
        except Exception as exc:
            _chotu_debug('EXCEPTION: ' + repr(exc))
            _chotu_debug(_chotu_traceback.format_exc())
            self.events.put('FAILED: ' + name + ': ' + str(exc))
            self.events.put(('__JOB_RESULT__', False, name))
        finally:
            if checkpoint_opened:
                _chotu_close_checkpoint(success=success)
            _chotu_debug_stage('Idle')
            _chotu_debug_sink = None

    def toggle_pause(self):
        if not self.running:
            return
        if _chotu_pause_gate.is_set():
            _chotu_pause_gate.clear()
            self.pause_button.configure(text='▶ Resume')
            self.set_live_status('working', 'PAUSE REQUESTED — waiting for safe point')
            self.logbox.insert('end', 'PAUSE REQUESTED: will stop at next safe checkpoint; an in-flight HTTP request may finish first.\n')
        else:
            _chotu_pause_gate.set()
            self.pause_button.configure(text='⏸ Pause')
            self.set_live_status('working', 'RESUMED')
            self.logbox.insert('end', 'RESUMED: continuing the current fresh run.\n')

    def open_folder(self, path):
        path = Path(path)
        path.mkdir(parents=True, exist_ok=True)
        try:
            if sys.platform == 'win32':
                os.startfile(str(path))
            else:
                subprocess.Popen(['open' if sys.platform == 'darwin' else 'xdg-open', str(path)])
        except OSError as exc:
            messagebox.showerror('Cannot open folder', str(exc))

    def close(self):
        if self.running and not messagebox.askyesno(
                'Extraction running', 'Close now? Unsaved work stops; saved exports remain. The next fetch starts from zero.'):
            return
        _chotu_pause_gate.set()
        self.root.destroy()

    def _install_wheel_scrolling(self, workspace):
        self._wheel_workspace = workspace
        self._wheel_tag = 'ChotuWheel' + str(id(self))
        for sequence in ('<MouseWheel>', '<Button-4>', '<Button-5>'):
            button = 4 if sequence == '<Button-4>' else 5 if sequence == '<Button-5>' else None
            self.root.bind_class(self._wheel_tag, sequence,
                                 lambda event, button=button: self._route_wheel(event, button))
        self._pan_state = None
        for sequence, callback in (('<ButtonPress-1>', self._pan_start),
                                   ('<B1-Motion>', self._pan_move),
                                   ('<ButtonRelease-1>', self._pan_end)):
            self.root.bind_class(self._wheel_tag, sequence, callback)
        self._tag_wheel_widgets(self.root)

    def _tag_wheel_widgets(self, widget):
        # Run before widget/class/global handlers, including CustomTkinter's
        # nested canvases. Redraw attaches the tag to newly created store rows.
        tags = widget.bindtags()
        widget.bindtags((self._wheel_tag,) + tuple(t for t in tags if t != self._wheel_tag))
        for child in widget.winfo_children():
            self._tag_wheel_widgets(child)

    def _pan_start(self, event):
        node = event.widget
        checkbox = None
        target = None
        while node is not None:
            kind = type(node).__name__
            # Preserve text selection, editable fields, buttons and native
            # scrollbar dragging. Store checkboxes defer clicks until release.
            if isinstance(node, (tk.Text, tk.Entry, tk.Listbox, ttk.Scrollbar)) or kind in (
                    'CTkEntry', 'CTkButton', 'CTkScrollbar', 'Button', 'Scrollbar'):
                self._pan_state = None
                return None
            if kind == 'CTkCheckBox':
                checkbox = node
            if node is self.store_list or node is self.store_list._parent_canvas:
                target = self.store_list._parent_canvas
                break
            if node is self._wheel_workspace or node is self._wheel_workspace._parent_canvas:
                target = self._wheel_workspace._parent_canvas
                break
            node = getattr(node, 'master', None)
        if target is None:
            self._pan_state = None
            return None
        self._pan_state = {'target': target, 'y': event.y_root,
                           'fraction': target.yview()[0], 'moved': False,
                           'checkbox': checkbox}
        return 'break'

    def _pan_move(self, event):
        state = self._pan_state
        if state is None:
            return None
        distance = event.y_root - state['y']
        if abs(distance) >= 5:
            state['moved'] = True
        if state['moved']:
            canvas = state['target']
            region = canvas.tk.splitlist(canvas.cget('scrollregion'))
            if len(region) == 4:
                height = float(region[3]) - float(region[1])
                if height > 0:
                    canvas.yview_moveto(state['fraction'] - distance / height)
        return 'break'

    def _pan_end(self, event):
        state = self._pan_state
        self._pan_state = None
        if state is None:
            return None
        if not state['moved'] and state['checkbox'] is not None:
            state['checkbox'].toggle()
        return 'break'

    def _route_wheel(self, event, button=None):
        node = event.widget
        # Windows delivers MouseWheel to the focused widget, which can be
        # the root or an entry far from the pane under the pointer.
        try:
            hovered = self.root.winfo_containing(event.x_root, event.y_root)
            if hovered is not None and hovered is not self.root:
                node = hovered
        except (tk.TclError, AttributeError):
            pass
        target = None
        while node is not None:
            if isinstance(node, (tk.Text, tk.Listbox)):
                target = node
                break
            if node is self.store_list or node is self.store_list._parent_canvas:
                target = self.store_list._parent_canvas
                break
            if node is self._wheel_workspace or node is self._wheel_workspace._parent_canvas:
                target = self._wheel_workspace._parent_canvas
                break
            node = getattr(node, 'master', None)
        if target is None:
            return None
        num = button if button is not None else getattr(event, 'num', None)
        delta = getattr(event, 'delta', 0)
        if num in (4, 5):
            steps = -3 if num == 4 else 3
        elif delta:
            amount = max(1, int(abs(delta) / 120)) if sys.platform != 'darwin' else max(1, int(abs(delta)))
            steps = -amount * 3 if delta > 0 else amount * 3
        else:
            return None
        # Keep each pane independent even at its boundary; prevent the
        # enclosing canvas from scrolling a second time through bind_all.
        horizontal = bool(getattr(event, 'state', 0) & 1)
        if horizontal:
            target.xview_scroll(steps, 'units')
        else:
            target.yview_scroll(steps, 'units')
        return 'break'

    def browse(self):
        path = filedialog.askopenfilename(filetypes=[('Excel template','*.xlsx')])
        if path:
            self.template.set(path)
            try:
                CONFIG.parent.mkdir(parents=True, exist_ok=True)
                CONFIG.with_name('chotuapp_preferences.json').write_text(
                    json.dumps({'template': path}), encoding='utf-8')
            except OSError as exc:
                messagebox.showwarning('Template preference', 'Selected for this session; could not save preference: ' + str(exc))
    def _selected_indices(self):
        return [i for i, site in enumerate(self.sites)
                if site['url'] in self.store_checks and self.store_checks[site['url']].get()]

    def _selection_changed(self):
        count = len(self._selected_indices())
        self.selection_label.configure(text=f'{count} of {len(self.sites)} stores selected')
        self.refresh_selected.configure(text=f'▶  FETCH SELECTED ({count})',
                                        state='disabled' if self.running else 'normal')

    def select_all_stores(self):
        for var in self.store_checks.values(): var.set(True)
        self._selection_changed()

    def clear_selected_stores(self):
        for var in self.store_checks.values(): var.set(False)
        self._selection_changed()

    def redraw(self):
        import customtkinter as ctk
        selected_urls = {url for url, var in self.store_checks.items() if var.get()}
        for child in self.store_list.winfo_children(): child.destroy()
        self.store_checks = {}
        for i, site in enumerate(self.sites):
            url = site['url']
            var = tk.BooleanVar(value=url in selected_urls)
            self.store_checks[url] = var
            item = ctk.CTkFrame(self.store_list,fg_color='#12301f' if i % 2 == 0 else '#0b1e14',corner_radius=8)
            item.pack(fill='x',pady=2)
            check = ctk.CTkCheckBox(item,text=f"{i+1:02d}   {site['name']}    ·    {url}",
                variable=var,command=self._selection_changed,
                font=ctk.CTkFont(family='Segoe UI',size=12),
                text_color='#e0f7e7',fg_color='#20b86b',hover_color='#159450',
                border_color='#4c9068',checkmark_color='#ffffff',corner_radius=5)
            check.pack(fill='x',padx=12,pady=8)
        self._selection_changed()
        if hasattr(self, '_wheel_tag'):
            self._tag_wheel_widgets(self.store_list)
    def save(self):
        CONFIG.parent.mkdir(parents=True, exist_ok=True)
        CONFIG.write_text(json.dumps(self.sites,indent=2),encoding='utf-8')
    def add(self):
        if self.running:
            messagebox.showinfo('Extraction running', 'Wait for the current extraction before editing stores.')
            return
        name=self.name.get().strip(); url=self.url.get().strip().rstrip('/')
        p=urlparse(url)
        if not name or name=='Brand name' or p.scheme not in ('http','https') or not p.netloc:
            messagebox.showerror('Invalid input','Enter a brand name and full https:// website URL');return
        if any(x['url']==url for x in self.sites):messagebox.showwarning('Duplicate','Website already added');return
        self.sites.append({'name':name,'url':url});self.save();self.redraw()
    def add_bulk(self):
        if self.running:
            messagebox.showinfo('Extraction running', 'Wait for the current extraction before editing stores.')
            return
        lines=self.bulk.get('1.0','end').splitlines()
        added=0; skipped=[]
        existing={x['url'].lower() for x in self.sites}
        for line in lines:
            line=line.strip()
            if not line:continue
            if '|' in line:
                name,url=[part.strip() for part in line.split('|',1)]
            else:
                url=line
                if not url.startswith(('https://','http://')):url='https://'+url
                host=urlparse(url).netloc.lower().removeprefix('www.')
                name=host.split('.')[0].replace('-',' ').title()
            url=url.rstrip('/')
            parsed=urlparse(url)
            if parsed.scheme not in ('https','http') or not parsed.hostname or not name:
                skipped.append(line);continue
            if url.lower() in existing:
                skipped.append(line);continue
            self.sites.append({'name':name,'url':url})
            existing.add(url.lower());added+=1
        if added:self.save();self.redraw();self.bulk.delete('1.0','end')
        messagebox.showinfo('Bulk Add',f'Added: {added}\nSkipped/duplicates: {len(skipped)}')
    def _top20_auto_tick(self):
        # Manual-only operation: no unattended refresh.
        return

    def remove(self):
        if str(self.refresh.cget('state')) == 'disabled': return
        indices = set(self._selected_indices())
        if not indices:
            messagebox.showwarning('Select stores','Tick at least one store to remove.')
            return
        if not messagebox.askyesno('Remove stores',f'Remove {len(indices)} ticked store(s) from the list? Existing Excel files will remain untouched.'):
            return
        self.sites = [site for i,site in enumerate(self.sites) if i not in indices]
        self.store_checks.clear()
        self.save(); self.redraw()

    def start_selected(self):
        if str(self.refresh.cget('state')) == 'disabled': return
        indices = self._selected_indices()
        if not indices:
            messagebox.showwarning('Select stores','Tick one or more stores first.')
            return
        template = self.template.get()
        if not Path(template).is_file():
            messagebox.showerror('Template missing','Choose your original ChotuApp template XLSX')
            return
        chosen = [dict(self.sites[i]) for i in indices]
        self._launch_jobs(chosen, template)

    def _launch_jobs(self, chosen, template):
        if self.running or not chosen:
            return
        self.running = True
        self.job_reviewed = False
        self.refresh.configure(state='disabled')
        self.refresh_selected.configure(state='disabled')
        self.logbox.delete('1.0','end')
        self.progress_value.set(0)
        self.progress_label.configure(text='Starting — 0%')
        _chotu_pause_gate.set()
        self.pause_button.configure(state='normal',text='⏸ Pause')
        self.job_failed=False; self.job_completed=0; self.job_expected=len(chosen)
        self._ui_started=time.monotonic()
        self._ui_products=0; self._ui_collections=0; self._ui_request_count=0; self._ui_429_count=0
        self.set_live_status('working',f'{len(chosen)} selected store(s)')
        def worker():
            try:
                for site in chosen:
                    self.events.put(f"\nREFRESH: {site['name']} — {site['url']}")
                    self._run_checked(site,template)
            except Exception as exc:
                self.events.put('FAILED: worker: ' + str(exc))
                self.events.put(('__JOB_RESULT__', False, 'Worker'))
            finally:
                self.events.put('__DONE__')
        threading.Thread(target=worker,daemon=True).start()

    def start(self):
        if str(self.refresh.cget('state')) == 'disabled': return
        template=self.template.get()
        if not Path(template).is_file():
            messagebox.showerror('Template missing','Choose your original ChotuApp template XLSX')
            return
        if not self.sites:
            messagebox.showerror('No websites','Add a website first')
            return
        self._launch_jobs([dict(site) for site in self.sites],template)

    # CHOTUAPP_PRO_V2_RESPONSIVE_UI
    def poll(self):
        # Drain a bounded batch, combine log writes, and redraw each console once.
        main_lines, debug_lines = [], []
        processed = 0
        try:
            while processed < 350:
                msg = self.events.get_nowait()
                processed += 1
                if msg == '__DONE__':
                    self.running = False
                    if self.job_failed or self.job_completed != self.job_expected:
                        self.set_live_status('error', 'Excel missing / failed')
                        self.progress_label.configure(text='ERROR — check log; close open Excel files')
                    else:
                        self.set_live_status('review' if self.job_reviewed else 'completed',
                                             'Excel saved — review required' if self.job_reviewed else 'Excel saved')
                        self.progress_value.set(100)
                        self.progress_label.configure(text='Saved — REVIEW REQUIRED; check audit reports' if self.job_reviewed else 'Completed — Excel saved')
                    self.refresh.configure(state='normal')
                    self._selection_changed()
                    self.pause_button.configure(state='disabled', text='⏸ Pause')
                    _chotu_pause_gate.set()
                elif isinstance(msg, tuple) and len(msg) == 3 and msg[0] == '__JOB_RESULT__':
                    _, ok, site_name = msg
                    self.job_completed += 1
                    if not ok:
                        self.job_failed = True
                        self.set_live_status('working', 'error in ' + site_name)
                elif isinstance(msg, tuple) and len(msg) == 2 and msg[0] == '__DEBUG__':
                    debug_lines.append(str(msg[1]))
                    self._dashboard_metrics(str(msg[1]), debug=True)
                elif isinstance(msg, str) and msg.startswith('__CHOTU_PROGRESS__|'):
                    _, pct, detail = msg.split('|', 2)
                    self.progress_value.set(int(pct))
                    self.progress_label.configure(text=f'{detail} — {pct}%')
                else:
                    if isinstance(msg, str) and ('REVIEW REQUIRED:' in msg or 'SAVED REVIEW EXCEL:' in msg):
                        self.job_reviewed = True
                    main_lines.append(str(msg))
                    self._dashboard_metrics(str(msg))
        except queue.Empty:
            pass
        if main_lines:
            self.logbox.insert('end', '\n'.join(main_lines) + '\n')
            self._trim_console(self.logbox, 350)
            self.logbox.see('end')
        if debug_lines:
            self.debug_box.insert('end', '\n'.join(debug_lines) + '\n')
            self._trim_console(self.debug_box, 350)
            self.debug_box.see('end')
            try:
                with self.debug_file.open('a', encoding='utf-8') as fh:
                    fh.write('\n'.join(debug_lines) + '\n')
            except OSError:
                pass
        self.root.after(80 if not self.events.empty() else 180, self.poll)

if __name__=='__main__':
    root=tk.Tk();App(root);root.mainloop()
