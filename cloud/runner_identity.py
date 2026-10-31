"""Refuse named single-source runners restored from another store's checkpoint."""
from urllib.parse import urlsplit
SINGLE={'laam':{'laam.com'},'khaadi':{'pk.khaadi.com','khaadi.com'},'sapphire':{'pk.sapphireonline.pk','sapphireonline.pk'}}
def validate_runner_sources(state,group):
    group=str(group or '').strip()
    if not group:return
    actual={(urlsplit(str(site.get('url',''))).hostname or '').lower().removeprefix('www.') for site in state.get('sites',[])}
    for name,hosts in SINGLE.items():
        if group=='solo-'+name or group.endswith('-'+name):
            if len(state.get('sites',[]))!=1 or not actual<=hosts:
                raise ValueError('RUNNER CHECKPOINT MISMATCH: '+group+' expects only '+name+'; restored stores: '+', '.join(str(s.get('name','')) for s in state.get('sites',[]))+'. No fetching started; select the correct checkpoint or explicitly partition it.')
            return


def paused_sources(sites):
    import json
    from pathlib import Path
    registry=json.loads((Path(__file__).resolve().parent/'fetch-update-release.json').read_text())['fresh_stores']
    from locked_store_rules import OWNER_PAUSED_STORES,owner_paused
    paused={r['name'] for r in registry if r.get('enabled',True) is False}|OWNER_PAUSED_STORES
    return {s.get('name') for s in sites if s.get('name') in paused or owner_paused(url=s.get('url',''))}
