"""Select a runner's queue and reindex only its restored checkpoint copy."""
import copy,re,shutil,uuid
from pathlib import Path
from urllib.parse import urlsplit
from resume_support import RunStore

def partition(data,sites):
    data=Path(data).resolve();store=RunStore(data/'saved_runs');state=store.load()
    if not state:raise ValueError('No restored queue')
    if not 1<=len(sites)<=3:raise ValueError('A runner accepts at most three selected stores')
    def key(s):
        host=(urlsplit(str(s['url'])).hostname or '').lower().removeprefix('www.')
        if host=='sapphireonline.pk':host='pk.sapphireonline.pk'
        return str(s['name']).casefold(),host
    requested={key(s) for s in sites}
    if len(requested)!=len(sites) or len({key(s)[1] for s in sites})!=len(sites):raise ValueError('Duplicate selected stores')
    selected=[(i,s) for i,s in enumerate(state['sites']) if key(s) in requested]
    if len(selected)!=len(sites):raise ValueError('Selected group does not match saved queue')
    oldid=str(state.get('id',''))
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,80}',oldid):raise ValueError('Invalid saved state ID')
    old=store.root/oldid;newid=uuid.uuid4().hex;new=store.root/newid;new.mkdir()
    template=old/'template.xlsx'
    if not template.is_file():template=data/'template.xlsx'
    if not template.is_file():raise ValueError('Saved template missing')
    shutil.copy2(template,new/'template.xlsx')
    for target,(original,site) in enumerate(selected):
        cache=old/str(original)
        if cache.exists():shutil.copytree(cache,new/str(target))
    result=copy.deepcopy(state);result.update(id=newid,sites=[copy.deepcopy(s) for _,s in selected],template=str(new/'template.xlsx'),status='incomplete')
    store.save(result)
    # Only this ephemeral restored runner copy is pruned. The parent artifact remains intact.
    if old.is_dir():shutil.rmtree(old)
    retained={Path((s.get('output') or {}).get('path','')).name for _,s in selected}
    for s in state['sites']:
        name=Path((s.get('output') or {}).get('path','')).name
        if name and name not in retained:
            p=data/'ANAS_DATA_FETCH'/name
            if p.is_file() and p.suffix.lower()=='.xlsx':p.unlink()
    (data/'ANAS_DATA_FETCH'/'run-summary.json').unlink(missing_ok=True)
    print('Restored group: '+', '.join(s['name'] for s in result['sites'])+'; source caches reindexed without refetching.')
    return result
