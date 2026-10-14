"""Read the last selected-store log segment without changing app files."""
import argparse
from collections import deque
from pathlib import Path
import re
from urllib.parse import urlsplit


def redact_urls(text):
    def clean(match):
        try:
            parsed=urlsplit(match.group(0));return '['+(parsed.hostname or 'URL')+parsed.path+']'
        except ValueError:return '[URL]'
    return re.sub(r'https?://[^\s<>]+',clean,text)


def extract(path,name,limit=160):
    active=False;found=False;tail=deque(maxlen=limit);head=[]
    with Path(path).open(encoding='utf-8',errors='replace') as stream:
        for raw in stream:
            line=raw.rstrip('\r\n')
            marker=re.search(r'STAGE: Starting (.+)$',line)
            if marker:
                active=marker.group(1).strip().casefold()==name.casefold()
                if active:found=True;tail.clear();head=[]
            if active:
                tail.append(line)
                if len(head)<8:head.append(line)
    return found,head,list(tail)


def diagnose(root,name):
    print('CHOTUAPP STORE FAILURE DIAGNOSTIC — READ ONLY')
    path=Path(root)/'debug_logs/live_debug.log'
    if not path.is_file():print('Debug log missing at this installation.');return
    found,head,tail=extract(path,name)
    if not found:print('No starting marker found for '+name+'. Share the app main log FAILED line.');return
    print('Store:',name,'(latest matching segment; may belong to an earlier run)')
    if tail and head and tail[0]!=head[0]:
        print('\n'.join(redact_urls(line) for line in head));print('... last 160 lines follow ...')
    print('\n'.join(redact_urls(line) for line in tail))
    print('END STORE DIAGNOSTIC — no application data changed.')

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--target',type=Path,default=Path.home()/'Desktop'/'ChotuApp_Software')
    parser.add_argument('--store',default='Shop Modest');args=parser.parse_args()
    diagnose(args.target,args.store)
