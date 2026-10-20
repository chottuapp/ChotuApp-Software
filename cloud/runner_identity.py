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
