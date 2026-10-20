"""Read v2 signer certificate fingerprints after apksigner has verified the APK."""
import hashlib,struct
from pathlib import Path

def lp(data,offset=0,width=4):
 if offset+width>len(data):raise ValueError('Truncated APK signing block')
 size=int.from_bytes(data[offset:offset+width],'little');start=offset+width;end=start+size
 if end>len(data):raise ValueError('Invalid APK signing block length')
 return data[start:end],end

def fingerprints(path):
 data=Path(path).read_bytes();eocd=data.rfind(b'PK\x05\x06')
 if eocd<0 or eocd+22>len(data) or eocd+22+int.from_bytes(data[eocd+20:eocd+22],'little')!=len(data):raise ValueError('Invalid APK end record')
 central=int.from_bytes(data[eocd+16:eocd+20],'little')
 if central<32 or data[central-16:central]!=b'APK Sig Block 42':raise ValueError('APK v2 signing block missing')
 size=int.from_bytes(data[central-24:central-16],'little');start=central-size-8
 if start<0 or int.from_bytes(data[start:start+8],'little')!=size:raise ValueError('APK signing block size mismatch')
 pairs=data[start+8:central-24];offset=0;certs=set()
 while offset<len(pairs):
  pair,offset=lp(pairs,offset,8)
  if len(pair)<4:raise ValueError('Invalid APK signing pair')
  if int.from_bytes(pair[:4],'little')!=0x7109871a:continue
  signers,_=lp(pair[4:]);position=0
  while position<len(signers):
   signer,position=lp(signers,position);signed,_=lp(signer);digests,next_field=lp(signed);certificates,_=lp(signed,next_field);certificate,_=lp(certificates)
   if not certificate:raise ValueError('Empty signer certificate')
   certs.add(hashlib.sha256(certificate).hexdigest())
 if not certs:raise ValueError('No APK v2 signer certificates')
 return sorted(certs)
