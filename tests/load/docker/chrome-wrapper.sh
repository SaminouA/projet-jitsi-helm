#!/bin/sh
set -eu
exec /usr/bin/google-chrome "$@" \
  --use-fake-device-for-media-stream --use-fake-ui-for-media-stream \
  --use-file-for-fake-video-capture=/usr/share/jitsi-meet-torture/resources/FourPeople_1280x720_30.y4m \
  --use-file-for-fake-audio-capture=/usr/share/jitsi-meet-torture/resources/fakeAudioStream.wav \
  --autoplay-policy=no-user-gesture-required --no-sandbox --disable-dev-shm-usage
