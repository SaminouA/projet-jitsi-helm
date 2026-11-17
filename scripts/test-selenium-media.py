#!/usr/bin/env python3
"""Local Grid smoke test: synthetic media only, no external meeting."""
import json
import time
import urllib.request

BASE = 'http://127.0.0.1:4444'

def request(method, path, body=None):
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(BASE + path, data=data, method=method,
                                 headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=45) as response:
        value = json.load(response)['value']
    if isinstance(value, dict) and 'error' in value:
        raise RuntimeError('WebDriver command failed: ' + value['error'])
    return value

for attempt in range(60):
    try:
        if request('GET', '/status').get('ready'):
            break
    except (OSError, ValueError):
        pass
    time.sleep(2)
else:
    raise SystemExit('Selenium readiness timeout')

session = request('POST', '/session', {'capabilities': {'alwaysMatch': {
    'browserName': 'chrome', 'goog:chromeOptions': {
        'binary': '/opt/jitsi/chrome-wrapper',
        'args': ['--headless=new', '--no-proxy-server']}}}})['sessionId']
prefix = '/session/' + session
try:
    # Loopback is a secure context; no bypass of HTTPS certificate checks.
    request('POST', prefix + '/url', {'url': 'http://localhost:4444/status'})
    result = request('POST', prefix + '/execute/async', {'script': '''
const done = arguments[arguments.length - 1];
(async () => {
 let stream;
 try {
  stream = await navigator.mediaDevices.getUserMedia({video:true,audio:true});
  const video = document.createElement('video'); video.muted=true;
  video.autoplay=true; video.srcObject=stream; document.body.appendChild(video);
  await video.play();
  const ctx = new AudioContext(); await ctx.resume();
  const analyser=ctx.createAnalyser();
  ctx.createMediaStreamSource(stream).connect(analyser);
  await new Promise(r=>setTimeout(r,2000));
  const samples=new Float32Array(analyser.fftSize); analyser.getFloatTimeDomainData(samples);
  const rms=Math.sqrt(samples.reduce((s,x)=>s+x*x,0)/samples.length);
  const frames=video.getVideoPlaybackQuality().totalVideoFrames;
  done({ok:true, videoTracks:stream.getVideoTracks().filter(t=>t.readyState==='live'&&!t.muted).length,
    audioTracks:stream.getAudioTracks().filter(t=>t.readyState==='live'&&!t.muted).length,
    width:video.videoWidth,height:video.videoHeight,decodedFrames:frames,audioRms:rms});
  await ctx.close();
 } catch(e) { done({ok:false,category:e.name}); }
 finally { if(stream) stream.getTracks().forEach(t=>t.stop()); }
})();''', 'args': []})
    assert result.get('ok') and result['videoTracks'] == 1 and result['audioTracks'] == 1, result
    assert result['width'] > 0 and result['height'] > 0 and result['decodedFrames'] > 5, result
    assert result['audioRms'] > 0.001, result
    print(json.dumps(result, sort_keys=True))
finally:
    request('DELETE', prefix)
