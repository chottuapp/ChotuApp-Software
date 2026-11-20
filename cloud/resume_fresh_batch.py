"""Resume the latest paused fetch generation without duplicating its groups."""

import json
import os

from fresh804_dispatch import REPO, gh, lane_prefix, planned_groups, publish_progress
from github_json import read_json


def resume_batch(request, sites):
    pause_id = str(request['resume_pause_run_id'])
    if not pause_id.isdigit():
        raise ValueError('The pause run ID must be numeric')
    pause = read_json(gh, f'repos/{REPO}/contents/runs/{pause_id}.json?ref=stopped-fetch-reports')
    if (str(pause['run_id']) != pause_id or pause['pause'] != 'complete'
            or pause['refresh_generation'] != request['refresh_generation']):
        raise ValueError('No completed pause report for this generation')

    plan = planned_groups(sites, request)
    prefix = lane_prefix(request)
    report = {
        'run_id': os.environ['GITHUB_RUN_ID'],
        'refresh_generation': request['refresh_generation'],
        'pause_run_id': pause_id,
        'groups': [],
    }
    existing = json.loads(gh('run', 'list', '--repo', REPO, '--workflow', 'cloud-fetch.yml',
                             '--limit', '100', '--json', 'databaseId,displayTitle,status'))
    by_title = {entry['title']: (identity, entry) for identity, entry in pause['runs'].items()}
    pending = {}
    for index, stores in enumerate(plan, 1):
        lane = prefix + str(index)
        identity, entry = by_title['Cloud group ' + lane]
        while 'Automatic continuation of ' + identity in by_title:
            identity, entry = by_title['Automatic continuation of ' + identity]
        if not identity.isdigit() or entry['status'] != 'completed':
            raise ValueError('Invalid paused run')
        checkpoint = False
        if entry['checkpoint']:
            data = json.loads(gh('api', f'repos/{REPO}/actions/runs/{identity}/artifacts?per_page=100'))
            checkpoint = any(row['name'] == 'chotuapp-checkpoint' and not row['expired']
                             for row in data['artifacts'])
            if not checkpoint:
                raise RuntimeError(f'Previously verified checkpoint unavailable for run {identity}')
        title = 'Automatic continuation of ' + identity
        group = {'runner_group': lane, 'parent_run': identity, 'stores': [s['name'] for s in stores],
                 'mode': 'checkpoint' if checkpoint else 'fresh', 'status': 'pending'}
        report['groups'].append(group)
        if any(row['displayTitle'] == title for row in existing):
            group['status'] = 'already_dispatched'
        else:
            pending[identity] = (stores, group)

    publish_progress(report)
    for identity, (stores, group) in pending.items():
        inputs = ['-f', 'resume_run_id=' + identity] if group['mode'] == 'checkpoint' else [
            '-f', 'stores=' + json.dumps(stores, separators=(',', ':')),
        ]
        gh('workflow', 'run', 'cloud-fetch.yml', '--repo', REPO, '--ref', 'main',
           '-f', 'runner_group=' + group['runner_group'],
           '-f', 'continuation_parent=' + identity,
           '-f', 'minutes=' + str(request['fetch_segment_minutes']),
           '-f', 'save_checkpoint=true', '-f', 'auto_continue_limit=48',
           '-f', 'auto_continue_once=false', *inputs)
        group['status'] = 'dispatched'
        print(f"Resumed {group['runner_group']} using {group['mode']}", flush=True)
    report['dispatch'] = 'complete'
    publish_progress(report)
