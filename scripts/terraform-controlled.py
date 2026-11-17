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


def verify_context(payload, env, main_sha, local_sha):
    check_env = dict(env, CD_ENABLE=env.get('TF_CD_ENABLED', ''))
    expected = event.verify_event(payload, check_env)
    require(env.get('HELM_CD_ENABLED', '').lower() != 'true')
    require(expected == main_sha == local_sha == env.get('TF_APPROVED_SHA'))
    require(env.get('TF_STATE_BUCKET') == BUCKET)
    require(re.fullmatch(r'[0-9a-fA-F-]{36}', env.get('TF_STATE_LINEAGE', '')) is not None)
    return expected


def guard():
    payload = json.loads(Path(os.environ['GITHUB_EVENT_PATH']).read_text())
    main = run(['gh', 'api', 'repos/' + REPO + '/git/ref/heads/main', '--jq', '.object.sha']).stdout.strip()
    local = run(['git', 'rev-parse', 'HEAD']).stdout.strip()
    return verify_context(payload, os.environ, main, local)


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
        require(state_before['serial'] == state_now['serial'])
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
            guard()
            print('CI push main, SHA approuve, backend et opt-in controles ; aucun acces GCP.')
        else:
            controlled_apply()
    except (OSError, ValueError, KeyError, TypeError, AttributeError, subprocess.TimeoutExpired):
        raise SystemExit('Execution Terraform refusee ou interrompue ; details sensibles non publies.') from None
    finally:
        os.umask(old_umask)


if __name__ == '__main__':
    main()
