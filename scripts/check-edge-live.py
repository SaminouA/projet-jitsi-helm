#!/usr/bin/env python3
"""Garde CD edge : uniquement objets et PVC deja crees apres autorisation."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import yaml

spec = importlib.util.spec_from_file_location('edge_render', Path(__file__).with_name('check-edge-render.py'))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def get(kind, name):
    p = subprocess.run(['kubectl', '-n', 'jitsi', 'get', kind, name, '-o', 'json'], capture_output=True, text=True, timeout=30)
    if p.returncode:
        raise SystemExit('Bootstrap edge absent ou lecture interdite : ' + kind + '/' + name)
    return json.loads(p.stdout)


if __name__ == '__main__':
    docs = [d for d in yaml.safe_load_all(Path(sys.argv[1]).read_text()) if d]
    domain = sys.argv[2]
    module.verify(docs, domain)
    mapping = {'Service': 'services', 'ConfigMap': 'configmaps', 'Deployment': 'deployments.apps'}
    for doc in docs:
        live = get(mapping[doc['kind']], doc['metadata']['name'])
        annotations = live['metadata'].get('annotations', {})
        module.require(annotations.get('meta.helm.sh/release-name') == 'jitsi-edge' and
                       annotations.get('meta.helm.sh/release-namespace') == 'jitsi', 'Adoption edge interdite')
        if doc['kind'] == 'Service':
            module.require(live['spec']['type'] == doc['spec']['type'] and
                           bool(live.get('status', {}).get('loadBalancer', {}).get('ingress')), 'LoadBalancer edge existant requis')
            shape = lambda s: sorted((p['port'], p['targetPort'], p['protocol']) for p in s['ports'])
            module.require(shape(live['spec']) == shape(doc['spec']), 'Changement des ports edge interdit')
            for key, value in doc['metadata']['annotations'].items():
                module.require(annotations.get(key) == value, 'Changement de reservation/annotation edge interdit')
        if doc['kind'] == 'ConfigMap':
            module.require('https://' + domain + ' {' in live['data']['Caddyfile'], 'Migration DNS edge : autorisation distincte requise')
        if '--after' in sys.argv and doc['kind'] == 'Deployment':
            module.require(live.get('status', {}).get('readyReplicas', 0) == 1 and
                           live['status'].get('observedGeneration', 0) >= live['metadata']['generation'], 'Caddy non pret')
    pvc = get('persistentvolumeclaims', 'jitsi-edge-data')
    module.require(pvc.get('status', {}).get('phase') == 'Bound', 'PVC edge existant Bound requis')
    print('Edge existant et PVC Bound verifies ; aucune creation implicite autorisee.')
