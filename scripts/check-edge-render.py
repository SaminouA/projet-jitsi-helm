#!/usr/bin/env python3
"""Invariants du proxy public ; pas de requete au cluster ni de secret."""
import sys
from pathlib import Path
import yaml


def require(ok, message):
    if not ok:
        raise SystemExit(message)


def verify(documents, expected_domain=None):
    by_kind = {d['kind']: d for d in documents}
    require(len(documents) == 3 and set(by_kind) == {'Deployment', 'Service', 'ConfigMap'},
            'Edge : seulement Deployment, Service et ConfigMap ; PVC gere separement.')
    service = by_kind['Service']
    spec = service['spec']
    require(service['metadata']['name'] == 'jitsi-edge' and spec['type'] == 'LoadBalancer', 'Service edge inattendu')
    require({(p['port'], p['targetPort'], p['protocol']) for p in spec['ports']} ==
            {(80, 'http', 'TCP'), (443, 'https', 'TCP')} and len(spec['ports']) == 2,
            'Seuls TCP 80/443 peuvent etre exposes')
    require(not spec.get('externalIPs'), 'Pas de contournement externalIPs')
    require(bool(service['metadata']['annotations'].get('networking.gke.io/load-balancer-ip-addresses')),
            'Reservation IPv4 nommee requise')
    pod = by_kind['Deployment']['spec']
    require(pod['replicas'] == 1 and pod['strategy']['type'] == 'Recreate', 'Une replique Recreate requise')
    pod = pod['template']['spec']
    require(not pod.get('hostNetwork') and not any(p.get('hostPort') for c in pod['containers'] for p in c.get('ports', [])), 'Pas de hostNetwork/hostPort')
    require(pod.get('automountServiceAccountToken') is False, 'Jeton Kubernetes interdit dans Caddy')
    require(pod['securityContext'].get('runAsNonRoot') is True, 'Caddy non-root requis')
    container = pod['containers'][0]
    require(len(pod['containers']) == 1, 'Conteneur supplementaire non autorise')
    require({(p['name'], p['containerPort']) for p in container['ports']} ==
            {('http', 8080), ('https', 8443), ('health', 8082)}, 'Ports internes edge incoherents')
    require(container['securityContext'].get('readOnlyRootFilesystem') is True and
            container['securityContext']['capabilities']['drop'] == ['ALL'], 'Durcissement Caddy manquant')
    for key in ['startupProbe', 'readinessProbe', 'livenessProbe']:
        require(container[key]['httpGet'] == {'path': '/healthz', 'port': 'health'}, 'Sonde interne independante requise')
    require(any(v.get('persistentVolumeClaim', {}).get('claimName') == 'jitsi-edge-data' for v in pod['volumes']),
            'PVC persistant existant requis')
    caddy = by_kind['ConfigMap']['data']['Caddyfile']
    for token in ['admin off', 'protocols h1 h2', 'http_port 8080', 'https_port 8443',
                  'http://:8082', 'respond /healthz "ok" 200',
                  'reverse_proxy http://jitsi-jitsi-meet-web.jitsi.svc.cluster.local:8000',
                  '/colibri/*', '/colibri-ws/*', '/metrics', 'handle @private', 'respond 404']:
        require(token in caddy, 'Protection ou routage Caddy absent')
    require('jitsi-jitsi-meet-jvb' not in caddy and '2019' not in caddy and 'log {' not in caddy,
            'Ni controle JVB, administration ou journal de requetes sensibles exposes')
    if expected_domain:
        require('https://' + expected_domain + ' {' in caddy, 'Domaines Caddy/Jitsi differents')
    return caddy


if __name__ == '__main__':
    docs = [d for d in yaml.safe_load_all(Path(sys.argv[1]).read_text()) if d]
    verify(docs, sys.argv[2] if len(sys.argv) > 2 else None)
    print('Rendu edge : ports, persistance, sondes et protections valides.')
