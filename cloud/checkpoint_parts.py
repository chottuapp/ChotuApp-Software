"""Bounded, checksummed checkpoint parts; preserves legacy checkpoint.zip support."""
import hashlib,json,re,shutil,tempfile
from contextlib import contextmanager
from pathlib import Path
MAX_ARCHIVE=2*1024**3
PART_BYTES=250*1024**2

def split_archive(source,folder,part_bytes=PART_BYTES,max_bytes=MAX_ARCHIVE):
    source=Path(source);folder=Path(folder)
    if source.stat().st_size>max_bytes:raise ValueError('Checkpoint exceeds 2 GB compressed safety limit; outputs remain available')
    folder.mkdir(parents=True,exist_ok=True);records=[]
    with source.open('rb') as incoming:
        index=0
        while True:
            block=incoming.read(part_bytes)
            if not block:break
            name='part-'+str(index).zfill(4)+'.bin';index+=1
            (folder/name).write_bytes(block);records.append({'name':name,'bytes':len(block),'sha256':hashlib.sha256(block).hexdigest()})
    (folder/'manifest.json').write_text(json.dumps({'version':1,'total_bytes':source.stat().st_size,'parts':records},indent=2))
    return folder

@contextmanager
def archive_path(path):
    path=Path(path)
    if path.is_file():yield path;return
    if (path/'checkpoint.zip').is_file():yield path/'checkpoint.zip';return
    folder=path/'checkpoint.parts' if (path/'checkpoint.parts').is_dir() else path
    manifest=json.loads((folder/'manifest.json').read_text())
    parts=manifest.get('parts',[]);total=manifest.get('total_bytes')
    if manifest.get('version')!=1 or not isinstance(parts,list) or not 1<=len(parts)<=16 or not isinstance(total,int) or not 0<total<=MAX_ARCHIVE:raise ValueError('Invalid multipart checkpoint manifest')
    if sum(p.get('bytes',0) for p in parts)!=total:raise ValueError('Checkpoint byte count mismatch')
    if shutil.disk_usage(folder).free<total+256*1024**2:raise ValueError('Insufficient disk space to assemble checkpoint')
    with tempfile.TemporaryDirectory(prefix='chotu-checkpoint-',dir=folder.parent) as tmp:
        target=Path(tmp)/'checkpoint.zip'
        with target.open('wb') as outgoing:
            for index,part in enumerate(parts):
                if part.get('name')!='part-'+str(index).zfill(4)+'.bin' or not isinstance(part.get('bytes'),int) or not 0<part['bytes']<=PART_BYTES or not re.fullmatch('[0-9a-f]{64}',str(part.get('sha256',''))):raise ValueError('Unsafe checkpoint part')
                source=folder/part['name']
                if source.is_symlink() or source.stat().st_size!=part['bytes']:raise ValueError('Checkpoint part size mismatch')
                digest=hashlib.sha256()
                with source.open('rb') as stream:
                    while True:
                        block=stream.read(1024**2)
                        if not block:break
                        outgoing.write(block);digest.update(block)
                if digest.hexdigest()!=part['sha256']:raise ValueError('Checkpoint part checksum mismatch')
        yield target
