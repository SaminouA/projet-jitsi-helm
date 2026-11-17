#!/bin/sh
set -eu
if [ "${1:-}" = --version ]; then exec mvn -version; fi
if [ "${1:-}" = --self-test ]; then
  exec java -Xmx384m -cp "/opt/malleus:target/test-classes:target/classes:$(cat /opt/malleus/classpath.txt)" MalleusSmoke
fi
if [ "${1:-}" = --maven-self-test ]; then
  exec mvn -B -o -Dmaven.repo.local=/opt/malleus/repository -Dcheckstyle.skip=true -Dsuite.xml=/opt/malleus/smoke-testng.xml test
fi
if [ "${1:-}" = --compile-check ]; then
  exec mvn -B -o -Dmaven.repo.local=/opt/malleus/repository -DskipTests -Dcheckstyle.skip=true test-compile
fi
[ "${1:-}" = test ] || { echo 'Argument test explicite requis.' >&2; exit 1; }
case "${PARTICIPANTS:-2}" in 2|3) ;; *) echo 'Maximum 3 participants dans ce profil.' >&2; exit 1;; esac
case "${DURATION:-60}" in 60|90) ;; *) exit 1;; esac
: "${GRID_URL:?Grid dedie requis}"
# Pas de jeton, aucune connexion Kubernetes ni mutation applicative.
exec mvn -B -o -Dmaven.repo.local=/opt/malleus/repository -Dcheckstyle.skip=true \
  -Dthreadcount=1 -Djitsi-meet.tests.toRun=MalleusJitsificus \
  -Djitsi-meet.instance.url=https://jitsi-meet-m2.duckdns.org -Djitsi-meet.isRemote=true \
  "-Dremote.address=$GRID_URL" -Dremote.resource.path=/usr/share/jitsi-meet-torture \
  "-Dorg.jitsi.malleus.participants=${PARTICIPANTS:-2}" -Dorg.jitsi.malleus.conferences=1 \
  "-Dorg.jitsi.malleus.senders=${PARTICIPANTS:-2}" -Dorg.jitsi.malleus.audio_senders=0 \
  "-Dorg.jitsi.malleus.duration=${DURATION:-60}" -Dorg.jitsi.malleus.join_delay=1000 \
  '-Dorg.jitsi.malleus.extra_sender_params=config.resolution=360&config.constraints.video.height.ideal=360&config.constraints.video.height.min=180&config.constraints.video.height.max=360&config.constraints.video.width.ideal=640&config.constraints.video.width.min=320&config.constraints.video.width.max=640&config.constraints.video.frameRate.ideal=15&config.constraints.video.frameRate.max=15&config.testing.noAutoPlayVideo=false&config.startWithAudioMuted=true' \
  -Dorg.jitsi.malleus.room_name_prefix=m2docker -Dorg.jitsi.malleus.enable_p2p=false \
  -Dorg.jitsi.malleus.max_disrupted_bridges_pct=0 -Dorg.jitsi.malleus.use_node_types=false \
  -Dorg.jitsi.malleus.enable.headless=true -Dorg.jitsi.malleus.use_load_test=false \
  -Dchrome.disable.nosanbox=false -DallowInsecureCerts=false \
  -Dwdm.chromeDriverVersion=130.0.6723.91 -Dwdm.cachePath=/opt/malleus/driver-cache \
  -Dweb.participant1.binary=/opt/jitsi/chrome-wrapper \
  -Dweb.participant2.binary=/opt/jitsi/chrome-wrapper \
  -Dweb.participant3.binary=/opt/jitsi/chrome-wrapper test
