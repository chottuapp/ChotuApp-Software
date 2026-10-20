"""Bundle reviewed extractor sources with only desktop GUI imports removed."""
import ast,hashlib,json,shutil,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];DEST=ROOT/'android/app/src/main/python/engine'
def prepare():
 import importlib.util
 spec=importlib.util.spec_from_file_location('worker',ROOT/'catalog-tools/start_khaadi_local_fetch_windows.py');worker=importlib.util.module_from_spec(spec);spec.loader.exec_module(worker)
 DEST.mkdir(parents=True,exist_ok=True)
 for name,sha in worker.FILES.items():
  payload=(ROOT/name).read_bytes()
  if hashlib.sha256(payload).hexdigest()!=sha:raise ValueError('Reviewed source changed: '+name)
  target=DEST/name;target.parent.mkdir(parents=True,exist_ok=True)
  if name=='main.py':
   tree=ast.parse(payload);remove=[n for n in tree.body if isinstance(n,ast.Import) and any(a.name=='tkinter' for a in n.names) or isinstance(n,ast.ImportFrom) and n.module=='tkinter']
   lines=payload.decode().splitlines(True)
   for node in remove:
    lines[node.lineno-1]='tk = ttk = filedialog = messagebox = None\n'
    for i in range(node.lineno,node.end_lineno):lines[i]=''
   payload=''.join(lines).encode()
  target.write_bytes(payload)
 shutil.copytree(ROOT/'tests/fixtures/khaadi_public',DEST/'test-fixtures',dirs_exist_ok=True)
 (DEST/'reviewed-release.json').write_text(json.dumps({'worker_revision':worker.REVISION,'desktop_gui_removed':True}))
 shutil.copy2(ROOT/'catalog-tools/start_khaadi_local_fetch_windows.py',DEST/'approved_worker.py')
 with zipfile.ZipFile(ROOT/'android/app/src/main/assets/engine.zip','w',zipfile.ZIP_DEFLATED) as archive:
  for path in DEST.rglob('*'):
   if path.is_file() and '__pycache__' not in path.parts:archive.write(path,str(path.relative_to(DEST)))
if __name__=='__main__':prepare()
