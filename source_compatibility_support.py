"""Explicit, source-specific failures until Pakistan variant data can be verified."""
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser

def enable_source_compatibility(g):
    if g.get('_chotu_source_compatibility'):return
    original=g['discover']
    def discover(base,log):
        host=(urlsplit(base).hostname or '').lower().removeprefix('www.')
        if host not in ('pk.khaadi.com','khaadi.com','sapphireonline.pk','pk.sapphireonline.pk'):return original(base,log)
        g['_chotu_wait']()
        if host in ('pk.khaadi.com','khaadi.com'):
            response=g['S'].get('https://pk.khaadi.com/',timeout=30)
            actual=(urlsplit(response.url).hostname or '').lower()
            if actual!='pk.khaadi.com':raise RuntimeError('SOURCE BLOCKED: Khaadi Pakistan redirected to '+actual+'. Pakistan locale/currency unverified; foreign storefront prices will not be exported as PKR. Saved work retained.')
            raise RuntimeError('SOURCE BLOCKED: Khaadi uses Salesforce Commerce. A verified Pakistan product/variant adapter or merchant feed is required; no products.json fallback or guessed prices.')
        url='https://pk.sapphireonline.pk/robots.txt';response=g['S'].get(url,timeout=30)
        if response.status_code!=200 or (urlsplit(response.url).hostname or '').lower()!='pk.sapphireonline.pk':raise RuntimeError('SOURCE BLOCKED: Sapphire public source permissions could not be verified; saved work retained.')
        robot=RobotFileParser();robot.parse(response.text.splitlines())
        endpoint='https://pk.sapphireonline.pk/on/demandware.store/Sites-Sapphire-Site/default/Product-Variation'
        if not robot.can_fetch('ChotuAppCatalogRefresh',endpoint):raise RuntimeError('SOURCE BLOCKED: Sapphire public robots rules disallow its variant endpoint. Exact size prices/availability require an approved public feed or source permission; no variant prices or stock guessed.')
        raise RuntimeError('SOURCE BLOCKED: Sapphire uses Salesforce Commerce; variant response format still requires verification before export. Existing files retained.')
    g['discover']=discover;g['_chotu_source_compatibility']=True
