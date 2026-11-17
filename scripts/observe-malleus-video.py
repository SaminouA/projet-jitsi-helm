#!/usr/bin/env python3
"""Observe only the dedicated Grid via local port-forward; no Kubernetes writes."""
import argparse
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
import time
from urllib.parse import urlparse


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--grid', default='http://127.0.0.1:14444')
    parser.add_argument('--participants', type=int, choices=[2,3], default=2)
    parser.add_argument('--duration', type=int, choices=[180,240], default=180)
    args=parser.parse_args()
    url=urlparse(args.grid)
    if url.scheme!='http' or url.hostname not in ['127.0.0.1','localhost'] or url.username or url.password:
        raise SystemExit('Dedicated loopback Grid only')
    spec=importlib.util.spec_from_file_location('light',Path(__file__).with_name('run-malleus-light.py'))
    light=importlib.util.module_from_spec(spec);spec.loader.exec_module(light)
    light.GRID=args.grid.rstrip('/');light.VIDEO_MODE=True
    folder=Path(__file__).resolve().parents[1]/'tests/results'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ-grid-video')
    folder.mkdir(mode=0o700)
    consecutive=0;verified=False;start=time.monotonic()
    with (folder/'browser-observations.jsonl').open('x') as output:
        while time.monotonic()-start<args.duration:
            browsers=light.browser_stats()
            if len(browsers)>args.participants:raise SystemExit('Unexpected concurrent Grid sessions')
            good=len(browsers)==args.participants and all(
                b.get('joined') and b.get('connection')=='connected' and
                any(t.get('type')=='video' and not t.get('muted') for t in b.get('tracks',[])) and
                (b.get('bitrate') or {}).get('video',{}).get('upload',0)>0 and
                (b.get('bitrate') or {}).get('video',{}).get('download',0)>0 and
                any(v.get('frames',0)>0 for v in b.get('videoElements',[]))
                for b in browsers)
            consecutive=consecutive+1 if good else 0
            verified=verified or consecutive>=3
            output.write(json.dumps({'elapsed_s':round(time.monotonic()-start,1),'browsers':browsers,'all_clients_video':good})+'\n');output.flush()
            print('Grid sessions='+str(len(browsers))+' video='+str(good),flush=True)
            time.sleep(5)
    (folder/'summary.json').write_text(json.dumps({'client_video_observed':verified,'jvb_video_validated':False,'job_result_checked':False},indent=2)+'\n')
    print('Private evidence: '+str(folder))
    return 0 if verified else 2


if __name__=='__main__':raise SystemExit(main())
