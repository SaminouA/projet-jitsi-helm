#!/usr/bin/env python3
"""Diagnostic manuel main uniquement. Aucun deploiement, aucun bootstrap."""
import argparse
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import tempfile
import yaml

REPO = 'SaminouA/projet-jitsi-helm'
PROJECT = 'project-fcf2ef91-c005-4910-a10'
ACCOUNT = 'github-jitsi-deployer@' + PROJECT + '.iam.gserviceaccount.com'
CONTEXT = 'gke_' + PROJECT + '_europe-west1-b_jitsi-cluster'
DOMAIN = 'jitsi-meet-m2.duckdns.org'


def require(ok, message):
    if not ok:
        raise SystemExit(message)


def verify_guard(env, payload, main_sha, local_sha):
    expected = env.get('EXPECTED_SHA', '')
    require(env.get('GITHUB_ACTIONS') == 'true' and
            env.get('GITHUB_EVENT_NAME') == 'workflow_dispatch' and
            env.get('GITHUB_REPOSITORY') == REPO and
            env.get('GITHUB_REF') == 'refs/heads/main' and
            (payload.get('repository') or {}).get('full_name') == REPO and
            (payload.get('inputs') or {}).get('confirm_read_only') in ('true', True) and
            re.fullmatch(r'[0-9a-f]{40}', expected) is not None and
            expected == main_sha == local_sha == env.get('GITHUB_SHA') and
            env.get('JITSI_ACCESS_PROFILE') == 'public-edge',
            'Diagnostic refuse : dispatch explicite sur la tete main du depot attendu requis.')


def read_command(label, args):
    # Seuls ces outils/operations sont admis ici. Jamais de shell ni sortie brute.
    allowed = (args == ['git', 'rev-parse', 'HEAD'] or
               args == ['gh', 'api', 'repos/' + REPO + '/git/ref/heads/main', '--jq', '.object.sha'] or
               args[:2] == ['sops', '--decrypt'] or
               args[:2] in [['helm', 'list'], ['helm', 'lint'], ['helm', 'template']] or
               args[:3] in [['kubectl', 'config', 'current-context'], ['kubectl', 'auth', 'whoami'],
                             ['kubectl', 'auth', 'can-i']] or
               args[:4] == ['kubectl', '-n', 'jitsi', 'get'] or
               (args[0] == 'python3' and args[1] in ['scripts/check-edge-live.py',
                'scripts/check-render.py', 'scripts/check-cd-render.py']))
    require(allowed, 'Commande hors perimetre diagnostic refusee.')
    try:
        p = subprocess.run(args, capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired):
        raise SystemExit('Echec diagnostic : ' + label + ' ; details non publies.') from None
    require(p.returncode == 0, 'Echec diagnostic : ' + label + ' ; details non publies.')
    return p.stdout


def check_rbac(query):
    checks = [(v, r) for r in ['configmaps', 'secrets', 'services', 'serviceaccounts',
                              'deployments.apps', 'statefulsets.apps']
              for v in ['get', 'list', 'watch', 'create', 'update', 'patch', 'delete']]
    checks += [(v, r) for r in ['pods', 'replicasets.apps'] for v in ['get', 'list', 'watch']]
    checks.append(('get', 'persistentvolumeclaims/jitsi-edge-data'))
    for verb, resource in checks:
        require(query(verb, resource), 'RBAC manquant : ' + verb + ' ' + resource)
    return len(checks)


def guard():
    payload = json.loads(Path(os.environ['GITHUB_EVENT_PATH']).read_text())
    main = read_command('lecture main GitHub', ['gh', 'api', 'repos/' + REPO + '/git/ref/heads/main',
                                               '--jq', '.object.sha']).strip()
    local = read_command('SHA local', ['git', 'rev-parse', 'HEAD']).strip()
    verify_guard(os.environ, payload, main, local)


def diagnose():
    guard()
    require(read_command('contexte GKE', ['kubectl', 'config', 'current-context']).strip() == CONTEXT,
            'Contexte GKE inattendu.')
    identity = json.loads(read_command('identite GKE', ['kubectl', 'auth', 'whoami', '-o', 'json']))
    require(identity['status']['userInfo']['username'] == ACCOUNT, 'Identite GKE inattendue.')
    common = json.loads(read_command('configuration publique live', ['kubectl', '-n', 'jitsi', 'get',
        'configmaps', '-l', 'app.kubernetes.io/instance=jitsi', '-o', 'json']))
    urls = [obj['data']['PUBLIC_URL'] for obj in common['items'] if 'PUBLIC_URL' in (obj.get('data') or {})]
    require(urls == ['https://' + DOMAIN], 'URL Jitsi deployee inattendue.')
    caddy = json.loads(read_command('configuration Caddy live', ['kubectl', '-n', 'jitsi', 'get',
        'configmap', 'jitsi-edge-config', '-o', 'json']))['data']['Caddyfile']
    require('acme_ca https://acme-v02.api.letsencrypt.org/directory' in caddy and
            'acme-staging' not in caddy, 'ACME production requis sur la release existante.')
    count = check_rbac(lambda v, r: read_command('autorisation ' + v + ' ' + r,
        ['kubectl', 'auth', 'can-i', v, r, '-n', 'jitsi']).strip() == 'yes')
    print('Identite GKE attendue et ' + str(count) + ' autorisations confirmees (aucune operation CRUD executee).')
    releases = json.loads(read_command('releases existantes', ['helm', 'list', '-n', 'jitsi', '-o', 'json']))
    for name in ['jitsi', 'jitsi-edge']:
        matching = [r for r in releases if r['name'] == name and r['status'] == 'deployed']
        require(len(matching) == 1, 'Release existante deployee requise : ' + name)
    service = json.loads(read_command('Service JVB', ['kubectl', '-n', 'jitsi', 'get',
                                                     'service', 'jitsi-jitsi-meet-jvb', '-o', 'json']))
    ip = service['status']['loadBalancer']['ingress'][0]['ip']
    root = Path(os.environ['RUNNER_TEMP']).resolve()
    with tempfile.TemporaryDirectory(prefix='jitsi-diagnostic.', dir=root) as directory:
        tmp = Path(directory)
        os.chmod(tmp, 0o700)
        # Secours always() en cas d'interruption ; aucun artefact ni cache sensible.
        with open(os.environ['GITHUB_ENV'], 'a') as env:
            env.write('CD_DIAG_TMP_DIR=' + str(tmp) + '\n')
        def save(name, text):
            path = tmp / name
            with os.fdopen(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), 'w') as f:
                f.write(text)
            return str(path)
        edge = read_command('rendu Caddy', ['helm', 'template', 'jitsi-edge', 'charts/jitsi-edge',
            '-n', 'jitsi', '-f', 'deploy/jitsi-edge-duckdns.yaml'])
        edge_file = save('edge.yaml', edge)
        edge_values = yaml.safe_load(Path('deploy/jitsi-edge-duckdns.yaml').read_text())
        require(edge_values.get('acmeEnvironment') == 'production' and
                edge_values.get('publicDomain') == DOMAIN and
                edge_values.get('service', {}).get('addressName') == 'jitsi-edge-ip',
                'Profil public Caddy inattendu.')
        read_command('edge et PVC existants', ['python3', 'scripts/check-edge-live.py', edge_file, DOMAIN, '--after'])
        secret_file = str(tmp / 'secrets.yaml')
        read_command('dechiffrement SOPS/KMS', ['sops', '--decrypt', '--output', secret_file, 'values-secrets.sops.yaml'])
        os.chmod(secret_file, 0o600)
        network_file = save('network.yaml', yaml.safe_dump({'jvb': {'publicIPs': [ip]}}))
        values = ['-f', 'values-gke.yaml', '-f', 'values-jitsi-public.yaml',
                  '-f', 'deploy/jitsi-duckdns.yaml', '-f', network_file, '-f', secret_file]
        read_command('lint Jitsi', ['helm', 'lint', '--strict', 'charts-officiels/jitsi-meet', *values])
        rendered = read_command('rendu Jitsi', ['helm', 'template', 'jitsi', 'charts-officiels/jitsi-meet',
            '-n', 'jitsi', '--skip-tests', *values])
        render_file = save('render.yaml', rendered)
        read_command('invariants publics', ['python3', 'scripts/check-render.py', render_file, '--edge', '--ready'])
        read_command('comparaison secrets et ressources', ['python3', 'scripts/check-cd-render.py',
                                                          render_file, secret_file, '--after'])
        guard()  # Un push pendant le diagnostic rend le resultat obsolete.
        print('SOPS/KMS, rendus, secrets existants, reseau et disponibilite verifies ; aucune valeur sensible publiee.')
    print('Fichiers temporaires supprimes. Aucun deploiement ni bootstrap effectue.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--guard-only', action='store_true')
    args = parser.parse_args()
    signal.signal(signal.SIGTERM, lambda *_: (_ for _ in ()).throw(SystemExit('Diagnostic interrompu.')))
    try:
        if args.guard_only:
            guard()
            print('Dispatch manuel, depot, branche et SHA main verifies.')
        else:
            diagnose()
    except (OSError, ValueError, KeyError, TypeError, IndexError, AttributeError):
        raise SystemExit('Diagnostic impossible ; details potentiellement sensibles non publies.') from None


if __name__ == '__main__':
    main()
