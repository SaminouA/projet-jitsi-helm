#!/bin/sh
# Outil de validation local : aucune installation globale, aucun serveur lance.
set -eu
[ "$#" -eq 1 ] || { echo 'Usage: sh scripts/fetch-caddy.sh DOSSIER_TEMPORAIRE' >&2; exit 1; }
[ "$(uname -s)" = Linux ] && [ "$(uname -m)" = x86_64 ] || {
  echo 'Le binaire epingle est reserve a Linux amd64.' >&2; exit 1;
}
mkdir -p "$1"
curl --fail --silent --show-error --location --retry 3 --max-time 120 \
  https://github.com/caddyserver/caddy/releases/download/v2.11.9/caddy_2.11.9_linux_amd64.tar.gz \
  --output "$1/caddy.tar.gz"
printf '%s  %s\n' \
  0e85544340290a16ce4bfb76fe7d65e9de1bf3a6e67f5ccfff30b30d27ea4c73e078077b7bf3e58ae60b6b12e44327705287059c775bca5782e8ee85ea7edd75 \
  "$1/caddy.tar.gz" | sha512sum --check --status
tar -xzf "$1/caddy.tar.gz" -C "$1" caddy
chmod 755 "$1/caddy"
