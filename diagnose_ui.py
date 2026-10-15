"""Read-only Windows hang diagnostic. Does not launch or modify ChotuApp."""
import ast
import collections
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys


def inspect_source(folder):
    main=folder/'main.py'
    if not main.is_file():
        print('Installed main.py not found at the expected Desktop folder.');return
    data=main.read_bytes();source=data.decode('utf-8-sig')
    print('Main SHA256:',hashlib.sha256(data).hexdigest()[:16])
    try:
        tree=ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute) and node.func.attr=='title' and node.args and isinstance(node.args[0],ast.Constant):
                print('Base title:',node.args[0].value);break
        print('Main syntax: OK')
    except SyntaxError as exc:print('Main syntax error:',exc.msg,'line',exc.lineno)
    for label,marker in [('Saved Runs','CHOTUAPP_DURABLE_RUNS_V1'),('Fast Fetch','CHOTUAPP_CONTROLLED_FAST_V1'),('Smooth UI hook','CHOTUAPP_RESPONSIVE_UI_V1')]:
        print(label+':',marker in source)
    for name in ('responsive_ui_support.py','fast_fetch_support.py','resume_support.py'):
        path=folder/name
        if path.is_file():
            payload=path.read_bytes();body=payload.decode('utf-8-sig')
            print(name,'SHA256='+hashlib.sha256(payload).hexdigest()[:16])
            if name=='responsive_ui_support.py':
                print('UI details: Configure binding=',"'<Configure>'" in body,'deferred widget wrappers=','class QuietLabel:' in body)
            if name=='fast_fetch_support.py':
                worker=re.search(r'tls\.fast_worker_count=(\d+)',body)
                print('Workers:',worker.group(1) if worker else 'unknown')
    log=folder/'debug_logs'/'live_debug.log'
    if log.is_file():
        with log.open('rb') as stream:
            stream.seek(max(0,log.stat().st_size-128*1024));tail=stream.read().decode('utf-8',errors='replace')
        statuses=collections.Counter(re.findall(r'HTTP END status=(\S+)',tail))
        print('Recent log HTTP statuses (last 128 KiB):',json.dumps(statuses))
        times=re.findall(r'^\[([^\]]+)\]',tail,re.M)
        print('Recent log time range:',times[0] if times else 'unknown','to',times[-1] if times else 'unknown')
        print('Recent logged UI/trace errors:',len(re.findall(r'Traceback|TclError|Exception in Tkinter callback',tail)))
        print('Note: CMD-only errors may not be recorded in this log.')


def windows_samples():
    # No command lines, storefront lists, credentials, or workbook contents are collected.
    script=r'''
$ErrorActionPreference='Stop'
for($sample=0;$sample -lt 3;$sample++) {
  $processes=@(Get-Process -Name python,pythonw -ErrorAction SilentlyContinue | ForEach-Object {
    [pscustomobject]@{pid=$_.Id;responding=$_.Responding;cpu_seconds=$_.CPU;memory_mb=[math]::Round($_.WorkingSet64/1MB,1);handles=$_.HandleCount;threads=$_.Threads.Count;is_chotu_window=($_.MainWindowTitle -like '*ChotuApp*')}
  })
  $os=Get-CimInstance Win32_OperatingSystem
  [pscustomobject]@{sample=$sample;utc=[DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds();free_memory_mb=[math]::Round($os.FreePhysicalMemory/1024);total_memory_mb=[math]::Round($os.TotalVisibleMemorySize/1024);processes=$processes} | ConvertTo-Json -Depth 5 -Compress
  if($sample -lt 2){Start-Sleep -Seconds 3}
}
'''
    try:
        result=subprocess.run(['powershell','-NoProfile','-NonInteractive','-Command',script],capture_output=True,text=True,timeout=30)
    except (OSError,subprocess.TimeoutExpired) as exc:
        print('Process sampling unavailable:',type(exc).__name__);return
    if result.returncode:
        print('Windows process sampling failed; exit code',result.returncode);return
    previous={}
    for line in result.stdout.splitlines():
        try:sample=json.loads(line)
        except ValueError:continue
        print('WINDOWS SAMPLE:',json.dumps(sample))
        for proc in sample.get('processes') or []:
            pid=proc['pid'];old=previous.get(pid)
            if old and proc.get('cpu_seconds') is not None and old[1] is not None:
                wall=(sample['utc']-old[0])/1000
                if wall>0:print('CPU core usage PID',pid,':',round(100*(proc['cpu_seconds']-old[1])/wall,1),'% (100% = one logical CPU)')
            previous[pid]=(sample['utc'],proc.get('cpu_seconds'))


def main():
    print('CHOTUAPP UI DIAGNOSTIC — READ ONLY')
    print('Python:',sys.version.split()[0],'Logical CPUs:',os.cpu_count())
    inspect_source(Path.home()/'Desktop'/'ChotuApp_Software')
    if sys.platform=='win32':windows_samples()
    else:print('Windows process sampling skipped on this operating system.')
    print('END DIAGNOSTIC — no app files, fetching settings, saved runs or exports changed.')

if __name__=='__main__':main()
