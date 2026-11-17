#!/usr/bin/env python3
"""Un palier Malleus borne, Grid local et controles cluster sans mutation."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import signal
import shutil
import subprocess
import time
import urllib.request
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
CONTEXT = 'gke_project-fcf2ef91-c005-4910-a10_europe-west1-b_jitsi-cluster'
GRID = 'http://127.0.0.1:4444'
SOURCE = Path('/tmp/jitsi-meet-torture-light')
ACTIVATED = set()
VIDEO_MODE = False


def read(args):
    if args[0] == 'kubectl' and args[1:3] != ['config', 'current-context']:
        args = ['kubectl', '--context', CONTEXT, *args[1:]]
    result = subprocess.run(args, capture_output=True, text=True, timeout=20)
    if result.returncode:
        raise RuntimeError('lecture de controle echouee : ' + args[0])
    return result.stdout


def browser_stats():
    # Seulement etats et compteurs ; aucun ID de session/candidat ICE exporte.
    with urllib.request.urlopen(GRID + '/status', timeout=10) as response:
        nodes = json.load(response)['value']['nodes']
    script = """try {const c=window.APP&&APP.conference;const r=c&&c._room;
      return {joined:c&&typeof c.isJoined==='function'?c.isJoined():null,
        connection:c&&typeof c.getConnectionState==='function'?c.getConnectionState():null,
        tracks:r&&r.getLocalTracks?r.getLocalTracks().map(t=>({type:t.getType(),muted:t.isMuted()})):[],
        bitrate:c&&typeof c.getStats==='function'?(c.getStats()||{}).bitrate:null,
        videoElements:[...document.querySelectorAll('video')].map(v=>({width:v.videoWidth,height:v.videoHeight,frames:v.getVideoPlaybackQuality?v.getVideoPlaybackQuality().totalVideoFrames:0}))};
      }catch(e){return {category:e.name};}"""
    result = []
    for node in nodes:
        for slot in node['slots']:
            if slot.get('session'):
                session_id = slot['session']['sessionId']
                # Certains clients rejoignent sans pistes : activation UI explicite,
                # uniquement de nos sessions Grid et de leurs peripheriques factices.
                for label in (['Start camera'] if VIDEO_MODE else ['Unmute microphone', 'Start camera']):
                    if (session_id, label) in ACTIVATED: continue
                    query = urllib.request.Request(GRID + '/session/' + session_id + '/elements',
                        data=json.dumps({'using': 'css selector', 'value': '[aria-label="' + label + '"]'}).encode(),
                        headers={'Content-Type': 'application/json; charset=utf-8'})
                    try:
                        with urllib.request.urlopen(query, timeout=5) as response:
                            found = json.load(response)['value']
                        if found:
                            element = found[0]['element-6066-11e4-a52e-4f735466cecf']
                            click = urllib.request.Request(GRID + '/session/' + session_id + '/element/' + element + '/click',
                                data=b'{}', headers={'Content-Type': 'application/json; charset=utf-8'})
                            with urllib.request.urlopen(click, timeout=5): pass
                            ACTIVATED.add((session_id, label))
                    except Exception: pass
                request = urllib.request.Request(GRID + '/session/' + slot['session']['sessionId'] + '/execute/sync',
                    data=json.dumps({'script': script, 'args': []}).encode(),
                    headers={'Content-Type': 'application/json; charset=utf-8'})
                try:
                    with urllib.request.urlopen(request, timeout=10) as response:
                        result.append(json.load(response)['value'])
                except Exception:
                    result.append({'category': 'BROWSER_STATS_UNAVAILABLE'})
    return result


def observe():
    meminfo = dict(line.split(':', 1) for line in Path('/proc/meminfo').read_text().splitlines())
    values = {'timestamp': datetime.now(timezone.utc).isoformat(), 'generator_disk_free_mib': shutil.disk_usage('/tmp').free // 1048576,
              'generator_mem_available_mib': int(meminfo['MemAvailable'].split()[0]) // 1024,
              'generator_tmpfs_free_mib': shutil.disk_usage('/dev/shm').free // 1048576}
    for name, url in [('jicofo', 'http://127.0.0.1:8888/stats'), ('jvb-0', 'http://127.0.0.1:8080/colibri/stats')]:
        stats = json.loads(read(['kubectl', '-n', 'jitsi', 'exec', 'deployment/jitsi-jitsi-meet-' + name,
                                 '--', 'curl', '--max-time', '8', '-fsS', url]))
        values[name] = {k: stats[k] for k in ['conferences', 'participants', 'local_active_endpoints',
                    'stress_level', 'bit_rate_download', 'bit_rate_upload', 'packet_rate_download',
                    'packet_rate_upload', 'largest_conference'] if k in stats}
    values['browsers'] = browser_stats()
    values['nodes'] = read(['kubectl', 'top', 'nodes', '--no-headers']).strip().splitlines()
    values['pods_metrics'] = read(['kubectl', 'top', 'pods', '-n', 'jitsi', '--no-headers']).strip().splitlines()
    pods = json.loads(read(['kubectl', '-n', 'jitsi', 'get', 'pods', '-o', 'json']))['items']
    values['pods'] = {p['metadata']['name']: {'ready': all(c['ready'] for c in p['status'].get('containerStatuses', []))
                                            and bool(p['status'].get('containerStatuses')),
                                          'restarts': sum(c['restartCount'] for c in p['status'].get('containerStatuses', []))}
                      for p in pods}
    return values


def healthy(sample, baseline):
    if sample.get('generator_disk_free_mib', 1000) < (500 if VIDEO_MODE else 300): return False
    if sample.get('generator_mem_available_mib', 10000) < 1024: return False
    if sample.get('generator_tmpfs_free_mib', 10000) < 512: return False
    if not all(p['ready'] for p in sample['pods'].values()): return False
    if any(p['restarts'] > baseline['pods'].get(n, {'restarts': 0})['restarts'] for n, p in sample['pods'].items()): return False
    if set(sample['pods']) != set(baseline['pods']): return False
    for line in sample['nodes']:
        fields = line.split()
        if int(fields[2].strip('%')) >= 80 or int(fields[4].strip('%')) >= 80: return False
    return True


def clean_grid():
    with urllib.request.urlopen(GRID + '/status', timeout=10) as response:
        nodes = json.load(response)['value']['nodes']
    for node in nodes:
        for slot in node['slots']:
            session = slot.get('session')
            if session:
                request = urllib.request.Request(GRID + '/session/' + session['sessionId'], method='DELETE')
                with urllib.request.urlopen(request, timeout=15): pass


def video_verified(sample, participants):
    browsers = sample.get('browsers', [])
    return len(browsers) == participants and all(
        b.get('joined') and b.get('connection') == 'connected' and
        any(t.get('type') == 'video' and not t.get('muted') for t in b.get('tracks', [])) and
        isinstance(b.get('bitrate'), dict) and b['bitrate'].get('video', {}).get('download', 0) > 0 and
        b['bitrate'].get('video', {}).get('upload', 0) > 0 for b in browsers) and \
        sample.get('jvb-0', {}).get('local_active_endpoints', 0) >= participants and \
        sample['jvb-0'].get('bit_rate_upload', 0) > 0 and sample['jvb-0'].get('bit_rate_download', 0) > 0


def main():
    global VIDEO_MODE
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--participants', type=int, choices=[2, 3], default=2)
    parser.add_argument('--duration', type=int, choices=[60, 90], default=60)
    parser.add_argument('--video', action='store_true', help='Video requise, sans rejouer le palier audio')
    args = parser.parse_args()
    VIDEO_MODE = args.video
    os.umask(0o077)
    if read(['kubectl', 'config', 'current-context']).strip() != CONTEXT:
        raise SystemExit('Contexte GKE inattendu : arret')
    resource_root = Path('/dev/shm/jitsi-m2-video') if args.video else SOURCE
    fixture = resource_root / 'resources/FourPeople_1280x720_30.y4m'
    if not fixture.is_file(): raise SystemExit('Fixture video Malleus absente : arret avant navigateurs')
    baseline = observe()
    if not healthy(baseline, baseline): raise SystemExit('Cluster non sain : arret')
    if not all(baseline[k].get('conferences') == 0 and baseline[k].get('participants') == 0
               for k in ['jicofo', 'jvb-0']): raise SystemExit('Absence de reunion non confirmee : arret')
    clean_grid()
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    folder = ROOT / 'tests/results' / (stamp + ('-malleus-video-' if args.video else '-malleus-') + str(args.participants))
    folder.mkdir(parents=True, mode=0o700)
    command = ['mvn', '-B', '-Dcheckstyle.skip=true', '-Dthreadcount=1',
       '-Djitsi-meet.tests.toRun=MalleusJitsificus', '-Djitsi-meet.instance.url=https://jitsi-meet-m2.duckdns.org',
       '-Djitsi-meet.isRemote=true', '-Dremote.address=' + GRID + '/wd/hub', '-Dremote.resource.path=' + str(resource_root),
       '-Dorg.jitsi.malleus.conferences=1', '-Dorg.jitsi.malleus.participants=' + str(args.participants),
       '-Dorg.jitsi.malleus.senders=' + str(args.participants), '-Dorg.jitsi.malleus.audio_senders=' + str(0 if args.video else args.participants),
       '-Dorg.jitsi.malleus.duration=' + str(args.duration), '-Dorg.jitsi.malleus.join_delay=1000',
       '-Dorg.jitsi.malleus.room_name_prefix=m2light' + stamp.lower(), '-Dorg.jitsi.malleus.enable_p2p=false',
       '-Dorg.jitsi.malleus.use_node_types=false', '-Dorg.jitsi.malleus.max_disrupted_bridges_pct=0',
       '-Dorg.jitsi.malleus.enable.headless=true', '-Dorg.jitsi.malleus.use_load_test=false',
       '-Dorg.jitsi.malleus.extra_sender_params=' + ('config.resolution=360&config.constraints.video.height.ideal=360&config.constraints.video.height.min=180&config.constraints.video.height.max=360&config.constraints.video.width.ideal=640&config.constraints.video.width.min=320&config.constraints.video.width.max=640&config.constraints.video.frameRate.ideal=15&config.constraints.video.frameRate.max=15&config.testing.noAutoPlayVideo=false&config.startWithAudioMuted=true' if args.video else 'config.resolution=180&config.constraints.video.height.ideal=180&config.constraints.video.height.min=180&config.constraints.video.height.max=180'),
       '-Dchrome.disable.nosanbox=false', '-DallowInsecureCerts=false',
       '-Dwdm.chromeDriverVersion=130.0.6723.116', '-Dwebdriver.chrome.driver=/tmp/jitsi-load-tools/chromedriver-linux64/chromedriver',
       '-Dtest.report.directory=' + str(folder / 'surefire-reports')]
    command += ['-Dweb.participant' + str(i) + '.binary=/tmp/jitsi-load-tools/chrome-linux64/chrome' for i in range(1, 4)]
    command += ['test']
    summary = {'tool_commit': read(['git', '-C', str(SOURCE), 'rev-parse', 'HEAD']).strip(),
               'participants_requested': args.participants, 'conferences_requested': 1,
               'duration_requested_s': args.duration, 'p2p_disabled_client_side': True,
               'video_required': args.video, 'fixture_alias': None if args.video else 'FourPeople_1280x720_30.y4m -> fakeVideoStream.y4m', 'actual_video': '1280x720 at 30 fps, requested output 640x360 at 15 fps' if args.video else '320x180 at 5 fps', 'explicit_media_activation': True,
               'command': command, 'baseline': baseline, 'observations': []}
    start = time.monotonic(); proc = None
    print('Precontrole sain ; preuves privees : ' + str(folder), flush=True)
    try:
        with open(folder / 'maven.log', 'w') as log, open(folder / 'observations.jsonl', 'w') as metrics:
            proc = subprocess.Popen(command, cwd=SOURCE, stdout=log, stderr=subprocess.STDOUT, start_new_session=True,
                                    env=dict(os.environ, MAVEN_OPTS='-Xmx512m'))
            while proc.poll() is None:
                sample = observe(); metrics.write(json.dumps(sample) + '\n'); metrics.flush()
                summary['observations'].append(sample)
                if not healthy(sample, baseline): raise RuntimeError('seuil de securite cluster/generateur atteint')
                if sample['jicofo'].get('conferences', 0) > 1 or sample['jicofo'].get('participants', 0) > args.participants:
                    raise RuntimeError('activite concurrente inattendue : arret du generateur')
                if time.monotonic() - start > args.duration + 180: raise RuntimeError('delai maximal atteint')
                print('Observation : conferences=' + str(sample['jicofo'].get('conferences')) +
                      ', participants=' + str(sample['jicofo'].get('participants')) + ', pods prets', flush=True)
                time.sleep(10)
            summary['returncode'] = proc.returncode
    except BaseException as error:
        summary['abort'] = str(error)
        if proc and proc.poll() is None:
            os.killpg(proc.pid, signal.SIGTERM)
            try: proc.wait(timeout=10)
            except subprocess.TimeoutExpired: os.killpg(proc.pid, signal.SIGKILL); proc.wait()
    finally:
        try: clean_grid()
        except Exception: summary['grid_cleanup_error'] = True
        summary['elapsed_s'] = round(time.monotonic() - start, 2)
        summary['media_observed'] = any(x['jvb-0'].get('local_active_endpoints', 0) > 0 and
                                        x['jvb-0'].get('bit_rate_upload', 0) > 0 for x in summary['observations'])
        summary['video_observed'] = any(video_verified(x, args.participants) for x in summary['observations'])
        summary['after'] = observe()
        reports = []
        for report in (folder / 'surefire-reports').glob('**/*.xml'):
            if report.name != 'TEST-TestSuite.xml' and 'MalleusJitsificus' not in report.name: continue
            try:
                root = ET.parse(report).getroot()
                reports.append({'file': report.name, 'tag': root.tag, 'counts': {k: root.attrib[k]
                                for k in ['tests', 'failures', 'errors', 'skipped', 'time'] if k in root.attrib}})
            except ET.ParseError: pass
        summary['reports'] = reports
        (folder / 'summary.json').write_text(json.dumps(summary, indent=2))
        print('Resultat : ' + json.dumps({k: summary[k] for k in ['returncode', 'abort', 'elapsed_s', 'media_observed', 'video_observed', 'reports'] if k in summary}), flush=True)
    verified = summary.get('video_observed') if args.video else summary.get('media_observed')
    return 0 if summary.get('returncode') == 0 and verified and not summary.get('abort') else 2 if summary.get('returncode') == 0 and not summary.get('abort') else 1


if __name__ == '__main__':
    raise SystemExit(main())
