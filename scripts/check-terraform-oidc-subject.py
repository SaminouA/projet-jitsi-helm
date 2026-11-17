#!/usr/bin/env python3
"""Pure local correction proposal. Never mutates IAM/provider or fetches tokens."""
import json
from pathlib import Path

REPO='SaminouA/projet-jitsi-helm'
PREFIX='repo:SaminouA@194725286/projet-jitsi-helm@1427106572'
OLD_SUB='repo:'+REPO+':environment:terraform-controlled'
NEW_SUB=PREFIX+':environment:terraform-controlled'
TERMS=["assertion.repository=='"+REPO+"'",
       "assertion.repository_id=='1427106572'",
       "assertion.repository_owner_id=='194725286'",
       "assertion.ref=='refs/heads/main'",
       "assertion.workflow_ref=='"+REPO+"/.github/workflows/terraform-gke.yml@refs/heads/main'",
       "assertion.sub=='"+OLD_SUB+"'"]


def propose(condition,settings):
    if not (settings.get('use_default') is True and settings.get('use_immutable_subject') is True
            and settings.get('sub_claim_prefix')==PREFIX):
        raise ValueError('Unexpected GitHub subject configuration: stop')
    if condition.split(' && ')!=TERMS:
        raise ValueError('Unexpected provider condition: preserve and stop')
    return condition.replace("assertion.sub=='"+OLD_SUB+"'", "assertion.sub=='"+NEW_SUB+"'")


if __name__=='__main__':
    source=json.loads(Path('docs/preuves/terraform-bootstrap-resultats.json').read_text())
    settings={'use_default':True,'use_immutable_subject':True,'sub_claim_prefix':PREFIX}
    before=source['attribute_condition'];after=propose(before,settings)
    result={'status':'PROPOSED_NOT_APPLIED','provider':source['provider'],
            'github_settings_observed':settings,'old_subject':OLD_SUB,'new_subject':NEW_SUB,
            'before_attribute_condition':before,'after_attribute_condition':after,
            'other_conditions_unchanged':before.split(' && ')[:-1]==after.split(' && ')[:-1],
            'attribute_mapping_changed':False,'iam_roles_changed':False,'state_changed':False}
    Path('deploy/terraform/oidc-subject-correction.json').write_text(json.dumps(result,indent=2)+'\n')
    print('Proposal generated: only immutable subject comparison changes; no cloud mutation.')
