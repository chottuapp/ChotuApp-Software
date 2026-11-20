"""Save a fresh generation in place and withdraw its unstarted queue."""

import json
import os
import subprocess
import time

from fresh804_dispatch import REPO, chain_ids, gh, lane_prefix, publish_progress


def list_runs():
    return json.loads(gh(
        'run', 'list', '--repo', REPO, '--workflow', 'cloud-fetch.yml',
        '--limit', '100', '--json', 'databaseId,displayTitle,status,conclusion',
    ))


def pause_batch(request):
    prefix = 'Cloud group ' + lane_prefix(request)
    report = {
        'run_id': os.environ['GITHUB_RUN_ID'],
        'refresh_generation': request['refresh_generation'],
        'pause': 'in_progress',
        'runs': {},
    }
    deadline = time.monotonic() + 23 * 60
    targets = report['runs']
    requested = set()
    while time.monotonic() < deadline:
        runs = list_runs()
        roots = {str(run['databaseId']) for run in runs if run['displayTitle'].startswith(prefix)}
        owned = chain_ids(runs, roots | set(targets))
        if not owned:
            raise RuntimeError('No runs found for the requested generation')
        current = {str(run['databaseId']): run for run in runs if str(run['databaseId']) in owned}
        for identity, run in current.items():
            entry = targets.setdefault(identity, {'title': run['displayTitle']})
            entry.update(status=run['status'], conclusion=run['conclusion'])

        active = [identity for identity, run in current.items() if run['status'] != 'completed']
        for identity in active:
            entry = targets[identity]
            if entry['status'] != 'queued' or entry.get('cancel_requested'):
                continue
            status = json.loads(gh('run', 'view', identity, '--repo', REPO, '--json', 'status'))
            if status['status'] == 'queued':
                try:
                    gh('run', 'cancel', identity, '--repo', REPO)
                except subprocess.CalledProcessError:
                    continue
                entry['cancel_requested'] = True

        # Live workers poll only the 30 most recent stop requests. Leave room
        # below that limit until this wave has finished saving its checkpoints.
        available = 24 - len(requested.intersection(active))
        for identity in active:
            if available <= 0:
                break
            entry = targets[identity]
            if entry['status'] == 'queued' or identity in requested:
                continue
            gh('workflow', 'run', 'cloud-stop.yml', '--repo', REPO, '--ref', 'main',
               '-f', 'run_id=' + identity)
            entry['stop_requested'] = True
            requested.add(identity)
            available -= 1

        if not active and all(run['status'] == 'completed' for run in targets.values()):
            # Check again after the completion event has had time to arrive.
            time.sleep(15)
            latest = list_runs()
            latest_owned = chain_ids(latest, owned)
            if latest_owned != owned:
                continue
            for identity, entry in targets.items():
                data = json.loads(gh('api', f'repos/{REPO}/actions/runs/{identity}/artifacts?per_page=100'))
                entry['checkpoint'] = any(
                    record['name'] == 'chotuapp-checkpoint' and not record['expired']
                    for record in data['artifacts']
                )
                entry['fetch_started'] = None
                if entry.get('cancel_requested'):
                    jobs = json.loads(gh('api', f'repos/{REPO}/actions/runs/{identity}/jobs?per_page=100'))
                    entry['fetch_started'] = any(
                        step['name'] == 'Start continuous fetching on the cloud runner'
                        and step.get('started_at') and step.get('conclusion') != 'skipped'
                        for job in jobs['jobs'] for step in job.get('steps', [])
                    )
            report['pause'] = 'complete'
            publish_progress(report, branch='stopped-fetch-reports')
            print(f"Pause complete: {len(targets)} fetch runs inactive", flush=True)
            return
        print(f'Pause progress: {len(active)} active or queued / {len(targets)} total', flush=True)
        publish_progress(report, branch='stopped-fetch-reports')
        time.sleep(20)

    report['pause'] = 'timed_out'
    publish_progress(report, branch='stopped-fetch-reports')
    raise RuntimeError('Some targeted fetch runs have not stopped')
