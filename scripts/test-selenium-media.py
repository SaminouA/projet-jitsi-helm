#!/usr/bin/env python3
"""Loopback-only synthetic media test; fail closed, never log device/session IDs."""
import json
import time
import urllib.request

BASE = 'http://127.0.0.1:4444'
REQUIRED_FLAGS = (
    '--use-fake-device-for-media-stream', '--use-fake-ui-for-media-stream',
    '--use-file-for-fake-video-capture=/usr/share/jitsi-meet-torture/resources/FourPeople_1280x720_30.y4m',
    '--use-file-for-fake-audio-capture=/usr/share/jitsi-meet-torture/resources/fakeAudioStream.wav',
)


def request(method, path, body=None):
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(BASE + path, data=data, method=method,
                                 headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=45) as response:
        value = json.load(response)['value']
    if isinstance(value, dict) and 'error' in value:
        raise RuntimeError('WebDriver command failed: ' + value['error'])
    return value


def validate_flags(arguments):
    if not all(flag in arguments for flag in REQUIRED_FLAGS):
        raise RuntimeError('SYNTHETIC_FLAGS_MISSING')


def validate_media(result):
    if not result.get('ok'):
        raise RuntimeError('MEDIA_FAILURE: ' + str(result.get('category', 'UNKNOWN')))
    if not (result['videoTracks'] == 1 and result['audioTracks'] == 1
            and result['width'] > 0 and result['height'] > 0
            and result['decodedFrames'] > 5 and result['audioRms'] > 0.001):
        raise RuntimeError('MEDIA_SIGNAL_INSUFFICIENT')


MEDIA_SCRIPT = '''
const done = arguments[arguments.length - 1];
(async () => {
 const streams=[]; let ctx; let stage='secure-context';
 try {
  if (!window.isSecureContext || !navigator.mediaDevices) throw {name:'InsecureContext'};
  stage='video-capture';
  const camera=await navigator.mediaDevices.getUserMedia({video:true,audio:false});
  streams.push(camera);
  stage='audio-capture';
  const microphone=await navigator.mediaDevices.getUserMedia({video:false,audio:true});
  streams.push(microphone);
  stage='signal-measurement';
  const video=document.createElement('video'); video.muted=true; video.autoplay=true;
  video.srcObject=camera; document.body.appendChild(video); await video.play();
  ctx=new AudioContext(); await ctx.resume();
  const analyser=ctx.createAnalyser(); ctx.createMediaStreamSource(microphone).connect(analyser);
  await new Promise(r=>setTimeout(r,2000));
  const samples=new Float32Array(analyser.fftSize); analyser.getFloatTimeDomainData(samples);
  const rms=Math.sqrt(samples.reduce((s,x)=>s+x*x,0)/samples.length);
  done({ok:true, videoTracks:camera.getVideoTracks().filter(t=>t.readyState==='live'&&!t.muted).length,
    audioTracks:microphone.getAudioTracks().filter(t=>t.readyState==='live'&&!t.muted).length,
    width:video.videoWidth,height:video.videoHeight,
    decodedFrames:video.getVideoPlaybackQuality().totalVideoFrames,audioRms:rms});
 } catch(e) { done({ok:false,category:stage+':'+e.name}); }
 finally { for(const s of streams) s.getTracks().forEach(t=>t.stop()); if(ctx) await ctx.close(); }
})();'''


def main():
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
        # Only inspect the required flags, never print the full command line.
        command = request('POST', prefix + '/goog/cdp/execute', {
            'cmd': 'Browser.getBrowserCommandLine', 'params': {}})
        validate_flags(command['arguments'])
        print(json.dumps({'synthetic_flags_verified': True}), flush=True)
        request('POST', prefix + '/url', {'url': 'http://localhost:4444/status'})
        result = request('POST', prefix + '/execute/async', {'script': MEDIA_SCRIPT, 'args': []})
        print(json.dumps(result, sort_keys=True), flush=True)
        validate_media(result)
    finally:
        request('DELETE', prefix)


if __name__ == '__main__':
    main()
