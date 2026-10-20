"""Stage progress only: never turn discovery tasks into fetched product counts."""
import re

def parse_progress(text):
    stage = None
    result = {}
    for line in str(text).splitlines():
        if 'Stage: ' in line:
            stage = line.split('Stage: ', 1)[1].strip()
        match = re.search(r'(product prices and pages|public product pages|building Excel rows):\s*(\d+)/(\d+)', line, re.I)
        if match:
            unit, completed, total = match.group(1).lower(), int(match.group(2)), int(match.group(3))
            result = {'stage': stage, 'completed_tasks': completed, 'total_tasks': total,
                      'unit': unit, 'remaining_tasks': max(0, total-completed),
                      'stage_percent': round(100*completed/total, 1) if total and completed <= total else None,
                      'products_fetched': None, 'overall_percent': None}
    # Local log events use different, explicit units.
    match = re.findall(r'KHAADI LISTING PROGRESS:\s*(\d+)/(\d+) categories;\s*(\d+) distinct product URLs', str(text))
    if match and not result:
        done, total, found = map(int, match[-1])
        result = {'stage': 'Category discovery', 'completed_tasks': done, 'total_tasks': total,
                  'remaining_tasks': max(0,total-done), 'stage_percent': round(100*done/total,1) if total and done<=total else None,
                  'unit': 'categories', 'product_urls_found': found, 'products_fetched': None, 'overall_percent': None}
    return result

def rows(runners):
    output = []
    for run in runners.get('runs', []):
        current = None
        sections = {}
        for line in run.get('snapshot','').splitlines():
            match = re.fullmatch(r'([^:]+): (done|running|pending|failed|blocked|source_paused)',line.strip())
            if match:
                current = match.group(1);sections[current] = []
            elif current: sections[current].append(line)
        for name,status in run.get('stores',{}).items():
            output.append(dict(store=name,status=status,execution='GitHub runner',runner_id=str(run.get('databaseId','')),
                               observed_utc=run.get('snapshot_utc'),stale=run.get('snapshot_stale',False),
                               **parse_progress('\n'.join(sections.get(name,[])))))
    for local in runners.get('khaadi_devices',[]):
        output.append(dict(store='Khaadi',execution=local.get('execution','PC / CMD'), runner_id=str(local.get('worker_pid','')),
                           status=local.get('status','unknown'),observed_utc=local.get('observed_utc'),
                           stale=not local.get('status_confirmed',False),
                           **parse_progress(local.get('last_event','')+'\n'+'\n'.join(local.get('log_tail',[])))))
    return output
