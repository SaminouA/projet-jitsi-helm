#!/usr/bin/env python3
"""Manual OIDC/GCS/plan validation. No migration or infrastructure mutation path."""
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
PROJECT = 'project-fcf2ef91-c005-4910-a10'
BUCKET = PROJECT + '-tfstate'
SA = 'terraform-jitsi-deployer@' + PROJECT + '.iam.gserviceaccount.com'
CLUSTER = 'google_container_cluster.jitsi'
POOL = 'google_container_node_pool.jitsi_nodes'


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def verify_context(env, main_sha):
    require(env.get('GITHUB_ACTIONS') == 'true' and env.get('GITHUB_EVENT_NAME') == 'workflow_dispatch', 'MANUAL_GITHUB_RUN_REQUIRED')
    require(env.get('GITHUB_REPOSITORY') == 'SaminouA/projet-jitsi-helm' and env.get('GITHUB_REF') == 'refs/heads/main', 'MAIN_REPOSITORY_REQUIRED')
    require(env.get('GITHUB_SHA') == main_sha and re.fullmatch(r'[a-f0-9]{40}', main_sha), 'MAIN_SHA_CHANGED')
    require(env.get('TF_CD_ENABLED', '').lower() != 'true' and env.get('GKE_CD_ENABLED', '').lower() != 'true', 'DEPLOYMENT_FLAGS_MUST_BE_DISABLED')
    require(env.get('TF_STATE_BUCKET') == BUCKET and re.fullmatch(r'[a-fA-F0-9-]{36}', env.get('TF_STATE_LINEAGE', '')), 'BACKEND_VARIABLES_INVALID')


def verify_state(state, lineage):
    require(state.get('lineage') == lineage and isinstance(state.get('serial'), int) and state['serial'] >= 10, 'REMOTE_STATE_IDENTITY_INVALID')
    resources = state.get('resources', [])
    require(len(resources) == 2, 'REMOTE_STATE_RESOURCE_COUNT_INVALID')
    expected = {CLUSTER: 'jitsi-cluster', POOL: 'jitsi-node-pool'}
    actual = set()
    for r in resources:
        address = r['type'] + '.' + r['name']
        require(r.get('mode') == 'managed' and not r.get('module') and address in expected and len(r['instances']) == 1, 'REMOTE_STATE_RESOURCE_INVALID')
        instance = r['instances'][0]
        require(not instance.get('deposed'), 'DEPOSED_RESOURCE_REFUSED')
        a = instance['attributes']; actual.add(address)
        suffix = '' if address == CLUSTER else '/nodePools/jitsi-node-pool'
        require(a.get('project') == PROJECT and a.get('location') == 'europe-west1-b' and a.get('name') == expected[address], 'REMOTE_RESOURCE_MISMATCH')
        require(a.get('id') == 'projects/' + PROJECT + '/locations/europe-west1-b/clusters/jitsi-cluster' + suffix, 'REMOTE_RESOURCE_ID_MISMATCH')
    require(actual == set(expected), 'REMOTE_RESOURCES_DUPLICATED')


def verify_plan(plan):
    require(not plan.get('errored') and plan.get('complete', True) and not plan.get('deferred_changes'), 'INCOMPLETE_PLAN')
    changes = plan.get('resource_changes', [])
    require(len(changes) == 2 and {r['address'] for r in changes} == {CLUSTER, POOL}, 'PLAN_RESOURCES_INVALID')
    require(all(r.get('mode') == 'managed' and r['change']['actions'] == ['no-op'] and not r['change'].get('replace_paths') for r in changes), 'PLAN_CHANGE_REFUSED')
    require(not any(c.get('actions') != ['no-op'] for c in plan.get('output_changes', {}).values()), 'OUTPUT_CHANGE_REFUSED')
    return {'create': 0, 'update': 0, 'delete': 0, 'replace': 0}


def run(args, accepted=(0,)):
    p = subprocess.run(args, capture_output=True, text=True, timeout=240)
    require(p.returncode in accepted, 'READONLY_COMMAND_FAILED_' + args[0])
    return p


def main():
    os.umask(0o077)
    main_sha = run(['gh', 'api', 'repos/SaminouA/projet-jitsi-helm/git/ref/heads/main', '--jq', '.object.sha']).stdout.strip()
    verify_context(os.environ, main_sha)
    credentials = json.loads(Path(os.environ['GOOGLE_APPLICATION_CREDENTIALS']).read_text())
    require(credentials.get('type') == 'external_account' and 'private_key' not in credentials, 'KEYLESS_EXTERNAL_ACCOUNT_REQUIRED')
    require(SA in unquote(credentials.get('service_account_impersonation_url', '')), 'TERRAFORM_IMPERSONATION_REQUIRED')
    account = run(['gcloud', 'auth', 'list', '--filter=status:ACTIVE', '--format=value(account)']).stdout.strip()
    require(account == SA, 'ACTIVE_TERRAFORM_IDENTITY_REQUIRED')
    with tempfile.TemporaryDirectory(prefix='terraform-readonly.', dir=os.environ['RUNNER_TEMP']) as name:
        directory = Path(name)
        for p in (ROOT / 'terraform').glob('*.tf'):
            shutil.copy2(p, directory / p.name)
        shutil.copy2(ROOT / 'terraform/.terraform.lock.hcl', directory / '.terraform.lock.hcl')
        tf = ['terraform', '-chdir=' + str(directory)]
        run(tf + ['init', '-input=false', '-lockfile=readonly', '-backend-config=bucket=' + BUCKET, '-backend-config=prefix=jitsi/gke'])
        backend = json.loads((directory / '.terraform/terraform.tfstate').read_text())['backend']
        require(backend['type'] == 'gcs' and backend['config']['bucket'] == BUCKET and backend['config']['prefix'] == 'jitsi/gke', 'GCS_BACKEND_NOT_CONFIRMED')
        require(run(tf + ['workspace', 'show']).stdout.strip() == 'default', 'WORKSPACE_INVALID')
        before = json.loads(run(tf + ['state', 'pull']).stdout)
        verify_state(before, os.environ['TF_STATE_LINEAGE'])
        run(tf + ['validate'])
        planned = directory / 'readonly.tfplan'
        run(tf + ['plan', '-input=false', '-no-color', '-lock-timeout=60s', '-detailed-exitcode', '-out=' + str(planned)], accepted=(0, 2))
        plan = json.loads(run(tf + ['show', '-json', str(planned)]).stdout)
        counts = verify_plan(plan)
        after = json.loads(run(tf + ['state', 'pull']).stdout)
        verify_state(after, os.environ['TF_STATE_LINEAGE'])
        require(after == before, 'REMOTE_STATE_CHANGED_DURING_DIAGNOSTIC')
        summary = {'oidc_keyless': True, 'identity': SA, 'backend': 'gcs', 'bucket': BUCKET, 'prefix': 'jitsi/gke', 'workspace': 'default', 'state_serial': after['serial'], 'lineage_verified_not_logged': True, 'resources': 2, 'plan': counts, 'remote_state_unchanged': True, 'apply_executed': False}
        print(json.dumps(summary, sort_keys=True), flush=True)
        with open(os.environ['GITHUB_STEP_SUMMARY'], 'a') as out:
            out.write('OIDC sans clé, identité Terraform, GCS distant et state vérifiés.\n\n```json\n' + json.dumps(summary, indent=2) + '\n```\n')
    print('Diagnostic terminé ; fichiers privés supprimés, aucune mutation GKE.', flush=True)


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        # Never publish subprocess output, plan/state contents, kubeconfigs or tokens.
        category = str(error) if isinstance(error, RuntimeError) else type(error).__name__
        raise SystemExit('Diagnostic Terraform refusé : ' + category) from None
