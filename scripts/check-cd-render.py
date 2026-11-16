#!/usr/bin/env python3
"""Preflight local/cluster CD ; aucun apply, aucun log de Secret."""
import base64
import json
from pathlib import Path
import subprocess
import sys
import yaml


def require(condition, message):
    if not condition:
        raise SystemExit(message)


def read_resource(kind, name):
    p = subprocess.run(['kubectl', '-n', 'jitsi', 'get', kind, name, '-o', 'json'],
                       capture_output=True, text=True, timeout=30)
    require(p.returncode == 0, f'Ressource existante requise ou lecture interdite : {kind}/{name}')
    return json.loads(p.stdout)


def verify(render, values, getter, after=False):
    require(isinstance(values, dict) and set(values) == {'jicofo', 'jvb'},
            'Le fichier dechiffre doit contenir uniquement jicofo et jvb.')
    passwords = {}
    for component in ['jicofo', 'jvb']:
        obj = values[component]
        require(isinstance(obj, dict) and set(obj) == {'xmpp'} and
                isinstance(obj['xmpp'], dict) and set(obj['xmpp']) == {'password'},
                'Schema des valeurs sensibles refuse.')
        value = obj['xmpp']['password']
        require(isinstance(value, str) and bool(value) and not value.startswith('ENC['),
                'Mot de passe dechiffre requis (valeur non affichee).')
        passwords[component] = value
    allowed = {'ConfigMap': 'configmaps', 'Secret': 'secrets', 'Service': 'services',
               'ServiceAccount': 'serviceaccounts', 'Deployment': 'deployments.apps',
               'StatefulSet': 'statefulsets.apps'}
    for doc in render:
        require(doc['kind'] in allowed, 'Ressource hors perimetre CD : revue necessaire.')
        meta = doc['metadata']
        require(meta.get('namespace', 'jitsi') == 'jitsi', 'Namespace hors perimetre.')
        require(meta.get('labels', {}).get('app.kubernetes.io/instance') == 'jitsi',
                'Ressource sans appartenance a la release jitsi.')
        live = getter(allowed[doc['kind']], meta['name'])
        require(live.get('metadata', {}).get('annotations', {}).get('meta.helm.sh/release-name') == 'jitsi' and
                live.get('metadata', {}).get('annotations', {}).get('meta.helm.sh/release-namespace') == 'jitsi',
                'Ressource existante non geree par cette release : adoption refusee.')
        if doc['kind'] == 'Service':
            desired, current = doc['spec'], live['spec']
            require(desired.get('type', 'ClusterIP') == current.get('type', 'ClusterIP'),
                    'Changement de type Service refuse.')
            shape = lambda spec: sorted((p['port'], p.get('protocol', 'TCP'), str(p.get('targetPort', p['port'])))
                                        for p in spec['ports'])
            require(shape(desired) == shape(current), 'Changement de ports Service refuse.')
            # Ne pas ajouter des options LB/reservation/annotations sans revue.
            for field in ['loadBalancerIP', 'loadBalancerClass', 'externalIPs', 'loadBalancerSourceRanges',
                          'externalTrafficPolicy', 'ipFamilyPolicy']:
                require(desired.get(field) in (None, [], '') or desired.get(field) == current.get(field),
                        'Changement reseau Service refuse.')
            for key, value in meta.get('annotations', {}).items():
                require(live['metadata'].get('annotations', {}).get(key) == value,
                        'Annotation Service nouvelle/modifiee : revue necessaire.')
            if meta['name'].endswith('-jvb'):
                ip = live.get('status', {}).get('loadBalancer', {}).get('ingress', [{}])[0].get('ip')
                require(bool(ip), 'IP JVB publique manquante.')
                bridge = next(x for x in render if x['kind'] == 'Deployment' and x['metadata']['name'].endswith('-jvb-0'))
                env = bridge['spec']['template']['spec']['containers'][0]['env']
                require(any(e['name'] == 'JVB_ADVERTISE_IPS' and e.get('value') == ip for e in env),
                        'IP annoncee differente du LoadBalancer existant.')
        if after and doc['kind'] in ('Deployment', 'StatefulSet'):
            target = doc['spec'].get('replicas', 1)
            status = live.get('status', {})
            require(status.get('readyReplicas', 0) >= target and
                    status.get('observedGeneration', 0) >= live['metadata'].get('generation', 1),
                    'Workload pas encore pret.')
    # Les mots de passe doivent correspondre aux Secrets actuels : pas de rotation implicite.
    for component, password in passwords.items():
        key = 'JICOFO_AUTH_PASSWORD' if component == 'jicofo' else 'JVB_AUTH_PASSWORD'
        live = getter('secrets', f'jitsi-jitsi-meet-{component}-secret')
        try:
            existing = base64.b64decode(live['data'][key], validate=True).decode()
        except (KeyError, ValueError, UnicodeError):
            raise SystemExit('Secret existant illisible ; valeur non affichee.') from None
        require(existing == password, 'Mot de passe different du Secret existant : rotation non autorisee.')
    if after:
        bridge = getter('deployments.apps', 'jitsi-jitsi-meet-jvb-0')
        env = bridge['spec']['template']['spec']['containers'][0]['env']
        service = getter('services', 'jitsi-jitsi-meet-jvb')
        ip = service['status']['loadBalancer']['ingress'][0]['ip']
        require(any(e['name'] == 'JVB_ADVERTISE_IPS' and e.get('value') == ip for e in env),
                'IP JVB finale incoherente.')


if __name__ == '__main__':
    try:
        chart = yaml.safe_load(Path('charts-officiels/jitsi-meet/Chart.yaml').read_text())
        require(chart.get('version') == '3.10.0', 'Version de chart differente : revue necessaire.')
        documents = [d for d in yaml.safe_load_all(Path(sys.argv[1]).read_text()) if d]
        values = yaml.safe_load(Path(sys.argv[2]).read_text())
        verify(documents, values, read_resource, '--after' in sys.argv[3:])
        print('Perimetre existant, coherence des secrets et reseau : OK (aucune valeur affichee).')
    except SystemExit:
        raise
    except Exception:
        raise SystemExit('Verification CD impossible ; details potentiellement sensibles non affiches.') from None
