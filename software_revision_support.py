"""Identify installed Python code and invalidate derived data across code updates."""
import hashlib,json,os,sys,tempfile
from pathlib import Path


def installed_revision(engine):
    engine=Path(engine).resolve();digest=hashlib.sha256()
    paths=[engine]+[p for p in sorted(engine.parent.glob('*.py')) if p!=engine and not p.name.startswith(('main_before_', 'backup_', 'diagnose_', 'install_', 'rollback_', 'capture_'))]
    for path in paths:
        digest.update(path.name.encode());digest.update(b'\0');digest.update(path.read_bytes());digest.update(b'\0')
    return digest.hexdigest()[:16]


def prepare_revision(engine,folder):
    revision=installed_revision(engine);folder=Path(folder);record=folder/'software_revision.json';previous=None
    if record.exists():
        try:previous=json.loads(record.read_text(encoding='utf-8')).get('revision')
        except (ValueError,OSError):pass
    # Cached HTTP responses remain intact; only derived Webx parsing is versioned.
    module=sys.modules.get('czone_source_support')
    if module is not None:
        base=getattr(module,'_revision_base_parser_version',module.PARSER_VERSION)
        module._revision_base_parser_version=base;module.PARSER_VERSION=base+'@'+revision
    fd,name=tempfile.mkstemp(prefix='.revision-',dir=folder)
    try:
        with os.fdopen(fd,'w',encoding='utf-8') as stream:
            json.dump({'revision':revision},stream);stream.flush();os.fsync(stream.fileno())
        os.replace(name,record)
    finally:Path(name).unlink(missing_ok=True)
    return revision,previous
