"""Bounded, checksummed checkpoint parts; preserves legacy checkpoint.zip support."""
import hashlib,json,re,shutil,tempfile,zipfile
from contextlib import contextmanager
from pathlib import Path
MAX_ARCHIVE=8*1024**3
MAX_PARTS=64
PART_BYTES=250*1024**2

def split_archive(source,folder,part_bytes=PART_BYTES,max_bytes=MAX_ARCHIVE):
    source=Path(source);folder=Path(folder)
    if source.stat().st_size>max_bytes:raise ValueError('Checkpoint exceeds bounded compressed safety limit; outputs remain available')
    if shutil.disk_usage(source.parent).free<source.stat().st_size+256*1024**2:raise ValueError('Insufficient disk space to split checkpoint; original work retained')
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
    if manifest.get('version')!=1 or not isinstance(parts,list) or not 1<=len(parts)<=MAX_PARTS or not isinstance(total,int) or not 0<total<=MAX_ARCHIVE:raise ValueError('Invalid multipart checkpoint manifest')
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

class _PartSink:
    def __init__(self,folder,part_bytes,max_bytes,reserve):
        self.folder=folder;self.part_bytes=part_bytes;self.max_bytes=max_bytes;self.reserve=reserve
        self.total=0;self.size=0;self.stream=None;self.records=[];self.digest=None
    def tell(self):return self.total
    def seek(self,*args):raise OSError('Streaming checkpoint is not seekable')
    def flush(self):
        if self.stream:self.stream.flush()
    def _finish_part(self):
        if self.stream:
            self.stream.flush();self.stream.close();self.stream=None
            self.records.append(dict(name='part-'+str(len(self.records)).zfill(4)+'.bin',bytes=self.size,sha256=self.digest.hexdigest()))
    def write(self,data):
        if self.total+len(data)>self.max_bytes:raise ValueError('Checkpoint exceeds bounded compressed safety limit; prior checkpoint retained')
        view=memoryview(data)
        while view:
            if self.stream is None or self.size==self.part_bytes:
                self._finish_part()
                if len(self.records)>=MAX_PARTS:raise ValueError('Checkpoint part count exceeds safety bound')
                if shutil.disk_usage(self.folder).free<min(self.part_bytes,self.max_bytes-self.total)+self.reserve:raise ValueError('Insufficient disk space for checkpoint part; prior checkpoint retained')
                self.size=0;self.digest=hashlib.sha256();self.stream=(self.folder/('part-'+str(len(self.records)).zfill(4)+'.bin')).open('wb')
            chunk=view[:self.part_bytes-self.size];self.stream.write(chunk);self.digest.update(chunk);self.size+=len(chunk);self.total+=len(chunk);view=view[len(chunk):]
        return len(data)
    def close(self):
        if self.stream:self.stream.close();self.stream=None

@contextmanager
def archive_writer(destination,part_bytes=PART_BYTES,max_bytes=MAX_ARCHIVE,reserve=256*1024**2):
    """Write ZIP bytes directly into immutable parts, without a second full copy."""
    destination=Path(destination)
    if not isinstance(part_bytes,int) or not 0<part_bytes<=PART_BYTES or not 0<max_bytes<=MAX_ARCHIVE:raise ValueError('Invalid checkpoint bounds')
    destination.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.checkpoint-',dir=destination.parent) as tmp:
        folder=Path(tmp)/'parts';folder.mkdir();sink=_PartSink(folder,part_bytes,max_bytes,reserve)
        try:
            with zipfile.ZipFile(sink,'w',zipfile.ZIP_DEFLATED,compresslevel=1) as archive:yield archive
            sink._finish_part()
            if sink.total<=part_bytes:
                (folder/sink.records[0]['name']).replace(destination)
            else:
                (folder/'manifest.json').write_text(json.dumps(dict(version=1,total_bytes=sink.total,parts=sink.records),indent=2))
                target=destination.with_suffix('.parts');backup=Path(tmp)/'previous'
                if target.is_symlink():raise ValueError('Checkpoint output cannot be a symlink')
                if target.exists():target.replace(backup)
                try:folder.replace(target)
                except Exception:
                    if backup.exists() and not target.exists():backup.replace(target)
                    raise
                destination.unlink(missing_ok=True)
        finally:sink.close()
