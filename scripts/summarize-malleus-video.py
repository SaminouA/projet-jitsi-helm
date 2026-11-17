#!/usr/bin/env python3
"""Synthese video separee : ne jamais ecraser les preuves audio/Chaos."""
from datetime import datetime
import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'scripts' / filename)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def main():
    runner = load('video_rules', 'run-malleus-light.py')
    common = load('video_metrics', 'summarize-malleus-light.py')
    results = []
    for path in sorted((ROOT / 'tests/results').glob('*-malleus-video-*/summary.json')):
        run = json.loads(path.read_text()); n = run['participants_requested']
        row = common.summarize(path.parent)
        verified = [s for s in run['observations'] if runner.video_verified(s, n)]
        times = [datetime.fromisoformat(s['timestamp']) for s in verified]
        row['video_verified_samples'] = len(verified)
        row['video_verified_span_s'] = round((times[-1] - times[0]).total_seconds(), 2) if len(times) > 1 else 0
        row['video_proven'] = bool(verified)
        row['complete_video_test_passed'] = run.get('returncode') == 0 and not run.get('abort') and bool(verified)
        row['audio_senders'] = 0
        row['decoded_frames_max_per_anonymous_client'] = [max((v.get('frames', 0)
            for s in verified for v in s['browsers'][i].get('videoElements', [])), default=0) for i in range(n)]
        row['clients_video_bitrate_raw'] = [{direction + '_min': min(s['browsers'][i]['bitrate']['video'][direction] for s in verified)
            for direction in ['upload', 'download']} for i in range(n)] if verified else []
        row['generator_disk_free_min_mib'] = min(s['generator_disk_free_mib'] for s in run['observations'])
        for field in ['generator_mem_available_mib', 'generator_tmpfs_free_mib']:
            values = [s[field] for s in run['observations'] if field in s]
            if values: row[field + '_min'] = min(values)
        results.append(row)
    fixture = Path('/dev/shm/jitsi-m2-video/resources/FourPeople_1280x720_30.y4m')
    output = {'date': '2026-11-17', 'tool_commit': '4c00915e97006ff2224bb509eb3582bf3a10ca85',
        'selenium': '4.26.0', 'chrome_and_driver': '130.0.6723.116',
        'fixture': {'format': 'Y4M I420', 'width': 1280, 'height': 720, 'fps': 30, 'frames_looped': 2,
                    'bytes': fixture.stat().st_size, 'sha256': hashlib.sha256(fixture.read_bytes()).hexdigest()},
        'requested_client_capture': '640x360, maximum 15 fps', 'audio_senders': 0,
        'results': results, 'ten_participants_attempted': False,
        'ten_participants_reason': 'Generator VM: 2 vCPU, narrow disk budget; no safe increase beyond 3 slots',
        'limits': 'Synthetic low-complexity pattern; sampled metrics, not maximum capacity or subjective image quality.'}
    (ROOT / 'tests/load/video-results-summary.json').write_text(json.dumps(output, indent=2) + '\n')
    print('Video :', sum(r['complete_video_test_passed'] for r in results), 'paliers complets reussis sur', len(results),
          'tentatives ; preuves audio anterieures inchangees.')


if __name__ == '__main__':
    main()
