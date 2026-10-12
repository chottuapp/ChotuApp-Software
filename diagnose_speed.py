"""Read-only ChotuApp performance diagnostic. Does not import or control the app."""
from pathlib import Path
from collections import Counter
from urllib.parse import urlsplit
from datetime import datetime
import importlib.metadata
import hashlib
import json
import os
import platform
import re
import statistics
import subprocess
import sys


def redact(line):
    # Report host and endpoint type, never query strings or URL credentials.
    def replace(match):
        try:
            parts=urlsplit(match.group(0))
            path=parts.path
            kind='product.js' if path.endswith('.js') else 'products.json' if path.endswith('/products.json') else 'collections.json' if path.endswith('/collections.json') else 'page'
            return '['+(parts.hostname or 'host')+'/'+kind+']'
        except ValueError:
            return '[URL]'
    return re.sub(r'https?://[^\s<>]+',replace,line)


def diagnose(root):
    root=Path(root)
    print('CHOTUAPP SPEED DIAGNOSTIC — READ ONLY')
    print('Python:',platform.python_version(),'OS:',platform.system(),platform.release())
    source=root/'main.py'
    if source.is_file():
        data=source.read_bytes()
        text=data.decode('utf-8-sig',errors='replace')
        version=re.search(r"root\.title\(['\"]([^'\"]+)",text)
        print('Installed title:',version.group(1) if version else 'unknown')
        print('Source SHA256:',hashlib.sha256(data).hexdigest()[:16])
        print('Configured request pacing:', '1.5s baseline' if 'adaptive_pace' in text and '1.5' in text else 'inspect source')
    else:print('main.py not found at selected installation')
    for package in ('requests','customtkinter','openpyxl','beautifulsoup4'):
        try:print(package+':',importlib.metadata.version(package))
        except importlib.metadata.PackageNotFoundError:print(package+': not installed in this Python')
    log=root/'debug_logs'/'live_debug.log'
    if not log.is_file():
        print('Debug log not found. Share the current app console instead.')
        return
    size=log.stat().st_size
    with log.open('rb') as stream:
        start=max(0,size-2*1024*1024)
        stream.seek(start)
        raw=stream.read()
    text=raw.decode('utf-8',errors='replace')
    if start:text=text.partition('\n')[2]
    lines=text.splitlines()
    print('Log last update (machine local time):',datetime.fromtimestamp(log.stat().st_mtime).isoformat(timespec='seconds'))
    print('Scope: last 2 MiB of log; cumulative log may include previous runs.')
    markers=[i for i,line in enumerate(lines) if 'STAGE: Starting ' in line]
    current=lines[markers[-1]:] if markers else lines
    print('Most recent store marker:',redact(current[0]) if current else 'none')
    status=Counter();durations=[];hosts=Counter();endpoints=Counter()
    for line in current:
        match=re.search(r'HTTP END status=(\S+) elapsed=([\d.]+)s',line)
        if match:
            status[match.group(1)]+=1
            durations.append(float(match.group(2)))
            url=re.search(r'https?://\S+',line)
            if url:
                try:
                    p=urlsplit(url.group(0));hosts[p.hostname]+=1
                    kind='product.js' if p.path.endswith('.js') else 'collection-products.json' if '/collections/' in p.path and p.path.endswith('products.json') else 'catalog-products.json' if p.path.endswith('/products.json') else 'collections.json' if p.path.endswith('/collections.json') else 'other'
                    endpoints[kind]+=1
                except ValueError:pass
    print('Current-store logged HTTP results:',json.dumps(dict(status)))
    print('Logged endpoints:',json.dumps(dict(endpoints)))
    print('Hosts:',json.dumps(dict(hosts)))
    if durations:
        ordered=sorted(durations)
        print('Logged response times seconds: mean',round(statistics.mean(durations),2),'p95',ordered[min(len(ordered)-1,int(len(ordered)*.95))],'max',max(ordered))
    print('Note: page/image/ranking requests are not all timed by this version; counts are not total requests.')
    print('Recent stages:')
    for line in [line for line in lines if 'STAGE:' in line][-10:]:print(redact(line))
    print('Recent rate-limit/pacing messages:')
    for line in [line for line in current if 'ADAPTIVE SPEED:' in line or 'RATE LIMIT:' in line][-12:]:print(redact(line))
    print('Recent request activity:')
    for line in [line for line in current if 'HTTP START' in line or 'HTTP END' in line][-16:]:print(redact(line))
    if platform.system()=='Windows':
        result=subprocess.run(['tasklist','/FI','IMAGENAME eq python.exe'],capture_output=True,text=True,errors='replace')
        print('Python process memory (no command lines):');print(result.stdout.strip())
    print('END DIAGNOSTIC — application and its files were not changed.')


if __name__=='__main__':
    root=Path(sys.argv[1]) if len(sys.argv)>1 else Path.home()/'Desktop'/'ChotuApp_Software'
    diagnose(root)
