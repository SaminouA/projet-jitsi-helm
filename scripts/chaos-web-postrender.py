#!/usr/bin/env python3
"""Post-render Helm local : aucun daemon, suppression du seul pod Web approuve."""
import os
import re
import sys
import yaml


def transform(documents, target):
    if not re.fullmatch(r'jitsi-jitsi-meet-web-[a-z0-9]+-[a-z0-9]+', target):
        raise SystemExit('Nom exact du pod Web approuve requis ; rendu refuse.')
    output = []
    changed = False
    for obj in documents:
        if not obj: continue
        meta = obj.get('metadata', {})
        component = meta.get('labels', {}).get('app.kubernetes.io/component')
        if obj['kind'] == 'DaemonSet' or component in ('chaos-daemon', 'chaos-dashboard'): continue
        if obj['kind'] in ('PersistentVolumeClaim', 'PersistentVolume', 'PodSecurityPolicy'):
            raise SystemExit('Ressource inattendue dans installation minimale : refusee.')
        if obj['kind'] == 'ClusterRole' and meta['name'] == 'chaos-mesh-chaos-controller-manager-target-namespace':
            obj['rules'] = [
                {'apiGroups': [''], 'resources': ['pods'], 'verbs': ['get', 'list', 'watch']},
                {'apiGroups': [''], 'resources': ['pods'], 'verbs': ['delete'], 'resourceNames': [target]},
                {'apiGroups': [''], 'resources': ['events'], 'verbs': ['get', 'list', 'watch', 'create', 'patch']},
                {'apiGroups': ['chaos-mesh.org'], 'resources': ['podchaos', 'podchaos/status', 'podchaos/finalizers'],
                 'verbs': ['get', 'list', 'watch', 'create', 'update', 'patch', 'delete']},
            ]
            changed = True
        output.append(obj)
    if not changed: raise SystemExit('Role cible absent : version/release inattendue, rendu refuse.')
    bindings = [d for d in output if d.get('roleRef', {}).get('name') ==
                'chaos-mesh-chaos-controller-manager-target-namespace']
    if len(bindings) != 1 or bindings[0]['kind'] != 'RoleBinding' or bindings[0]['metadata'].get('namespace') != 'jitsi':
        raise SystemExit('Binding cible hors namespace jitsi : rendu refuse.')
    deployments = [d for d in output if d['kind'] == 'Deployment']
    if len(deployments) != 1 or deployments[0]['spec']['replicas'] != 1:
        raise SystemExit('Un seul controleur attendu : rendu refuse.')
    pod = deployments[0]['spec']['template']['spec']
    if pod.get('hostNetwork') or pod.get('hostPID') or any('hostPath' in v for v in pod.get('volumes', [])) or any(
            c.get('securityContext', {}).get('privileged') for c in pod['containers']):
        raise SystemExit('Acces hote interdit pour ce test controller-only.')
    for d in output:
        if d['kind'] == 'Service' and d['spec'].get('type', 'ClusterIP') != 'ClusterIP':
            raise SystemExit('Service expose interdit.')
    return output


if __name__ == '__main__':
    try:
        documents = list(yaml.safe_load_all(sys.stdin))
        yaml.safe_dump_all(transform(documents, os.environ.get('CHAOS_WEB_POD', '')), sys.stdout, sort_keys=False)
    except (KeyError, TypeError, ValueError, yaml.YAMLError):
        raise SystemExit('Rendu Chaos illisible ; aucune sortie sensible publiee.') from None
