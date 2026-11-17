#!/usr/bin/env python3
"""Garde strict du premier apply : une seule mise a jour de label GKE."""
import json
import sys

CLUSTER = 'google_container_cluster.jitsi'
POOL = 'google_container_node_pool.jitsi_nodes'
LABEL = 'devops-apply-proof'
VALUE = 'github-actions'
PROJECT = 'project-fcf2ef91-c005-4910-a10'
LABEL_FIELDS = {'resource_labels', 'terraform_labels', 'effective_labels'}


def require(ok):
    if not ok:
        raise SystemExit('Plan refuse : seul le label de preuve sur le cluster existant est autorise ; details masques.')


def unknown(value):
    if isinstance(value, dict): return any(unknown(v) for v in value.values())
    if isinstance(value, list): return any(unknown(v) for v in value)
    return value is True


def verify(plan):
    require(not plan.get('errored') and plan.get('complete', True) and not plan.get('deferred_changes'))
    changes = plan.get('resource_changes') or []
    require(len(changes) == 2 and {r.get('address') for r in changes} == {CLUSTER, POOL})
    for resource in changes:
        require(resource.get('mode') == 'managed')
        c = resource['change']
        require(not c.get('replace_paths') and not unknown(c.get('after_unknown', {})))
        before, after = c.get('before'), c.get('after')
        require(isinstance(before, dict) and isinstance(after, dict))
        require(before.get('project') == after.get('project') == PROJECT)
        require(before.get('location') == after.get('location') == 'europe-west1-b')
        if resource['address'] == POOL:
            require(c['actions'] == ['no-op'] and before == after)
            require(before.get('name') == 'jitsi-node-pool' and before.get('node_count') == 2)
        else:
            require(c['actions'] == ['update'])
            require(before.get('name') == after.get('name') == 'jitsi-cluster')
            require(LABEL not in (before.get('resource_labels') or {}))
            require({k: v for k, v in before.items() if k not in LABEL_FIELDS} ==
                    {k: v for k, v in after.items() if k not in LABEL_FIELDS})
            for field in LABEL_FIELDS:
                require(LABEL not in (before.get(field) or {}))
                expected = dict(before.get(field) or {})
                expected[LABEL] = VALUE
                require(after.get(field) == expected)
    require(not any(c.get('actions') != ['no-op'] for c in plan.get('output_changes', {}).values()))
    return 'Plan autorise : 1 update de label, 0 create, 0 delete, 0 replace ; pool inchange.'


if __name__ == '__main__':
    try:
        print(verify(json.load(sys.stdin)))
    except (ValueError, KeyError, TypeError, AttributeError):
        raise SystemExit('Plan illisible ou incomplet : apply refuse ; details masques.') from None
