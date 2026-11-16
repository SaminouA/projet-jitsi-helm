#!/usr/bin/env python3
"""Validation hors cluster du profil public : fixtures uniquement."""
import importlib.util
import os
from pathlib import Path
import subprocess
import tempfile
import yaml

ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)


def run(args, **kwargs):
    return subprocess.run(args, check=True, **kwargs)


if __name__ == '__main__':
    run(['helm', 'lint', '--strict', 'charts/jitsi-edge', '-n', 'jitsi', '-f', 'tests/fixtures/edge-values.yaml'])
    with tempfile.TemporaryDirectory(prefix='jitsi-edge-check-') as tmp:
        tmp = Path(tmp)
        # Rendu en memoire puis en fichiers temporaires ; rien dans le depot.
        edge = run(['helm', 'template', 'jitsi-edge', 'charts/jitsi-edge', '-n', 'jitsi',
                    '-f', 'tests/fixtures/edge-values.yaml'], capture_output=True, text=True).stdout
        docs = [d for d in yaml.safe_load_all(edge) if d]
        (tmp / 'edge.yaml').write_text(edge)
        run(['python3', 'scripts/check-edge-render.py', str(tmp / 'edge.yaml'), 'jitsi.invalid'])
        merged = run(['helm', 'template', 'jitsi', 'charts-officiels/jitsi-meet', '-n', 'jitsi',
                      '--skip-tests', '-f', 'values-gke.yaml', '-f', 'values-jitsi-public.yaml',
                      '-f', 'tests/fixtures/jitsi-public-values.yaml'], capture_output=True, text=True).stdout
        (tmp / 'jitsi.yaml').write_text(merged)
        run(['python3', 'scripts/check-render.py', str(tmp / 'jitsi.yaml'), '--edge'])
        config = next(d['data']['Caddyfile'] for d in docs if d['kind'] == 'ConfigMap')
        # Valider avec des repertoires jetables, sans lancer caddy run/serve.
        (tmp / 'Caddyfile').write_text(config)
        caddy = os.environ.get('CADDY_BIN')
        if not caddy:
            raise SystemExit('CADDY_BIN requis pour valider Caddy ; utiliser fetch-caddy.sh dans un dossier temporaire.')
        env = dict(os.environ, XDG_DATA_HOME=str(tmp / 'data'), XDG_CONFIG_HOME=str(tmp / 'config'), HOME=str(tmp))
        p = subprocess.run([caddy, 'validate', '--config', str(tmp / 'Caddyfile'), '--adapter', 'caddyfile'],
                           env=env, capture_output=True, text=True)
        if p.returncode:
            raise SystemExit('Validation Caddy echouee : ' + p.stderr)
        print('Caddyfile rendu valide ; aucun serveur lance.')
