"""Use Farda's explicitly linked ordering shop, after validating its catalog."""
from urllib.parse import urlsplit
import time

SHOP='https://shop.fardafoods.com'

def validate_catalog(data):
    if not isinstance(data,dict) or not isinstance(data.get('products'),list):
        raise RuntimeError('Farda ordering shop did not return a compatible public Shopify catalog. Existing Excel retained; source adapter needs verification.')
    products=data['products']
    if not products:
        raise RuntimeError('Farda ordering shop returned zero public products. Existing Excel retained; no empty catalog published.')
    for p in products:
        if not isinstance(p,dict) or p.get('id') is None or not p.get('handle') or not isinstance(p.get('variants'),list) or not p['variants']:
            raise RuntimeError('Farda shop catalog has an unsupported product schema; no export produced.')
        for v in p['variants']:
            if not isinstance(v,dict) or v.get('id') is None or 'price' not in v or not isinstance(v.get('available'),bool):
                raise RuntimeError('Farda shop variant price/availability schema is incomplete; no export produced.')
    return products


def enable_farda_source(g):
    if g.get('_chotu_farda_source'):return
    original=g['run_site']
    def run_site(base,name,template,log):
        host=(urlsplit(base).hostname or '').lower().removeprefix('www.')
        if host not in ('fardafoods.com','shop.fardafoods.com'):return original(base,name,template,log)
        # The homepage's Shop Now link points here. Never guess another host.
        target=SHOP
        log('FARDA SOURCE: using official Shop Now destination '+target+'; validating public product catalog.')
        tls=g['_chotu_tls'];gate=getattr(tls,'fast_gate',None)
        if gate is not None:
            with gate.lock:
                recent_limit=getattr(gate,'limited',False) or time.time()<getattr(gate,'recovery_not_before',0) or gate.interval>1.0
                gate.baseline=max(0.5,gate.baseline);gate.interval=max(0.5,gate.interval)
            tls.fast_worker_count=1 if recent_limit else 2
            log('FARDA FETCH: '+str(tls.fast_worker_count)+' workers; shared '+format(gate.interval,'.2f')+'s request spacing; price and full-page checks preserved.')
        data=g['get_json'](target+'/products.json?limit=250&page=1')
        products=validate_catalog(data)
        log('FARDA SOURCE VERIFIED: '+str(len(products))+' products on first catalog page; existing price, variant, image and pagination checks follow.')
        # No data mapping, price conversion, workbook write or schema changes here.
        # The canonical pipeline reuses the same durable page-1 API checkpoint.
        return original(target,name,template,log)
    g['run_site']=run_site;g['_chotu_farda_source']=True
