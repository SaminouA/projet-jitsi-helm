#!/usr/bin/env python3
"""Configuration locale exec ADC pour CD workflow_run de confiance uniquement."""
import importlib.util
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


auth = load('gke_diagnostic_auth', 'diagnose-cd.py')
event = load('cd_event_guard', 'check-cd-event.py')


def guard_cd():
    payload = json.loads(Path(os.environ['GITHUB_EVENT_PATH']).read_text())
    expected = event.verify_event(payload, os.environ)
    current = auth.read_command('lecture main GitHub', ['gh', 'api',
        'repos/' + auth.REPO + '/git/ref/heads/main', '--jq', '.object.sha']).strip()
    local = auth.read_command('SHA local', ['git', 'rev-parse', 'HEAD']).strip()
    auth.require(expected == current == local,
                 'Configuration CD refusee : SHA main depasse ou checkout inattendu.')
    profile = os.environ.get('JITSI_ACCESS_PROFILE')
    auth.require(profile in ('localhost', 'public-edge'), 'Profil CD explicite requis.')
    if profile == 'public-edge':
        auth.require(os.environ.get('JITSI_EDGE_CD_ENABLED') == 'true' and
                     os.environ.get('JITSI_PUBLIC_DOMAIN') == auth.DOMAIN and
                     os.environ.get('JITSI_EDGE_ADDRESS_NAME') == 'jitsi-edge-ip',
                     'Configuration CD refusee : profil public inattendu.')


def main():
    try:
        auth.configure_gke(guard_fn=guard_cd, filename='jitsi-cd-kubeconfig')
    except (OSError, ValueError, KeyError, TypeError, IndexError, AttributeError):
        raise SystemExit('Configuration GKE CD refusee ; details sensibles non publies.') from None


if __name__ == '__main__':
    main()
