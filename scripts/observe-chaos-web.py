#!/usr/bin/env python3
"""Observation uniquement : aucune installation ni injection de faute."""
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import time
import urllib.request
import urllib.error

ROOT = Path(__file__).resolve().parents[1]
CONTEXT = 'gke_project-fcf2ef91-c005-4910-a10_europe-west1-b_jitsi-cluster'


def read(args):
    p = subprocess.run(['kubectl', '--context', CONTEXT, *args], capture_output=True, text=True, timeout=10)
    if p.returncode: raise RuntimeError('Lecture Kubernetes echouee ; details non affiches.')
    return p.stdout


def pods():
    result = []
    for p in json.loads(read(['-n', 'jitsi', 'get', 'pods', '-o', 'json']))['items']:
        result.append({'name': p['metadata']['name'], 'uid': p['metadata']['uid'],
            'created': p['metadata']['creationTimestamp'], 'terminating': bool(p['metadata'].get('deletionTimestamp')),
            'component': p['metadata'].get('labels', {}).get('app.kubernetes.io/component'),
            'ready': bool(p['status'].get('containerStatuses')) and all(c['ready'] for c in p['status'].get('containerStatuses', [])),
            'restarts': sum(c['restartCount'] for c in p['status'].get('containerStatuses', []))})
    return result


def https():
    start = time.monotonic()
    try:
        with urllib.request.urlopen('https://jitsi-meet-m2.duckdns.org/', timeout=2) as response:
            code = response.status
    except urllib.error.HTTPError as error:
        code = error.code
    except Exception:
        code = 'TRANSPORT_ERROR'
    return {'status': code, 'elapsed_ms': round((time.monotonic() - start) * 1000, 2)}


def main():
    os.umask(0o077)
    folder = ROOT / 'tests/results' / (datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '-chaos-web')
    folder.mkdir(parents=True, mode=0o700)
    initial = pods(); web = [p for p in initial if p['component'] == 'web']
    if len(web) != 1 or not web[0]['ready']: raise SystemExit('Un unique Web pret requis pour observer.')
    origin_uid = web[0]['uid']; start = time.monotonic(); first_change = recovered = None
    initial_other = {p['name']: p['uid'] for p in initial if p['component'] != 'web'}
    baseline = {'pods': initial, 'https': https(), 'pods_metrics': read(['top', 'pods', '-n', 'jitsi', '--no-headers']),
                'nodes_metrics': read(['top', 'nodes', '--no-headers'])}
    (folder / 'baseline.json').write_text(json.dumps(baseline, indent=2))
    print('Observateur lecture seule pret : ' + str(folder), flush=True)
    samples = []
    with open(folder / 'observations.jsonl', 'w') as out:
        for tick in range(180):
            elapsed = round(time.monotonic() - start, 3)
            sample = {'timestamp': datetime.now(timezone.utc).isoformat(), 'elapsed_s': elapsed, 'https': https()}
            if tick % 2 == 0:
                sample['pods'] = pods()
                current_web = [p for p in sample['pods'] if p['component'] == 'web']
                if first_change is None and (not current_web or any(p['uid'] != origin_uid or p['terminating'] or not p['ready'] for p in current_web)):
                    first_change = elapsed
                if recovered is None and first_change is not None and any(p['uid'] != origin_uid and p['ready'] for p in current_web) and sample['https']['status'] == 200:
                    recovered = elapsed
            if tick % 10 == 0:
                sample['pods_metrics'] = read(['top', 'pods', '-n', 'jitsi', '--no-headers'])
                sample['nodes_metrics'] = read(['top', 'nodes', '--no-headers'])
            out.write(json.dumps(sample) + '\n'); out.flush(); samples.append(sample)
            if recovered is not None and elapsed - recovered > 15: break
            if elapsed > 240: break
            time.sleep(1)
    final = pods()
    events = json.loads(read(['-n', 'jitsi', 'get', 'events', '-o', 'json']))['items']
    summary = {'baseline_web_uid': origin_uid, 'first_web_change_observed_s': first_change,
        'recovery_observed_s': recovered,
        'recovery_from_first_observed_change_s': round(recovered - first_change, 3) if recovered is not None else None,
        'https_non_200_samples': sum(s['https']['status'] != 200 for s in samples),
        'all_final_pods_ready': all(p['ready'] for p in final),
        'non_web_uids_unchanged': initial_other == {p['name']: p['uid'] for p in final if p['component'] != 'web'},
        'final_pods': final,
        'events': [{'reason': e.get('reason'), 'object': e.get('involvedObject', {}).get('name'),
                    'lastTimestamp': e.get('lastTimestamp'), 'type': e.get('type')} for e in events]}
    (folder / 'summary.json').write_text(json.dumps(summary, indent=2))
    print(json.dumps({k: v for k, v in summary.items() if k not in ['final_pods', 'events', 'baseline_web_uid']}), flush=True)


if __name__ == '__main__':
    main()
