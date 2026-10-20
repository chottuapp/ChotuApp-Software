"""Explicit original-store opt-in: phone Khaadi -> Rule 804 -> checked Drive copy."""
import hashlib,json,re,tempfile
from pathlib import Path
from rule804_pipeline import process
ROOT=Path(__file__).resolve().parents[1]
MARKER='catalog-inputs/khaadi-mobile/latest.json'

def input_file(root):
 marker=root/MARKER
 if not marker.exists():return None
 data=json.loads(marker.read_text(encoding='utf-8'))
 path=str(data.get('input_path',''));sha=str(data.get('sha256',''))
 if data.get('store')!='Khaadi' or not re.fullmatch('[0-9a-f]{64}',sha) or path!='catalog-inputs/khaadi-mobile/'+sha[:16]+'/Khaadi.xlsx':raise ValueError('Invalid mobile Khaadi input identity')
 source=root/path
 if not source.resolve().is_relative_to(root.resolve()) or not source.is_file() or source.stat().st_size>32*1024*1024:raise ValueError('Mobile workbook unavailable or outside size/path limit')
 if hashlib.sha256(source.read_bytes()).hexdigest()!=sha:raise ValueError('Mobile workbook checksum mismatch')
 return source,sha

def upload(state,folder,rc,*,root=ROOT):
 supplied=input_file(root)
 if supplied is None:return False
 source,sha=supplied
 revision=hashlib.sha256(b''.join((root/p).read_bytes() for p in ('cloud/rule804_pipeline.py','subcategory_inference_support.py','catalog-tools/complete_rule804_batch.py','cloud/confirmed-shop-codes.json','cloud/mobile_khaadi_ingest.py'))).hexdigest()
 previous=state.setdefault('original_uploads',{}).get('Khaadi',{})
 if previous.get('source_sha256')==sha and previous.get('pipeline_revision')==revision and previous.get('folder')==folder:return False
 codes=json.loads((root/'cloud/confirmed-shop-codes.json').read_text())
 with tempfile.TemporaryDirectory() as tmp:
  out=Path(tmp)/'Khaadi.xlsx'
  record=process(source,out,'Khaadi',codes,mobile_khaadi=True)
  # Never stage the raw input. Check processed output on Drive before recording success.
  remote='chotudrive:'+folder
  rc('copy',str(out.parent),remote,'--include','Khaadi.xlsx','--checksum')
  rc('check',str(out.parent),remote,'--include','Khaadi.xlsx','--one-way')
  record.update(source_sha256=sha,pipeline_revision=revision,folder=folder,coverage='Public default-page discovery; full catalog coverage unverified')
  state['original_uploads']['Khaadi']=record
 return True
