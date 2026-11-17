#!/usr/bin/env python3
"""Premier apply label-only. Ne pas lancer localement hors runner autorise."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
REPO = 'SaminouA/projet-jitsi-helm'
PROJECT = 'project-fcf2ef91-c005-4910-a10'
BUCKET = PROJECT + '-tfstate'
PREFIX = 'jitsi/gke'
ACCOUNT = 'terraform-jitsi-deployer@' + PROJECT + '.iam.gserviceaccount.com'


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'scripts' / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


event = load('terraform_event', 'check-cd-event.py')
plan_guard = load('terraform_plan_guard', 'check-terraform-plan.py')


def require(ok, message='Prerequis Terraform refuse ; details non publies.'):
    if not ok:
        raise SystemExit(message)


def run(args, accepted=(0,)):
    # Aucun shell, echo de commande, sortie brute ou transfert de plan.
    env = {k: v for k, v in os.environ.items() if not k.startswith('TF_')}
    env.update(TF_IN_AUTOMATION='true', TF_INPUT='false')
    result = subprocess.run(args, capture_output=True, text=True, timeout=900, env=env)
    require(result.returncode in accepted, 'Operation Terraform/GCP echouee ; sorties sensibles non publiees, aucune relance automatique.')
    return result


def verify_context(payload, env, main_sha, local_sha, check_backend=True):
    require(env.get('GITHUB_ACTIONS') == 'true' and env.get('GITHUB_EVENT_NAME') == 'workflow_dispatch')
    require(env.get('GITHUB_REPOSITORY') == REPO and env.get('GITHUB_REF') == 'refs/heads/main')
    require(env.get('TF_OPERATION') == 'apply-label' and payload.get('inputs', {}).get('operation') == 'apply-label')
    require(env.get('TF_CD_ENABLED') == 'true' and env.get('HELM_CD_ENABLED', '').lower() != 'true')
    expected = env.get('EXPECTED_SHA', '')
    require(re.fullmatch(r'[a-f0-9]{40}', expected) is not None)
    require(expected == main_sha == local_sha == env.get('TF_APPROVED_SHA') == env.get('GITHUB_SHA'))
    if check_backend:
        require(env.get('TF_STATE_BUCKET') == BUCKET)
        require(re.fullmatch(r'[0-9a-fA-F-]{36}', env.get('TF_STATE_LINEAGE', '')) is not None)
    return expected


def verify_environment(environment, branches):
    require(environment.get('can_admins_bypass') is False, 'ENVIRONMENT_ADMIN_BYPASS_REFUSED')
    reviewers = [r for r in environment.get('protection_rules', []) if r.get('type') == 'required_reviewers']
    require(len(reviewers) == 1 and bool(reviewers[0].get('reviewers')), 'HUMAN_REVIEWER_REQUIRED')
    require(environment.get('deployment_branch_policy', {}).get('custom_branch_policies') is True)
    require([(b.get('name'), b.get('type')) for b in branches.get('branch_policies', [])] == [('main', 'branch')])


def guard(check_backend=True):
    payload = json.loads(Path(os.environ['GITHUB_EVENT_PATH']).read_text())
    api = ['gh', 'api', 'repos/' + REPO]
    main = run(['gh', 'api', 'repos/' + REPO + '/git/ref/heads/main', '--jq', '.object.sha']).stdout.strip()
    local = run(['git', 'rev-parse', 'HEAD']).stdout.strip()
    sha = verify_context(payload, os.environ, main, local, check_backend=check_backend)
    environment = json.loads(run(['gh', 'api', 'repos/' + REPO + '/environments/terraform-controlled']).stdout)
    branches = json.loads(run(['gh', 'api', 'repos/' + REPO + '/environments/terraform-controlled/deployment-branch-policies']).stdout)
    verify_environment(environment, branches)
    runs = json.loads(run(['gh', 'api', 'repos/' + REPO + '/actions/workflows/helm-ci.yml/runs?branch=main&event=push&status=success&per_page=100']).stdout)
    eligible = [r for r in runs.get('workflow_runs', []) if r.get('head_sha') == sha]
    require(bool(eligible), 'SUCCESSFUL_MAIN_CI_REQUIRED')
    event.verify_event({'repository': {'full_name': REPO}, 'workflow_run': eligible[0]},
                       dict(os.environ, GITHUB_EVENT_NAME='workflow_run', CD_ENABLE='true'))
    return sha


def verify_state(state):
    require(state.get('lineage') == os.environ['TF_STATE_LINEAGE'])
    require(isinstance(state.get('serial'), int) and state['serial'] >= 9)
    resources = state.get('resources', [])
    require(len(resources) == 2)
    addresses = set()
    for resource in resources:
        require(not resource.get('module') and resource.get('mode') == 'managed')
        address = resource['type'] + '.' + resource['name']
        addresses.add(address)
        instances = resource.get('instances', [])
        require(len(instances) == 1 and not instances[0].get('deposed'))
        attrs = instances[0]['attributes']
        require(attrs.get('project') == PROJECT and attrs.get('location') == 'europe-west1-b')
        expected = 'jitsi-cluster' if address == plan_guard.CLUSTER else 'jitsi-node-pool'
        require(attrs.get('name') == expected)
        resource_id = 'projects/' + PROJECT + '/locations/europe-west1-b/clusters/jitsi-cluster'
        if address == plan_guard.POOL:
            resource_id += '/nodePools/jitsi-node-pool'
        require(attrs.get('id') == resource_id)
    require(addresses == {plan_guard.CLUSTER, plan_guard.POOL})


def verify_bucket(bucket):
    require(bucket.get('name') == BUCKET and str(bucket.get('projectNumber')) == '198310729956')
    require(bucket.get('location', '').upper() == 'EUROPE-WEST1')
    require(bucket.get('versioning', {}).get('enabled') is True)
    iam = bucket.get('iamConfiguration', {})
    require(iam.get('uniformBucketLevelAccess', {}).get('enabled') is True and
            iam.get('publicAccessPrevention') == 'enforced')
    # Une retention imposee peut empecher la suppression du verrou .tflock.
    require(not bucket.get('retentionPolicy'))


def controlled_apply():
    guard()
    from urllib.parse import unquote
    credentials = json.loads(Path(os.environ['GOOGLE_APPLICATION_CREDENTIALS']).read_text())
    require(credentials.get('type') == 'external_account' and 'private_key' not in credentials)
    require(ACCOUNT in unquote(credentials.get('service_account_impersonation_url', '')))
    account = run(['gcloud', 'auth', 'list', '--filter=status:ACTIVE', '--format=value(account)']).stdout.strip()
    require(account == ACCOUNT, 'Identite Terraform dediee requise ; apply refuse.')
    bucket = json.loads(run(['gcloud', 'storage', 'buckets', 'describe', 'gs://' + BUCKET,
                             '--raw', '--format=json']).stdout)
    verify_bucket(bucket)
    with tempfile.TemporaryDirectory(prefix='jitsi-terraform.', dir=Path(os.environ['RUNNER_TEMP']).resolve()) as directory:
        tmp = Path(directory)
        os.chmod(tmp, 0o700)
        with open(os.environ['GITHUB_ENV'], 'a') as out:
            out.write('TF_CONTROLLED_TMP=' + str(tmp) + '\n')
        for file in (ROOT / 'terraform').glob('*.tf'):
            shutil.copy2(file, tmp / file.name)
        shutil.copy2(ROOT / 'terraform/.terraform.lock.hcl', tmp / '.terraform.lock.hcl')
        terraform = ['terraform', '-chdir=' + str(tmp)]
        run(terraform + ['fmt', '-check'])
        # Aucun -migrate-state, -force-copy, -reconfigure, -lock=false ni import.
        run(terraform + ['init', '-input=false', '-lockfile=readonly',
                         '-backend-config=bucket=' + BUCKET, '-backend-config=prefix=' + PREFIX])
        require(run(terraform + ['workspace', 'show']).stdout.strip() == 'default')
        run(terraform + ['validate'])
        state_before = json.loads(run(terraform + ['state', 'pull']).stdout)
        verify_state(state_before)  # Etat absent/vide/mauvais : jamais de creation.
        saved = tmp / 'approved.tfplan'
        run(terraform + ['plan', '-input=false', '-no-color', '-detailed-exitcode',
                         '-lock-timeout=60s', '-out=' + str(saved)], accepted=(2,))
        os.chmod(saved, 0o600)
        plan = json.loads(run(terraform + ['show', '-json', str(saved)]).stdout)
        print(plan_guard.verify(plan), flush=True)
        digest = hashlib.sha256(saved.read_bytes()).digest()
        guard()  # Un push intervenu pendant le plan interdit l'apply.
        state_now = json.loads(run(terraform + ['state', 'pull']).stdout)
        verify_state(state_now)
        require(state_before == state_now)
        require(hashlib.sha256(saved.read_bytes()).digest() == digest)
        run(terraform + ['apply', '-input=false', '-no-color', '-lock-timeout=60s', str(saved)])
        # Le plan sauvegarde est le seul applique ; aucun nouveau calcul automatique.
        state_after = json.loads(run(terraform + ['state', 'pull']).stdout)
        verify_state(state_after)
        require(state_after['serial'] > state_before['serial'])
        cluster = json.loads(run(['gcloud', 'container', 'clusters', 'describe', 'jitsi-cluster',
            '--project=' + PROJECT, '--zone=europe-west1-b', '--format=json(resourceLabels,status)']).stdout)
        require(cluster.get('resourceLabels', {}).get(plan_guard.LABEL) == plan_guard.VALUE and cluster.get('status') == 'RUNNING')
        run(terraform + ['plan', '-input=false', '-no-color', '-detailed-exitcode', '-lock-timeout=60s'])
        print('Apply label verifie, cluster RUNNING, plan final sans changement ; aucun etat/plan publie.', flush=True)
    print('Fichiers Terraform prives supprimes ; aucune activation Helm effectuee.', flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--guard-only', action='store_true')
    args = parser.parse_args()
    old_umask = os.umask(0o077)
    try:
        if args.guard_only:
            guard(check_backend=False)
            print('CI main, SHA, opt-in et approbateur controles ; backend verifie dans le job protege.')
        else:
            controlled_apply()
    except (OSError, ValueError, KeyError, TypeError, AttributeError, subprocess.TimeoutExpired):
        raise SystemExit('Execution Terraform refusee ou interrompue ; details sensibles non publies.') from None
    finally:
        os.umask(old_umask)


if __name__ == '__main__':
    main()
