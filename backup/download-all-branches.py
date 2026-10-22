"""Download immutable GitHub branch snapshots recorded in this backup; no credentials needed."""
import json,urllib.request,hashlib
from pathlib import Path
root=Path(__file__).resolve().parent
refs=json.loads((root/'repository-refs.json').read_text())
folder=root/'branch-archives';folder.mkdir(exist_ok=True)
for name,sha in refs.items():
 target=folder/(name+'.zip')
 if target.exists():print('Already present:',target.name);continue
 print('Downloading:',name,flush=True)
 temporary=target.with_suffix('.zip.part')
 urllib.request.urlretrieve('https://codeload.github.com/chottuapp/ChotuApp-Software/zip/'+sha,temporary)
 temporary.replace(target)
 with target.open('rb') as stream:digest=hashlib.file_digest(stream,'sha256').hexdigest()
 target.with_suffix('.zip.sha256').write_text(digest+'  '+target.name+'\n')
print('All recorded branch snapshots downloaded. Runtime Actions secrets and device caches are not in Git.')
