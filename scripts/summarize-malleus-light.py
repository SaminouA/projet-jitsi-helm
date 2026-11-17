#!/usr/bin/env python3
"""Resumer les preuves privees Malleus sans exporter logs, IDs ou credentials."""
from datetime import datetime
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def cpu(value):
    return float(value[:-1]) if value.endswith('m') else float(value) * 1000


def memory(value):
    for suffix, factor in [('Mi', 1), ('Gi', 1024), ('Ki', 1 / 1024)]:
        if value.endswith(suffix): return float(value[:-2]) * factor
    raise ValueError('Unite memoire non prise en charge')


def summarize(folder):
    run = json.loads((folder / 'summary.json').read_text())
    samples = run['observations']
    requested = run['participants_requested']
    metrics = {}
    for sample in samples:
        for line in sample['pods_metrics']:
            name, cpu_raw, memory_raw = line.split()
            maxima = metrics.setdefault(name, {'cpu_max_m': 0, 'memory_max_mib': 0})
            maxima['cpu_max_m'] = max(maxima['cpu_max_m'], cpu(cpu_raw))
            maxima['memory_max_mib'] = max(maxima['memory_max_mib'], memory(memory_raw))
    full = [datetime.fromisoformat(s['timestamp']) for s in samples if s['jicofo'].get('participants') == requested]
    track_count = lambda s, kind: sum(t['type'] == kind and not t['muted']
        for b in s.get('browsers', []) if isinstance(b, dict) for t in b.get('tracks', []))
    audio_samples = [s for s in samples if track_count(s, 'audio') >= requested and
        s['jvb-0'].get('local_active_endpoints', 0) >= requested and s['jvb-0'].get('bit_rate_upload', 0) > 0 and
        len(s.get('browsers', [])) == requested and all(b.get('joined') and b.get('connection') == 'connected' and
        isinstance(b.get('bitrate'), dict) and b['bitrate'].get('audio', {}).get('download', 0) > 0 and
        b['bitrate'].get('audio', {}).get('upload', 0) > 0 for b in s['browsers'])]
    audio = bool(audio_samples)
    audio_times = [datetime.fromisoformat(s['timestamp']) for s in audio_samples]
    video = any(track_count(s, 'video') >= requested and any(b.get('bitrate', {}).get('video', {}).get('download', 0) > 0
                for b in s.get('browsers', []) if isinstance(b, dict) and isinstance(b.get('bitrate'), dict)) for s in samples)
    junit = next((r['counts'] for r in run['reports'] if 'MalleusJitsificus' in r['file']), None)
    return {'evidence_dir': str(folder.relative_to(ROOT)), 'participants_requested': requested,
        'duration_requested_s': run['duration_requested_s'], 'elapsed_s': run['elapsed_s'],
        'maven_exit_code': run.get('returncode'), 'abort': run.get('abort'), 'malleus_junit': junit,
        'participants_max_observed': max(s['jicofo'].get('participants', 0) for s in samples),
        'full_count_observation_span_s': round((full[-1] - full[0]).total_seconds(), 2) if len(full) >= 2 else 0,
        'node_cpu_max_percent': max(int(l.split()[2].strip('%')) for s in samples for l in s['nodes']),
        'node_memory_max_percent': max(int(l.split()[4].strip('%')) for s in samples for l in s['nodes']),
        'pods_metrics_observed_max': metrics,
        'jvb_active_endpoints_max': max(s['jvb-0'].get('local_active_endpoints', 0) for s in samples),
        'jvb_upload_raw_max': max(s['jvb-0'].get('bit_rate_upload', 0) for s in samples),
        'jvb_download_raw_max': max(s['jvb-0'].get('bit_rate_download', 0) for s in samples),
        'unmuted_audio_tracks_max': max(track_count(s, 'audio') for s in samples),
        'unmuted_video_tracks_max': max(track_count(s, 'video') for s in samples),
        'audio_media_forwarding_observed': audio, 'video_media_forwarding_observed': video,
        'audio_verified_samples': len(audio_samples),
        'audio_full_count_observation_span_s': round((audio_times[-1] - audio_times[0]).total_seconds(), 2) if len(audio_times) >= 2 else 0,
        'explicit_media_activation': run.get('explicit_media_activation', False),
        'pod_restarts_after': sum(p['restarts'] for p in run['after']['pods'].values()),
        'all_pods_ready_after': all(p['ready'] for p in run['after']['pods'].values())}


def main():
    rows = [summarize(p) for p in sorted((ROOT / 'tests/results').glob('*-malleus-*')) if (p / 'summary.json').is_file()]
    output = {'date': '2026-11-17', 'torture_commit': '4c00915e97006ff2224bb509eb3582bf3a10ca85',
        'selenium_version': '4.26.0', 'chrome_version': '130.0.6723.116',
        'generator': 'Local Selenium Grid standalone, outside GKE', 'results': rows,
        'audio_load_validated': any(r['audio_media_forwarding_observed'] for r in rows),
        'video_load_validated': any(r['video_media_forwarding_observed'] for r in rows),
        'metrics': 'Instantaneous Metrics Server samples, not a capacity limit or continuous trace'}
    (ROOT / 'tests/load/results-summary.json').write_text(json.dumps(output, indent=2) + '\n')
    print('Resume expurge :', len(rows), 'executions ; audio observe :', output['audio_load_validated'],
          '; video observee :', output['video_load_validated'])


if __name__ == '__main__':
    main()
