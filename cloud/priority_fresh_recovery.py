"""Recover only the prioritized stores in the current fresh campaign."""

import json
import os
import subprocess

from fresh804_dispatch import REPO, chain_ids, gh, lane_prefix, planned_groups, publish_progress
from github_json import read_json
from resume_failed_stores import checkpoint_parent


def recover_priority(request, sites):
    wanted = request['priority_stores']
    approved = {site['name'] for site in sites}
    if not wanted or len(set(wanted)) != len(wanted) or not set(wanted) <= approved:
        raise ValueError('Priority recovery requires distinct enabled stores')
    state = read_json(gh, f'repos/{REPO}/contents/latest.json?ref=drive-sync-reports')
    generation = request['refresh_generation']
    previous = read_json(gh, f'repos/{REPO}/contents/runs/{request["resume_pause_run_id"]}.json?ref=stopped-fetch-reports')
    if previous['refresh_generation'] != generation:
        raise ValueError('Priority recovery generation mismatch')
    runs = json.loads(gh('run', 'list', '--repo', REPO, '--workflow', 'cloud-fetch.yml',
                         '--limit', '200', '--json', 'databaseId,displayTitle,status,conclusion'))
    by_title = {entry['title']: identity for identity, entry in previous['runs'].items()}
    report = {'run_id': os.environ['GITHUB_RUN_ID'], 'refresh_generation': generation, 'stores': []}
    groups = planned_groups(sites, request)
    for index, group in sorted(enumerate(groups, 1), key=lambda row: row[1][0]["name"] not in request.get("additive_solo_stores", [])):
        lane = lane_prefix(request) + str(index)
        selected = []
        for site in group:
            name = site['name']
            if name not in wanted:
                continue
            entry = {'store': name, 'runner_group': lane}
            report['stores'].append(entry)
            audit = state.get('audit804_results', {}).get(name, {})
            if state.get('uploaded', {}).get(name, {}).get('refresh_generation') == generation:
                entry['status'] = 'verified'
            elif audit.get('refresh_generation') == generation and audit.get('held_input'):
                entry['status'] = 'saved_input_for_audit'
            else:
                selected.append((site, entry))
        if not selected:
            continue
        title = 'Cloud group ' + lane
        additive_roots = [str(run['databaseId']) for run in runs if run['displayTitle'] == title]
        additive_group = len(group) == 1 and group[0]['name'] in request.get('additive_solo_stores', [])
        if additive_group and not additive_roots:
            gh('workflow', 'run', 'cloud-fetch.yml', '--repo', REPO, '--ref', 'main',
               '-f', 'runner_group=' + lane, '-f', 'stores=' + json.dumps(group, separators=(',', ':')),
               '-f', 'minutes=300', '-f', 'save_checkpoint=true',
               '-f', 'auto_continue_limit=48', '-f', 'auto_continue_once=false')
            selected[0][1]['status'] = 'fresh_dispatched'
            continue
        roots = set(additive_roots) if additive_group else {by_title[title]}
        lineage = chain_ids(runs, roots)
        recent = [run for run in runs if str(run['databaseId']) in lineage]
        if not recent:
            raise RuntimeError(f'No trusted recent run for lane {lane}')
        latest = max(recent, key=lambda run: int(run['databaseId']))
        parent = str(latest['databaseId'])
        if latest['status'] != 'completed' or latest['conclusion'] == 'success':
            for _, entry in selected:
                entry.update(status='existing_run_retained', parent_run=parent)
            continue
        try:
            diagnostics = read_json(gh, f'repos/{REPO}/contents/runs/{parent}-1.json?ref=cloud-reports')
        except subprocess.CalledProcessError:
            diagnostics = {}
        by_store = {row['name']: row for row in diagnostics.get('stores', [])}
        eligible = []
        for site, entry in selected:
            receipt = by_store.get(site['name'], {})
            statuses = receipt.get('http_statuses', {})
            if receipt.get('status') == 'done':
                entry.update(status='completed_output_for_audit', parent_run=parent)
                continue
            if statuses and set(statuses) <= {'402', '403'} and site['name'] not in request.get('repaired_source_adapters', []):
                entry.update(status='source_access_blocked', parent_run=parent, http_statuses=statuses)
            else:
                eligible.append((site, entry))
        selected = eligible
        if not selected:
            continue
        try:
            checkpoint, _ = checkpoint_parent(parent)
        except ValueError as exc:
            if str(exc) != 'No available checkpoint in completed continuation ancestry':
                raise
            checkpoint = None
        restore = ['-f', 'resume_run_id=' + checkpoint, '-f', 'partition_resume=true'] if checkpoint else []
        gh('workflow', 'run', 'cloud-fetch.yml', '--repo', REPO, '--ref', 'main',
           '-f', 'runner_group=' + lane, '-f', 'continuation_parent=' + parent,
           '-f', 'stores=' + json.dumps([site for site, _ in selected], separators=(',', ':')),
           '-f', 'minutes=300', '-f', 'save_checkpoint=true',
           '-f', 'auto_continue_limit=48', '-f', 'auto_continue_once=false', *restore)
        for _, entry in selected:
            entry.update(status='checkpoint_dispatched' if checkpoint else 'fresh_dispatched', parent_run=parent)
    report['dispatch'] = 'complete'
    publish_progress(report)
